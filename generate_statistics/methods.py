import csv
import sys
import os
import numpy as np 


def loadCVSIntoDictionary(csvFileName,startingStep=1):
    # outputDict is a dictionary which key is the timer name as in the csv file
    # The elements in the dictionnary are a tuple of size 3 :
    # (CPP file name containing the timer (used to define if it is a FreeMotionAnimaitonLoop or not), [list of elaped time], [list of timestamp])
    csvfile=open(csvFileName,mode="r")
    reader = csv.reader(csvfile,delimiter=',')
    outputDict={}
    
    firstLine = True

    # Look for the timestemp of the startingStep'th time step of the simulation 
    # WARNING : This can be considerated weak as it depends on the timer "Simulation::animate"
    # This is necessary because we don't know how many time a timer will be called every timestep (except for this one), 
    # so we cannot simply remove the startingStep'th first occurence of every timer

    id = 0
    startTimeStep = None
    for row in reader:
        if(row[0] == "Simulation::animate"):
            id += 1 
            if(id == startingStep):
                startTimeStep = int(row[3])
                break
    if(startTimeStep is None):
        if(id == 0):
            print(f"[ERROR] loadCVSIntoDictionary, while reading the file " +csvFileName+ f" : the timer \"Simulation::animate\" was not exported, the timestamp of the {startingStep}th timestep cannot be found.")
        else:
            print(f"[ERROR] loadCVSIntoDictionary, while reading the file " +csvFileName+ f" : the starting step {startingStep} is certainly greater thant the number of steps.")
        exit(1)

    # We need to restart the reader 
    csvfile.close()
    csvfile=open(csvFileName,mode="r")
    reader = csv.reader(csvfile,delimiter=',')

    for row in reader:

        # First line of Tracy CSV conatins column labels
        if firstLine:
            firstLine = False
            continue
        
        # row[0] containes the timer name
        # row[4] containes the time spent in the timer. 
        # row[3] containes the elapsed time since the begining of the simulation
        # We might want to make it more robust by finding out the column number thank's to the first line labels
        if(int(row[3])<startTimeStep):
            continue
        if(row[0] not in outputDict):
            outputDict[row[0]] = (row[1],[int(row[4])],[int(row[3])])
        else:
            outputDict[row[0]][1].append(int(row[4]))
            outputDict[row[0]][2].append(int(row[3]))

    return outputDict

def isFreeMotionAL(tracyData):
    if(("UpdateBBox" in tracyData) and ("DefaultAnimationLoop.cpp" in tracyData["UpdateBBox"][0])):
        return False
    return True

def computeSingleData(rawData, applyDivisor = 1):
    # rawData is a np array containing time values at each time step for each execution
    percentiles = np.percentile(rawData,[25,50,75])
    # Return vector is constituted this way : [min, max, mean, std, first quartile, second quartile, third quartile]
    return [np.min(rawData)/applyDivisor, np.max(rawData)/applyDivisor, np.mean(rawData)/applyDivisor, np.std(rawData)/applyDivisor, percentiles[0]/applyDivisor, percentiles[1]/applyDivisor, percentiles[2]/applyDivisor]

def loadTimerFile(timersFile):
    # Output file looks like that : 
    # For a timer file with a line like this one : 
    # "Timer1Name=subTimer1+subTimer2"
    # { "Timer1Name" : ['+', subTimer1, subTimer2, ...],... }
    #
    # For a timer that is defined by two timepoints
    # "Timer1Name=subTimer1-subTimer2"
    # { "Timer1Name" : ['-', subTimer1, subTimer2 ],... }
    #
    # For a unique timer 
    # "Timer1Name=subTimer1"
    # { "Timer1Name" : [subTimer1 ],... }

    rawtimers = open(timersFile)
    timers = {}
    for line in rawtimers:
        temp = line.strip().split('=') 
        plusTimers = temp[1].split('+')
        minusTimers = temp[1].split('-')

        if(len(plusTimers) != 1 ):
            if(len(minusTimers) !=1):
                print("[ERROR] timer file is wrongly formed, an expression cannot contain a - and a +")
                exit(1)
            timers[temp[0]] = ['+', *plusTimers ]
        elif(len(minusTimers) !=1):
            timers[temp[0]] = ['-', *minusTimers ]
        else:
            timers[temp[0]] = plusTimers

    return timers

def processFile(tracyData,timers,sceneName="default"):
    # timers is the output of loadTimerFile
    # tracyData is the output of loadCVSIntoDictionary
    processedData = {}


    #For each output timer name 
    for timer in timers:
        try:
            if(len(timers[timer])==1):
                temp = np.array(tracyData[timers[timer][0]][1])
            else:
                # We have a timer that need subtimer to be computed

                if(timers[timer][0] == '+'):
                    temp = np.array(tracyData[timers[timer][1]][1])
                    # Now we add all other timers
                    for subTimer in timers[timer][2:]:
                        temp += np.array(tracyData[subTimer][1])
                else:
                    # We use timestamps 
                    temp = np.array(tracyData[timers[timer][1]][2])
                    # We substract the other timestamp
                    temp -= np.array(tracyData[timers[timer][2]][2])
                    # Because this is used for timers coming from events : SetBegin, StepEnd we don't want to take into account what is done by the users through the timers but what is done in between
                    # So we remove the time execution of the first timer
                    temp -= np.array(tracyData[timers[timer][1]][1])

            processedData[timer] = computeSingleData(temp,1000000) #Nano seconds
        except KeyError as e:
            if(timer == "CollisionDetection"):
                print("[WARNING] processFile : Expected timer name " + str(e) + " isn't in the csv file of the scene "+ sceneName +". It means that it wasn't exported by Tracy. The timer might not exist in this version of SOFA. It is used to compute " + timer + " that might be missing if no collision pipeline is present in the scene." )
                continue
            else:
                print("[ERROR] processFile : Expected timer name " + str(e) + " isn't in the csv file of the scene "+ sceneName +". It means that it wasn't exported by Tracy. The timer might not exist in this version of SOFA.")
                exit(1)

    return processedData

def exportToCSV(processedData,outputfile,timersDicts):
    ### IMPORTANT must be kept coherant with what is done in computeSingleData
    dataOrder = ["min","max","mean","std","quartile1","quartile2","quartile3"]

    #Create a unique list of all timers labels for the columns names (merging labels from all simulations)
    uniqueLabels = []
    for timerDict in timersDicts:
        for label in timerDict:
            if(label not in uniqueLabels):
                uniqueLabels.append(label)

    csvfile=open(outputfile,mode="w")
    writer = csv.writer(csvfile,delimiter=',')

    #Post fix label with data type (mean, std etc...)
    uniqueLabelsPostfixed = [(label + "_" + dataType) for label in uniqueLabels for dataType in dataOrder ]


    writer.writerow(["SceneName",*uniqueLabelsPostfixed])

    # This is used to add NaN whrn the timer doesn't exist for one simulation 
    # This is because we want the csv table to have consistant dimensions
    nanData = ["NaN" for i in range(len(dataOrder))]
 
    for simu in processedData:
        row = [simu]
        for timer in uniqueLabels:
            if(timer in processedData[simu]):
                row = [*row,*processedData[simu][timer]]
            else:
                row = [*row,*nanData]
        writer.writerow(row)

    csvfile.close()

    return