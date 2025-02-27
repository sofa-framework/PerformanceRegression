import csv
import numpy as np
from os import listdir
from os.path import isfile, join
import re
import time
import datetime

class FullStatSnap():

    class DataSample():
        minmax : tuple[float,float]
        meanstd : tuple[float,float]
        quartiles : tuple[float,float,float]
        cardinality : int

        def __init__(self, minmax:tuple[float,float], meanstd:tuple[float,float], quartiles:tuple[float,float,float], cardinality:int):
            self.minmax       = minmax
            self.meanstd      = meanstd
            self.quartiles    = quartiles
            self.cardinality    = cardinality
            pass

    fullHash : str                        # Either the hash or the release version
    dateTime : datetime.datetime          # Time of the commit (Day of the beginning of the month if release)
    sceneNames : list[str]                # List of all scenes run for this commit
    sceneTimers : list[list[int]]         # One list of index per scene. Each list are index of timers in the list timerNames by the order of samples
    sceneSamples : list[list[DataSample]] # One list of sample per scene. In the same order as sceneTimers
    timerNames : list[str]                # Unique list of timer names of all scenes
    hardInfo : list[str]                  # List of lines of the hard info file

    def __init__(self, fullHash='', dateTime=None):
        self.fullHash     = fullHash
        self.dateTime   = dateTime
        self.sceneNames   = []
        self.sceneTimers  = []
        self.sceneSamples = []
        self.timerNames   = []
        self.hardInfo     = []

    def setHashAndTime(self,fullHash='', dateTime=None):
        self.fullHash = fullHash
        self.dateTime = dateTime

    def setHardInfo(self,hardInfo:list[str]):
        self.hardInfo = hardInfo

    def getSceneDataSamples(self,sceneName):
        try:
            sceneId = self.sceneNames.index(sceneName)
        except(ValueError):
            return None, None
        timerNames = [ self.timerNames[i] for i in self.sceneTimers[sceneId]]
        samples = self.sceneSamples[sceneId]
        return timerNames, samples

    def addScene(self, sceneName:str, timerNames:list[str], sampleList:list[DataSample]):
        self.sceneNames.append(sceneName)
        self.sceneTimers.append([])
        self.sceneSamples.append(sampleList)
        # Merge new labels with existing ones
        for timer in timerNames:

            try: # Compliance to Python's EAFP principle
                timerId = self.timerNames.index(timer)
                self.sceneTimers[-1].append(timerId)
            except(ValueError): # If not found we add it and we use the new ID
                self.timerNames.append(timer)
                self.sceneTimers[-1].append(len(self.timerNames)-1)
                continue






