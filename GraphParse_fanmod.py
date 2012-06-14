import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
import cPickle as pickle
import scipy.stats as stats
import re
 
#Out put a text file representation of graph
def outputGraph(graph,name="OUTPUT.txt"):
	G = nx.convert_node_labels_to_integers(graph,1)
	with open("result/"+name,'wb') as f:
		f.write(str(len(G)) + '\n')
		nx.write_edgelist(G,f,data=False)

#Find motifs of motifSize in G
def findSingleMotif(G,motifSize):
	outputGraph(G)
	os.system("./fanmod_command_line_linux " +str(motifSize) + " 100000 1 result2/OUTPUT.txt 1 0 0 2 0 0 0 1 3 3 result2/MotifCount.txt 0 0")
	data = parseOutput("result2/MotifCount.txt")
	return data	


# convert Graph ID to a networkx graph	
def convertIDToGraph(id,motifSize):
	binary = bin(id);
	adj = np.zeros(motifSize*motifSize)
	for x in xrange(motifSize*motifSize):
		if binary[-x] == 'b':
			break
		adj[-x] = int(binary[-x])
	adj.shape = (motifSize,motifSize)
	graph = nx.to_networkx_graph(adj,create_using=nx.DiGraph())
	nx.draw_circular(graph)
	#plt.savefig("result/id-"+str(id)+"size-"+str(motifSize))
	plt.show()
	

def parseOutput(path):
	pattern = re.compile('%')
	returnlist = []
	f = open(path, 'r')
	total = None
	for line in f:
		myList = line.strip().split(",")
		if len(myList) == 1 and myList[0].find('original network') != -1:
			total = float(line.strip().split(" ")[0])
			#print total
		elif len(myList) == 7 and myList[0] != 'ID':
			estimate = float(re.sub(pattern, '', myList[2]))/100 * total
			#print estimate
			returnlist.append([int(myList[0]), estimate, float(re.sub(pattern, '', myList[2]))/100])
			
	return returnlist
			
# Main finding motifs routine	
def findMotifs(data,key,motifSize,degree,usetotal=False):
	#Check cache
	filename = str(key)+'s'+str(int(motifSize))+'d'+str(int(degree))+str(usetotal)+".pkl"
	if os.path.exists('cache2/'+filename):
		print "in cache"
		with open('cache2/'+filename,"rb") as f:
			return pickle.load(f)
			
	graphs = data[key]
	motifs = {}
	numstring ="/"+str(len(graphs))
	counter = 1
	for G in graphs:
		#calculate threshold
		sortedWeights = np.sort(G,axis=None)
		threshold = sortedWeights[-len(G)*degree-1]
		#Print progress
		sys.stdout.write("\r")
		sys.stdout.write("Motif Finding Progress: "+str(counter)+numstring)
		sys.stdout.write(" Threshold: "+str(threshold))
		sys.stdout.flush()
		counter+=1
		#Output graph to txt file
		graph = nx.DiGraph(G>threshold)
		graph = nx.convert_node_labels_to_integers(graph,1)
		with open('result2/OUTPUT.txt','wb') as f:
			nx.write_edgelist(graph,f,data=False)
		#Jenky way to use c++ motif finder in python
		os.system("./fanmod_command_line_linux " +str(motifSize) + " 100000 1 result2/OUTPUT.txt 1 0 0 2 0 0 0 1 3 3 result2/MotifCount.txt 0 0")
		data = parseOutput("result2/MotifCount.txt")
		for iD,total,percent in data:
			if iD in motifs:
				motifs[iD].append(total if usetotal else percent)
			else:
				motifs[iD] = [total if usetotal else percent]
	
	print '\nMotifs Done!'
		
	for key,value in motifs.iteritems():
		numZero = len(graphs)-len(value)
		value.extend([0 for derp in xrange(numZero)])
		motifs[key] = np.array(value)
	
	#add motifs to cache
	with open('cache2/'+filename,'wb') as f:
		pickle.dump(motifs,f)
		
	return motifs

def aveDegree(G):
	return G.size()/float(len(G))	

