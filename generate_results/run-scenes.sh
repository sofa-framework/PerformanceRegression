#!/bin/bash
set -o errexit # Exit on error

#### Run scenes ####
# Script used to run all scenes and register their time trace :
# 1. Run each scene the number of time specified in the file perf.scenes
#    If specified scene name doesn't exist in the current version of SOFA, it is skipped -> think about using the patches to fix this.
# 2. Record with tracy-capture --> output in ${WORK_DIR}/output/tracy.raw/
# 3. Export current CPU usage of the builder before each launch in files ${WORK_DIR}/output/SceneName_trialNumber_total_CPU_usage.log
####################
usage() {
    echo "Usage: run-scenes.sh <workdir> <builddir> <sofasourcesdir> <perf.scenes-file>"
}

if [ "$#" -eq 4 ]; then
    WORK_DIR=$1 
    SCRIPT_DIR=$WORK_DIR/PerformanceRegression
    BUILD_DIR=$2
    SOURCE_DIR=$3
    PERF_FILE=$4
else
    usage; exit 1
fi



#Create output folder
OUTPUT_DIR=$WORK_DIR/output
mkdir $OUTPUT_DIR
TRACY_OUTPUT=$OUTPUT_DIR/tracy.raw
mkdir $TRACY_OUTPUT

#setup SOFA env
export SOFA_ROOT=$BUILD_DIR

#Launch all scenes
echo "Running all scenes from file $PERF_FILE."
while IFS= read -r line; do

    SCENE_PATH_LOCAL=$(echo "$line" | awk '{print $1}')
    SCENE_PATH=$SOURCE_DIR/$SCENE_PATH_LOCAL
    NB_STEPS=$(echo "$line" | awk '{print $3}')
    NB_TRIALS=$(echo "$line" | awk '{print $4}')
    SCENE_NAME=$(echo "$SCENE_PATH" | awk -F '/' '{print $NF}' | awk -F '.' '{print $1}')

    # Skipped non existing scene
    if [ ! -f "$SCENE_PATH" ]; then
        echo "[WARNING] Skipping scene $SCENE_PATH because it doesn't exist"
        echo "- If the scene $SCENE_PATH has been renamed since this version of SOFA, think about adding the renaming in the patch"
        echo ""
        continue
    fi


    echo "Running $NB_TRIALS times the scene $SCENE_PATH_LOCAL for $NB_STEPS steps..."
    echo "Tracy profiling file is outputed here : $TRACY_OUTPUT/${SCENE_NAME}_i.tracy"
    echo "Logs can be found here : $OUTPUT_DIR/${SCENE_NAME}_i.log"

    for i in $(seq $NB_TRIALS)
    do 
        ps aux --sort=-pcpu > $OUTPUT_DIR/${SCENE_NAME}_${i}_OS_info.log 2>&1 
        top -bn1 | grep '%Cpu' | tail -1 | awk '{print $2}' > $OUTPUT_DIR/${SCENE_NAME}_${i}_total_CPU_usage.log 2>&1
        # Scene execution is timeouted to avoid being stuck by segfaults
        # TODO: Parametrize timeout value in perf.scenes file
        timeout -k 60 600 tracy-capture -o $TRACY_OUTPUT/${SCENE_NAME}_$i.tracy > /dev/null &
        pid=$!
        $BUILD_DIR/bin/runSofa $SCENE_PATH -g batch -n $NB_STEPS > $OUTPUT_DIR/${SCENE_NAME}_$i.log 2>&1 
        wait $pid
    done

    echo "Scene $SCENE_NAME done !"
    echo ""

done < $PERF_FILE   

echo "All scenes have been executed !"
echo ""

#Add environment variables for the following
export PR_RUN_SCENES_OUTPUT_DIR=$OUTPUT_DIR
export PR_RUN_SCENES_TRACY_OUTPUT_DIR=$TRACY_OUTPUT


echo "Exported variable are : "
echo "PR_RUN_SCENES_OUTPUT_DIR=$PR_RUN_SCENES_OUTPUT_DIR"
echo "PR_RUN_SCENES_TRACY_OUTPUT_DIR=$PR_RUN_SCENES_TRACY_OUTPUT_DIR"
echo ""