def loadCSVStatistic(filename):

    csvfile=open(filename,mode="r")
    reader = csv.reader(csvfile,delimiter=',')

    firstLine = True

    # map of maps
    # First key = scene name
    # second key = timer label
    # {"sceneName1" : { "timer1" : [[min,max], [mean,std], [quartile1,quartile2,quartile3]],
    #                   "timer2" : [[min,max], [mean,std], [quartile1,quartile2,quartile3]]},
    #  "sceneName2" : { "timer1" : [[min,max], [mean,std], [quartile1,quartile2,quartile3]],
    #                   "timer2" : [[min,max], [mean,std], [quartile1,quartile2,quartile3]]}}
    outputMap = FullStatSnap()

    for row in reader:
        sceneName = row[0]

        # First line of CSV contains labels
        if firstLine:
            firstLine = False
            # We expect labels to be sorted this way : label_min,label_max,label_mean,label_std,label_quartile1,label_quartile2,label_quartile3,cardinality
            # See method computeSingleData in generate_statistics/methods.py
            # POTENTIAL TODO: Make this parametrizable in a parameter file to avoid weak link like that.
            labels = [row[1 + i*8].split('_')[0] for i in range(len(row)//8)]

        else:
            samples = []
            sceneLabels = []
            for i in range(len(row)//8):
                if( not row[1 + i*8 + 0] == "NaN" ):
                    sceneLabels.append(labels[i])
                    samples.append(FullStatSnap.DataSample( (float(row[1 + i*8 + 0]),float(row[1 + i*8 + 1])),
                                                           (float(row[1 + i*8 + 2]),float(row[1 + i*8 + 3])),
                                                           (float(row[1 + i*8 + 4]),float(row[1 + i*8 + 5]),float(row[1 + i*8 + 6])),
                                                            (int(row[1 + i*8 + 7]))))

            outputMap.addScene(sceneName,sceneLabels,samples)

    return outputMap



def loadAllResults(resultsDir):
    # Create four lists : one for release
    #                   : one for commits
    #                   : two for dates of commits to be sorted regarding their date (one per data list)
    releaseData : list[FullStatSnap] = []
    releaseDate : list[str]          = []
    commitData  : list[FullStatSnap] = []
    commitDate  : list[str]          = []
    for f in listdir(resultsDir):
        if(isfile(join(resultsDir, f)) and ('.csv' in f)):
            #define either commit of release
            isRelease = re.match("v[0-9]{2}.[0-9]{2}.csv",f) is not None

            if(isRelease):
                releaseData.append(loadCSVStatistic(join(resultsDir, f)))
                formatedDateAndTime = f'20{f.split('.')[0][1:]}-{f.split('.')[1]}-01'
                releaseDate.append(formatedDateAndTime)
                releaseData[-1].setHashAndTime(f.split('.')[0]+'.'+f.split('.')[1],datetime.datetime.fromisoformat(formatedDateAndTime))

                #Add hardinfo
                hardInfo = []
                with open(join(resultsDir,f.split('.')[0] + '.' +f.split('.')[1]) + '.info', 'r') as file:
                    hardInfo = file.read().split('\n')
                releaseData[-1].setHardInfo(hardInfo)

            else:
                _cdate = f.split('_')[1]
                _ctime = f.split('_')[-1].split('.')[0]

                commitDate.append(_cdate+'_'+_ctime)
                formatedDateAndTime = _cdate+'T'+_ctime.replace('-',':')

                #Append the new FullStatSnap
                commitData.append(loadCSVStatistic(join(resultsDir, f)))
                commitData[-1].setHashAndTime(f.split('_')[0],datetime.datetime.fromisoformat(formatedDateAndTime))

                #Add hardinfo
                hardInfo = []
                with open(join(resultsDir,f.split('_')[0])+ '.info', 'r') as file:
                    hardInfo = file.read().split('\n')
                commitData[-1].setHardInfo(hardInfo)

    #Add master head as a release
    releaseIdx = np.argsort(releaseDate).tolist()
    commitIdx = np.argsort(commitDate).tolist()

    if(len(commitIdx) != 0):
        releaseData.append(commitData[commitIdx[-1]])
        releaseIdx.append(len(releaseData) -1)


    return releaseData, commitData, releaseIdx, commitIdx

def getUniqueSetOfLabels(dataStruct : list[FullStatSnap],indices : list[int], sceneName : str):

    timers : list[str] = []
    for i in indices:
        try:
            sceneIdx = dataStruct[i].sceneNames.index(sceneName)
        except(ValueError):
            print(f'[Warning] no scene named {sceneName} in {dataStruct[i].fullHash}')
            continue
        for timerID in dataStruct[i].sceneTimers[sceneIdx]:
            if(dataStruct[i].timerNames[timerID] not in timers ):
                timers.append(dataStruct[i].timerNames[timerID])

    return timers

def getUniqueSetOfScenes(dataStruct : list[FullStatSnap],indices : list[int]):

    sceneNames : list[str] = []
    for i in indices:
        for name in dataStruct[i].sceneNames:
            if(name not in sceneNames ):
                sceneNames.append(name)

    return sceneNames



# sortedIdx : should be a list of index ordering the data in term of date
# return id in the sortedIdx of the first FullStatSnap which date is more recent than given date
def findFirstAvailableIdOlderThanDate(data : list[FullStatSnap], sortedIdx : list[int], date : datetime.datetime ):
    if((len(data) < 1) or (date>data[sortedIdx[-1]].dateTime)):
        return None

    #Findout if we start from tail or head
    sartFromTail = abs(date - data[sortedIdx[0]].dateTime) > abs(date - data[sortedIdx[-1]].dateTime)

    if(sartFromTail):
        for i in range(len(data)):
            if(data[sortedIdx[-1 -i]].dateTime<date):
                return len(data) - i
    else:
        for i in range(len(data)):
            if(data[sortedIdx[i]].dateTime>date):
                return i


def computeCommitListIdInDataList(data : list[FullStatSnap], sortedIdx : list[int], date : datetime.datetime, commit_interval :int):
    firstCommit = findFirstAvailableIdOlderThanDate(data,sortedIdx,date)
    i = len(data) -1
    idxInData = []

    if firstCommit is None:
        return []

    while i >= firstCommit:
        idxInData.append(i)
        i-=commit_interval

    idxInData.reverse()
    return [sortedIdx[i] for i in idxInData]

def findCommitId(data : list[FullStatSnap], hash:str):
    for i in range(len(data)):
        if(data[i].fullHash == hash):
            return i
    return -1

# Method: getDataStructureForGraph
# Here the idea is to sort data to be used in box plots.
#
# the inputs are
# 1. data: the FullStatSnap list as outputed by loadAllResults
# 2. ids: ids of the data to extract in the data list
# 3. sceneName: filter for this scene
# 4. labels: Labels to filter
# 5. type: Could be either 'quartiles' or 'mean' depending type of statistics we want to compute.
#
# The outputs are
# 1. Dictionnary
#    - key is the tag label (to be used as the name parameter)
#    - value is a list of either tags/release version to be used as x value in box plots
# 2. Dictionnary
#    - key is the tag label (to be used as the name parameter)
#    - value is a np array with columns being in order : [min, q1, q2, q3, max] (for quartiles modes) and [mean, std] and lines are the values.
def getDataStructureForGraph(data : list[FullStatSnap], ids : list[int], sceneName : str, labels : list[str], type = "quartiles" ):
    xLabelList = {}
    outputStruct = {}

    for label in labels :
        xLabelList[label] = []
        labelIdInSceneLabelList = []
        sceneIdInData = []
        excludeId = []
        for id in ids:
            try:
                currLabelIdInCommitData = data[id].timerNames.index(label)
                currSceneIdInData = data[id].sceneNames.index(sceneName)
                currLabelIdInSceneLabelList = data[id].sceneTimers[currSceneIdInData].index(currLabelIdInCommitData)
            except(ValueError):
                excludeId.append(id) #The scene exists but here doesn't include the right timer or The scene isn't in the commit id
                continue

            currfullHash = data[id].fullHash
            if(len(currfullHash)>7):
                currfullHash = currfullHash[:6]

            xLabelList[label].append(currfullHash)
            labelIdInSceneLabelList.append(currLabelIdInSceneLabelList)
            sceneIdInData.append(currSceneIdInData)

        dataMatrix = np.array([])
        currId = 0
        if(type == "quartiles"):
            dataMatrix = np.zeros((5,len(labelIdInSceneLabelList)))
            for id in ids:
                if id not in excludeId:
                    dataMatrix[0][currId] = data[id].sceneSamples[sceneIdInData[currId]][labelIdInSceneLabelList[currId]].minmax[0]
                    dataMatrix[1][currId] = data[id].sceneSamples[sceneIdInData[currId]][labelIdInSceneLabelList[currId]].quartiles[0]
                    dataMatrix[2][currId] = data[id].sceneSamples[sceneIdInData[currId]][labelIdInSceneLabelList[currId]].quartiles[1]
                    dataMatrix[3][currId] = data[id].sceneSamples[sceneIdInData[currId]][labelIdInSceneLabelList[currId]].quartiles[2]
                    dataMatrix[4][currId] = data[id].sceneSamples[sceneIdInData[currId]][labelIdInSceneLabelList[currId]].minmax[1]
                    currId += 1
        if(type == "mean"):
            dataMatrix =np.zeros((2,len(labelIdInSceneLabelList)))
            for id in ids:
                if id not in excludeId:
                    dataMatrix[0][currId] = data[id].sceneSamples[sceneIdInData[currId]][labelIdInSceneLabelList[currId]].meanstd[0]
                    dataMatrix[1][currId] = data[id].sceneSamples[sceneIdInData[currId]][labelIdInSceneLabelList[currId]].meanstd[1]
                    currId += 1

        outputStruct[label] = dataMatrix

    return xLabelList, outputStruct

class ERROR_TYPE():
    def __init__(self):
        pass

ERROR_RETURNED = ERROR_TYPE()

def tic():
    global ticTS
    ticTS = time.time()

def tac():
    global ticTS
    tac = time.time()
    print(f"{tac - ticTS} secs")


if __name__=="__main__":
    tic()
    releaseData, commitData, sortedReleaseIdx, sortedCommitIdx = loadAllResults("/home/paul/dev/build/PerformanceRegression/PerformanceRegression/old_results/")
    tac()
    tic()
    timers = getUniqueSetOfLabels(releaseData,[0,1,2], "fallingBeamLagrangianCollision")
    tac()
    print(findFirstAvailableIdOlderThanDate(commitData,sortedCommitIdx, datetime.datetime.fromisoformat("2025-05-10T10:50:20")))
    print(findFirstAvailableIdOlderThanDate(commitData,sortedCommitIdx, datetime.datetime.fromisoformat("2024-05-10T10:30:20")))
    print(findFirstAvailableIdOlderThanDate(commitData,sortedCommitIdx, datetime.datetime.fromisoformat("2024-05-09T10:50:20")))
    print(findFirstAvailableIdOlderThanDate(commitData,sortedCommitIdx, datetime.datetime.fromisoformat("2024-04-09T10:50:20")))
    print(timers)