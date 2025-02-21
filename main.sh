#!/bin/bash
set -o errexit # Exit on error

#### Requirements ####
# SOFA : Dependencies to build SOFA without openGl, Qt, and no plugin. See https://sofa-framework.github.io/doc/getting-started/build/linux/
#
# Tracy : a compiled version of the tracy-cvsexporter and tracy-capture of the same version of the one currently used by SOFA and their path added to the system PATH
#
# Python3 : Version 3.12 + PyGithub
#
# ccache: By default ccache is used, it is recommended to have it installed
#
# inxi for machine info
######################



#### Main script ####
# brief: This script is used to launch the full pipeline of performance testing for one specific commit or branch.
#        It is parametrized by three files :
#        - perf.scenes : List of  "${scene name} ${starting time step to record} ${nax time step} ${number of scene launch}
#        - default.timers : timers to be used for statistics for scenes that uses a DefaultAnimationLoop. It allows to
#                           redefine the timer name using the syntax TimeNameInStats=TimerNameInSOFA. You can also use
#                           simple addition and subtraction of timer names on the right-hand side
#                           e.g : "CollisionDetection=CollisionEndEvent-CollisionBeginEvent"
#                           or "ProjectAndMechaMap=ProjectAndPropagateDx+ProjectAndPropagateXAndV".
#                           Subtraction uses timestamp and addition time spawn. This has been added to be able to have
#                           a unified notation between those timers an the ones from FreeMotionAnimaitonLoop scenes
#        - freemotion.timers : Same than the last one but for scenes with FreeMotionAnimationLoop
#
# inputs:
# - workdir     (required): directory used to store all working files. Where folders build, sofa, and output will be created.
# - sofa-branch (required): branch to test
# - commit-hash (optional): specific commit to test, if none is given, the tip of the branch will be tested.
#
# env:
# - RO_GITHUB_TOKEN: a read only github token
#
# outputs:
# - log files in the folder $WORK_DIR/logs
# - computed statistic : in a file named after the commit hash with the commit date and time (or the release version if
#                        only a branch is given and its name follows the release naming convention vXX.XX).
#                        e.g. sha_yyyy-mm-dd_hh-mm-ss.csv.
#                        The statistics are formated in a matrix which lines are the scenes names defined in perf.scenes
#                        and column are the results of the cartesian product between the timer names present in the
#                        files `default.timers` and `freemotion.timers` and all the type of statistics defined in
#                        generate_statistics/methods.py:computeSingleData.
# - hardware info : hardware information of the computer who generated the results. Same naming convention except that no date or time is added.
#
# Note that the statistic file and hard info file are copied in the repository in folder old_results to be ready to commit them
#####################
usage() {
    echo "Usage: main.sh <workdir> <sofa-branch> <commit-hash>"
}

if [ "$#" -ge 2 ]; then
    WORK_DIR=$1 
    SCRIPT_DIR=$WORK_DIR/PerformanceRegression
    BRANCH=$2
    if [ "$#" -eq 3 ]; then 
        HASH=$3
    else
        HASH="latest"
    fi
else
    usage; exit 1
fi

if [[ -z "${RO_GITHUB_TOKEN}" ]]; then
    echo "ERROR: environment variable RO_GITHUB_TOKEN should be set with a github token with read access to repository sofa-framework/sofa"
    exit 1
fi


# Add informations to Log
lshw > $WORK_DIR/hardware.log
apt --installed list > $WORK_DIR/software.log


##### GENERATE DATA #####
# Setup action (clone + build sofa)
echo "Calling '$SCRIPT_DIR/setup_action/action-setup.sh "$WORK_DIR" $BRANCH $HASH'"
. $SCRIPT_DIR/setup_action/action-setup.sh "$WORK_DIR" $BRANCH $HASH
echo ""

# Launch all scenes given perf.scenes file + record tracy timers
echo "Calling '$SCRIPT_DIR/generate_results/run-scenes.sh $WORK_DIR $PR_SETUP_SOFA_BUILD $PR_SETUP_SOFA_SOURCES $SCRIPT_DIR/perf.scenes'"
. $SCRIPT_DIR/generate_results/run-scenes.sh "$WORK_DIR" "$PR_SETUP_SOFA_BUILD" "$PR_SETUP_SOFA_SOURCES" "$SCRIPT_DIR/perf.scenes"
echo ""

# Exctract tracy datas into csv files
echo "Calling '$SCRIPT_DIR/generate_results/extract-results.sh $WORK_DIR $PR_RUN_SCENES_OUTPUT_DIR $PR_RUN_SCENES_TRACY_OUTPUT_DIR $SCRIPT_DIR/perf.scenes'"
. $SCRIPT_DIR/generate_results/extract-results.sh "$WORK_DIR" "$PR_RUN_SCENES_OUTPUT_DIR" "$PR_RUN_SCENES_TRACY_OUTPUT_DIR" "$SCRIPT_DIR/perf.scenes"
echo ""

##### GENERATE STATISTICS #####
echo "Processing CSV files to compute statistics..."
echo "Calling 'python3 $SCRIPT_DIR/generate_statistics/process_csv.py $WORK_DIR $PR_SETUP_SOFA_SOURCES $SCRIPT_DIR/perf.scenes $SCRIPT_DIR/default.timers $SCRIPT_DIR/freemotion.timers $PR_RUN_SCENES_OUTPUT_DIR $PR_EXTRACT_RESULTS_OUTPUT_DIR $PR_SETUP_FULL_HASH $BRANCH HIDDEN_RO_GITHUB_TOKEN  > process_csv.log 2>&1 '"
python3 $SCRIPT_DIR/generate_statistics/process_csv.py "$WORK_DIR" "$PR_SETUP_SOFA_SOURCES" "$SCRIPT_DIR/perf.scenes" "$SCRIPT_DIR/default.timers" "$SCRIPT_DIR/freemotion.timers" "$PR_RUN_SCENES_OUTPUT_DIR" "$PR_EXTRACT_RESULTS_OUTPUT_DIR" "$PR_SETUP_FULL_HASH" "$BRANCH" "$RO_GITHUB_TOKEN" > $WORK_DIR/process_csv.log 2>&1
echo "CSV files processed ! Stats are saved in file $PR_RUN_SCENES_OUTPUT_DIR/$PR_SETUP_FULL_HASH.csv"
echo ""

##### GENERATE INFO FILE
echo "Calling 'inxi -v3 -c0 > $PR_RUN_SCENES_OUTPUT_DIR/$PR_SETUP_FULL_HASH.info'"
inxi -v3 -c0 > $PR_RUN_SCENES_OUTPUT_DIR/$PR_SETUP_FULL_HASH.info
echo ""

##### PUBLISH RESULTS #####
echo "Calling '$SCRIPT_DIR/generate_results/save-results.sh $WORK_DIR $SCRIPT_DIR $PR_RUN_SCENES_OUTPUT_DIR $PR_SETUP_FULL_HASH'"
. $SCRIPT_DIR/generate_results/save-results.sh "$WORK_DIR" "$SCRIPT_DIR" "$PR_RUN_SCENES_OUTPUT_DIR" "$PR_SETUP_FULL_HASH"
echo ""

# Add informations to Log
env | grep PR_ > $WORK_DIR/env.log

