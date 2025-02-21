#!/bin/bash
set -o errexit # Exit on error

#### Extract results ####
# Script used to extract timer info into csv file from tracy raw data :
# 1. Use tracy-csvexport to dump csv files in ${WORK_DIR}/output/tracy.csv/
#########################
usage() {
    echo "Usage: extract-results.sh <workdir> <outputdir> <tracyoutputdir> <perf.scenes-file> "
}

if [ "$#" -eq 4 ]; then
    WORK_DIR=$1 
    SCRIPT_DIR=$WORK_DIR/PerformanceRegression
    OUTPUT_DIR=$2
    TRACY_RAW_DIR=$3
    PERF_FILE=$4
    CSV_DIR=$OUTPUT_DIR/tracy.csv
else
    usage; exit 1
fi


mkdir $CSV_DIR
cd $CSV_DIR

nbTrialsToWaitForTracy=5

echo "Extracting all tracy files to $CSV_DIR..."
while IFS= read -r line; do

    SCENE_PATH_LOCAL=$(echo "$line" | awk '{print $1}')
    SCENE_PATH=$SOURCE_DIR/$SCENE_PATH_LOCAL
    SCENE_NAME=$(echo "$SCENE_PATH" | awk -F '/' '{print $NF}' | awk -F '.' '{print $1}')
    NB_TRIALS=$(echo "$line" | awk '{print $4}')


    if [ ! -f "$SCENE_PATH" ]; then
        echo "[WARNING] Skipping scene $SCENE_PATH because it doesn't exist"
        echo "- If the scene $SCENE_PATH has been renamed since this version of SOFA, think about adding the renaming in the patch"
        echo ""
        continue
    fi

    for i in $(seq $NB_TRIALS)
    do 
        file=$TRACY_RAW_DIR/${SCENE_NAME}_$i.tracy
        tests=0
        #The dump of the file on the disk might take more time than changing script, this might break the execution here so we enable waiting
        while [ ! -f "$file" ] && (( $tests < $nbTrialsToWaitForTracy )); do
            ((++tests))
            echo "File $file hasn't already been poduced. Waiting 2s for tracy to produce it..."
            sleep 2
        done
        if [ -f "$file" ];then
            # echo "Extracting $file to $SCENE_NAME_$i.csv"
            tracy-csvexport -u  $file  > ${SCENE_NAME}_$i.csv 2>&1
        else
           echo "File $file hasn't been poduced in time."
           exit 1 
        fi
    done
done < $PERF_FILE 


export PR_EXTRACT_RESULTS_OUTPUT_DIR=$CSV_DIR

echo "Exported variable are : "
echo "PR_EXTRACT_RESULTS_OUTPUT_DIR=$PR_EXTRACT_RESULTS_OUTPUT_DIR"
echo ""
