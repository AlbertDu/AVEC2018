import sys
sys.path.append("../Config/")
import GlobalsVars as v
from ConcArff import concGs, concRec
from GSMatching import gsOpen, gsMatch
from FeatsNorm import normFeatures
from PostTreats import postTreatDev
from Print import printBestVal
sys.path.append("../Utils/")
from PredUtils import unimodalPredPrep, cccCalc
from Setup import setup
import operator
import arff
import os
import numpy as np
import sys
import scipy as sp
from scipy import signal
sys.path.append(v.labLinearPath)
from liblinearutil import train, predict
import timeit

#Unimodal prediction on Dev partition
def unimodalPredDev(gs, c, tr, de, earlystop):
	[model, pred, cccDev] = [[] for i in range(3)]
	gsC = np.array(gs['dev'])
	#Options for liblinear
	options = "-s "+str(v.sVal)+" -c "+str(c)+" -B 1 -q"
	#[0] = Arousal/[1] = Valence
	for nDim in range(v.nDim):
		if (earlystop[nDim] != 0):
			#We learn the model on train
			model.append(train(np.array(gs['train'])[:,nDim],tr,options))
			#We predict on dev data
			pred.append(predict(gsC[:,nDim],de,model[nDim],"-q")[0])
			#We calculate the correlation and store it
			cccDev.append(cccCalc(np.array(pred[nDim]),gsC[:,nDim]))
		else :
			cccDev.append(-1.0)
			pred.append([])
			model.append(None)
	return cccDev, pred
#Fin unimodalPredictionDev

#Return the best ccc value for a window size, a window step and a delay given
def bestdelay(ccc, wSize, wStep, delay):
	b = np.zeros(v.nDim)
	for i in range(len(ccc)):
		for nDim in range(v.nDim):
			if (ccc[i][0] == wSize and ccc[i][1] == wStep and ccc[i][4] == delay and ccc[i][2+nDim] > b[nDim]):
				b[nDim] = ccc[i][2+nDim]
	return b	

#Return the best ccc value for a window size and a windows step given
def bestVal(ccc, wSize, wStep):
	b = np.zeros(v.nDim)
	for i in range(len(ccc)):
		for nDim in range(v.nDim):
			if (ccc[i][0] == wSize and ccc[i][1] == wStep and ccc[i][2+nDim] > b[nDim]):
				b[nDim] = ccc[i][2+nDim]
	return b	

#Return true if the last three best value for delay are decreasing
def earlyStopDelay(earlystop, bDmU, bD, bDelay):
	for nDim in range(v.nDim):
		if (bD[nDim] == None) :
			bD[nDim] = bDelay[nDim]
			bDmU[nDim] = bD[nDim]						
		else :
			if (earlystop[nDim] > 0 and bDelay[nDim] < bD[nDim]):
				earlystop[nDim] -= 1
			elif (earlystop[nDim] > 0 and bDelay[nDim] >= bD[nDim]) :
				earlystop[nDim] = 3
				bDmU[nDim] = bD[nDim]						
				bD[nDim] = bDelay[nDim]
	if (earlystop[0] == 0 and earlystop[1] == 0):
		return True
	else :
		return False

#Try all the possibilities given and find the best CCCs values and parameters for each dimensions
def audioPred():
	try:
		#Var for storing differents CCC
		ccc = []
		#Data for the graphic
		tPlt = []
		#Concatenation of Gold Standards
		concGs(False)
		wSize = v.sizeBeg
		while (wSize <= v.sizeMax) :
			wStep = v.stepBeg
			while (wStep <= v.stepMax) :
				print(v.goodColor+"Unimodal prediction in progress : "+str(wSize)+"/"+str(wStep)+"..."+v.endColor)
				#Concatenation of ARFF data
				concRec(wSize, wStep)
				#Normalisation of Features
				normFeatures(wSize,wStep)
				#We try the delay given as global variables
				delay = v.delBeg
				#We prepare the earlystopping for the delays
				earlystop = [3,3]
				bDmU = [None,None]
				bD = [None,None]
				#We open the files for the unimodal prediction
				[tr,de, te] = unimodalPredPrep(wSize, wStep)
				#We open the files for the Gold Standard Matching
				[art, vat, dt] = gsOpen(wSize,wStep, False)
				while (delay <= v.delMax):
					for mGS in range(2):
						#We matche GoldStandards with parameters(wStep/fsize) and stock them
						gs = gsMatch(v.matchGS[mGS], delay, wSize, wStep, art, vat, dt, False)
						for comp in range(len(v.C)):
							#We do the prediction
							[cccDev, pred] = unimodalPredDev(gs, v.C[comp], tr, de, earlystop)
							#Post-treatement
							[cccSave, biasB, scaleB, bias, scale] = postTreatDev(cccDev, pred, gs, earlystop)
							#We store the results
							ccc.append([round(wSize,2), round(wStep,2), round(cccSave[0],2), round(cccSave[1],2)
							, round(delay,2), v.C[comp], v.matchGS[mGS], biasB, scaleB, bias[0], bias[1], scale[0], scale[1]])
					#We get the best CCC for all the delay [0] Arousal/ [1] Valence
					bDelay = bestdelay(ccc, wSize, wStep, delay)
					#We see if we must earlystop or not
					if (earlyStopDelay(earlystop, bDmU, bD, bDelay)) :
						break
					delay += v.delStep
				print(v.goodColor+"Unimodal prediction finished : window size:"+str(wSize)+" window step:"+str(wStep)+v.endColor)
				bA, bV = bestVal(ccc, wSize, wStep)
				tPlt.append([wSize, wStep, bA, bV])
				#We write in this file for keeping a trace of what we do
				f = open("./ccc.txt","wb").write(str(ccc))
				wStep += v.stepStep
			wSize += v.sizeStep
		printBestVal(ccc, tPlt)
	except KeyboardInterrupt :
		printBestVal(ccc, tPlt)
		raise
#End audioPred

setup()
audioPred()