def statTest(data,motifSize,degree):
	for corr in ('corr','lcorr','lacorr'):
		motifsNL = findMotifs(data,('NL',corr), motifSize, degree)
		motifsMCI = findMotifs(data,('MCI',corr), motifSize, degree)
		motifsAD = findMotifs(data,('AD',corr), motifSize, degree)
		
		allMotifs = list(set(motifsNL.keys()) & set(motifsAD.keys()) & set(motifsMCI.keys()))
		
		filename = "result2/{0} ks-stats size-{1} deg-{2}".format(corr,motifSize,degree)
		with open(filename,'w') as f:
			f.write("{0:>10}{1:>15}{2:>15}{3:>15}{4:>15}{5:>15}\n".format('ID','MCI','AD','NORM NL','NORM MCI','NORM AD'))
			for key in allMotifs:
				KSstatistic, MCIpvalue = stats.ks_2samp(motifsMCI[key],motifsNL[key])
				KSstatistic, ADpvalue = stats.ks_2samp(motifsAD[key],motifsNL[key])
				k2,NLnorm = stats.normaltest(motifsNL[key])
				k2,MCInorm = stats.normaltest(motifsMCI[key])
				k2,ADnorm = stats.normaltest(motifsAD[key])
				sig = "*" if (MCIpvalue<0.01 or ADpvalue <0.01) else ''
				
				line = "{0:>10}{1:15.3}{2:15.3}{3:15.3}{4:15.3}{5:15.3}\n"
				f.write(line.format(sig+str(int(key)),MCIpvalue,ADpvalue,NLnorm,MCInorm,ADnorm))

		
def plotMotifGraphs(data,motifSize,degree,numofmotifs):
	for corr in ('corr','lcorr','lacorr'):
		nl=findMotifs(data,('NL',corr), motifSize, degree)
		mci=findMotifs(data,('MCI',corr), motifSize, degree)
		ad=findMotifs(data,('AD',corr), motifSize, degree)
		
		motifs = nl.items()
		motifs = sorted(motifs,key=lambda x:-x[1].mean())
		keys = [int(x[0]) for x in motifs[:numofmotifs]]
		meansNL = []
		meansMCI = []
		meansAD = []
		stdNL = []
		stdMCI = []
		stdAD = []
		for key in keys:
			key = float(key)
			if key in nl:
				meansNL.append(nl[key].mean())
				stdNL.append(nl[key].std())
			else:
				meansNL.append(0.0)
				stdNL.append(0.0)
			if key in mci:
				meansMCI.append(mci[key].mean())
				stdMCI.append(mci[key].std())
			else:
				meansMCI.append(0.0)
				stdMCI.append(0.0)
			if key in ad:
				meansAD.append(ad[key].mean())
				stdAD.append(ad[key].std())
			else:
				meansAD.append(0.0)
				stdAD.append(0.0)
		
		ind = np.arange(numofmotifs)
		width = 0.2 

		NLplt = plt.bar(ind, meansNL, width, color='b', yerr=stdNL, ecolor='y')
		MCIplt = plt.bar(ind+width, meansMCI, width, color='y', yerr=stdMCI, ecolor='b')
		ADplt = plt.bar(ind+width+width, meansAD, width, color='g', yerr=stdAD, ecolor='r')

		plt.ylabel('Average number of motifs')
		plt.xlabel('Motif ID')
		plt.title('Fanmod - Motif size '+str(motifSize) +' distribution for '+corr+" with average degree "+str(degree))
		plt.xticks(ind+width+width/2., keys)
		plt.ylim(ymin=0.0)
		plt.legend( (NLplt[0], MCIplt[0], ADplt[0]), ('NL', 'MCI', 'AD') )
		plt.grid(True)
		plt.savefig("result2/MotifDistTotal-"+corr+" D-"+str(degree)+" S-"+str(motifSize))
		plt.clf()
	

if __name__ == '__main__':
	with open("aznorbert_corrsd.pkl","rb") as f:
		data = pickle.load(f)
		
#	plotMotifGraphs(data,3,10,10)
#	plotMotifGraphs(data,3,12,10)
#	plotMotifGraphs(data,3,15,10)
#	plotMotifGraphs(data,4,10,10)
#	keys = data.keys()
#	G = data[keys[0]][0]
#	degree = 10
#	sortedWeights = np.sort(G,axis=None)
#	threshold = sortedWeights[-len(G)*degree-1]
#
#	graph = nx.DiGraph(G>threshold)
#	findSingleMotif(graph, 3)

	statTest(data,3,15)
	statTest(data,4,10)
	statTest(data,4,15)

	#convertIDToGraph(142,3)
	
	

	
	
"""	
def plotThresholds():
	f = open("aznorbert_corrsd.pkl","rb")
	DATA = pickle.load(f)
	f.close()
	
	for name,graphs in DATA.iteritems():
		thresholds = np.linspace(.9999,0.9,11)
		totalAveDegree = []
		print str(name)
		for thresh in thresholds:
			minDeg = 999999
			array = np.zeros(len(graphs))
			counter = 0
			for graph in graphs:
				ave = aveDegree(nx.DiGraph(graph>thresh))
				array[counter]=ave
				counter+=1
			totalAveDegree.append(array.mean())
		plt.plot(thresholds,totalAveDegree)
		plt.savefig(str(name))
"""
	

	
	
	
