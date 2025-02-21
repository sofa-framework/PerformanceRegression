import csv
import sys
import os
from methods import *
from github import Auth
from github import Github


#### Process CSV ####
# brief: This script transform tracy data in csv format into statistical data to be read and displayed byt he dashboard.
#
#
# inputs:
# - workdir: work directory where the script can right files
# - sofaSourceDir: Directory containing SOFA sources used for the compilation
# - perffile: path to the perffile 'perf.scenes' used to generate the tracy data
# - defaultTimersFile: file containing description of the timer computation of DefaultAnimationLoop scenes 'default.timers'
# - lagrangianTimersFile: file containing description of the timer computation of FreeMotionAnimationLoop scenes 'freemotion.timers'
# - outputdir: Directory where the generated statistic should be written
# - csvdir: Directory containing the csv files of tracy data
# - full_hash: Full hash of the tested commit
# - branch_name: Tested branch name
# - github_token: github token with read only access to repository sofa-framework/sofa
#
# outputs :
# - One file containing statistic data in csv format :
#   - Lines are scenes
#   - Column are the result of the cartesian product between the timers names and the statistic type
#   - e.g. :
#              | Timer1_mean | Timer1_std | Timer2_mean | Timer2_std
#       Scene1 |
#       Scene2 |
#
# details:
# - Timer names are the list of unique timer names from both default.timer and freemotion.timer files.
# - The statistic data are defined in the method 'computeSingleData' in the file 'methods.py'
# - One strong assumption is made to define weather the scene currently being treated is using a DefaultAnimationLoop or
#   a FreeMotionAnimationLoop. The assumption is that the timer 'UpdateBBox' is sent in the file "DefaultAnimationLoop.cpp"
# - One hot fix was necessary : the timer "CollisionReset" is send one time before the scene starts, this is an issue of
#   SOFA calling the method CollisionReset once before the simulation starts. This is manually solved.
#
#
#####################

if(len(sys.argv) == 11):
    wordir = sys.argv[1]
    sofaSourceDir = sys.argv[2]
    perffile = sys.argv[3]
    defaultTimersFile = sys.argv[4]
    lagrangianTimersFile = sys.argv[5]
    outputdir = sys.argv[6]
    csvdir = sys.argv[7]
    full_hash = sys.argv[8]
    branch_name = sys.argv[9]
    github_token = sys.argv[10]
else:
    print("usage : python3 process_csv.py <workdir> <sofasourcedir> <perf.scenes-file> <default.timers-file> <lagrangian.timers-file> <outputdir> <csvdir> <full_hash> <branch_name>")

# Read per file to gather the names of the simulation  and the number of execution
with open(perffile) as file:
    lines = [line.rstrip().split(' ') for line in file]

# Read timer files to compute the timer values afterwards. 
# File structure : { "Timer1Name" : [subTimer1, subTimer2 ],... }
# Sub timers are added when cumputing Timer1
defaultTimers = loadTimerFile(defaultTimersFile)
lagrangianTimers = loadTimerFile(lagrangianTimersFile)

processedData={}

# Now process each simulation from perf file
for line in lines:
    if not os.path.isfile(sofaSourceDir + "/" + line[0]):
        print("[WARNING] Skipping scene " + line[0] + " because it doesn't exist")
        print("- If the scene " + line[0] + " has been renamed since this version of SOFA, think about adding the renaming in the patch")
        print()
        continue

    cvsFile = line[0].split('/')[-1]
    cvsFile = cvsFile.split('.')[0] 

    tracyData = None
    simulationType = None

    CPUData = []

    # For each execution of this simulation (second value after the scene path in the perf file)
    for i in range(int(line[3])):

        cvsFileName = csvdir + "/" + cvsFile + "_" + str(i+1) + ".csv"

        # Output look like that : { "TimerName" : list[int] (time spent in each occurence of this time in the simulation),...}
        temp = loadCVSIntoDictionary(cvsFileName,int(line[1]))

        # Small optim to test if it is a lagrangian based simulation only once for each execution
        # WARNING : This test is weak and depends on what file the UpdateBBox timer is located 
        # FMAL: FreeMotionAnimationLoop
        # DAL: DefaultAnimationLoop
        if(simulationType is None):
            if isFreeMotionAL(temp):
                simulationType = "FMAL"
            else:
                simulationType = "DAL"

        ### WARNING HOT FIX ###
        # We know CollisionReset is called at init so the vector of data will have more data point then the other one, we need to remove the first ones
        if((simulationType == "FMAL") and ("CollisionReset" in temp)):
            sizeDiff = len(temp["CollisionReset"][1]) - len(temp["CollisionDetection"][1])
            for j in range(sizeDiff):
                temp["CollisionReset"][1].pop(0)
                temp["CollisionReset"][2].pop(0)
        ##### HOT FIX END #####

        # Append all timer data to global vector
        if(tracyData is None):
            tracyData = temp
        else:
            for label in tracyData:
                tracyData[label][1].extend(temp[label][1])
                tracyData[label][2].extend(temp[label][2])

        #Add CPU usage for file
        cpuUsageFile = outputdir + '/' + cvsFile + "_" + str(i+1) + "_total_CPU_usage.log"
        with open(cpuUsageFile) as CPUFile:
            CPUData.append(float(CPUFile.readline().replace(',','.')))

    # Now that the timers data from each execution of the current simulation have been concatenated into tracyData, we can process it
    # This computes the statistics per timer by using the forumla given in the timers files
    if(simulationType == "FMAL"):
        processedData[cvsFile] = processFile(tracyData,lagrangianTimers,cvsFile)
    else:
        processedData[cvsFile] = processFile(tracyData,defaultTimers,cvsFile)

    processedData[cvsFile]["CPUUsage"] = computeSingleData(CPUData)


##Create csv name
if(branch_name[0] == "v"): #This is a release
    outputFileName = branch_name
else:
    ##Gather date information
    auth = Auth.Token(github_token)
    g = Github(auth=auth)
    repo = g.get_repo("sofa-framework/sofa")
    commit = repo.get_commit(full_hash)
    commit_date = commit.last_modified_datetime
    dateString = f"{commit_date.year}-{commit_date.month:02.0f}-{commit_date.day:02.0f}_{commit_date.hour:02.0f}-{commit_date.minute:02.0f}-{commit_date.second:02.0f}"
    outputFileName = f"{full_hash}_{dateString}"

exportToCSV(processedData,outputdir+"/" + outputFileName + ".csv",[defaultTimers,lagrangianTimers,{"CPUUsage":None}])
