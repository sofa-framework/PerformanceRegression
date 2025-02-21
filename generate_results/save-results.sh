#!/bin/bash
set -o errexit # Exit on error

#### Save results ####
# Script used to copy all files in the ${WORK_DIR}/output with prefix being the fullhash in the folder old_results in the repository
######################
usage() {
    echo "Usage: publish.sh <workdir> <scriptdir> <outputfolder> <commithash>"
}

if [ "$#" -eq 4 ]; then
    WORK_DIR=$1 
    SCRIPT_DIR=$2
    OUTPUT_FOLDER=$3
    COMMIT_HASH=$4
else
    usage; exit 1
fi

if [ ! -d "$SCRIPT_DIR/old_results/" ]; then
    mkdir $SCRIPT_DIR/old_results/
fi

echo "Copying all files prefixed with $COMMIT_HASH in folder $OUTPUT_FOLDER to $SCRIPT_DIR/old_results/"

cp -f $OUTPUT_FOLDER/${COMMIT_HASH}* $SCRIPT_DIR/old_results/

echo "Results ready to be pushed !"
echo ""


