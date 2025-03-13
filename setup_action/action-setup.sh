#!/bin/bash
set -o errexit # Exit on error



#### Action setup ####
# Script used to setup the action by doing :
# 1. Clone SOFA in folder ${WORK_DIR}/sofa at given branch + checkout the given commit hash (if none stay at tip)
# 2. Patch sofa if a file with the name of the branch exists in the folder branch-dependency/git-patches
# 3. Setup the project in folder ${WORK_DIR}/build using cmake.
# 4. build using Ninja
# 5. Export some variables
######################
usage() {
    echo "Usage: action-setup.sh <workdir> <sofa-branch> <commit-hash>"
}

if [ "$#" -eq 3 ]; then
    WORK_DIR=$1 
    SCRIPT_DIR=$WORK_DIR/PerformanceRegression
    BRANCH=$2
    HASH=$3
else
    usage; exit 1
fi

#setup folders
cd $WORK_DIR
mkdir build
BUILD_DIR=$WORK_DIR/build

#Clone SOFA 
echo "Cloning sofa branch $BRANCH at sha $HASH into folder $WORK_DIR/sofa... Logs can be found there : git.log"

git clone -b $BRANCH --single-branch https://www.github.com/sofa-framework/sofa >> $WORK_DIR/git.log 2>&1
SOURCE_DIR=$WORK_DIR/sofa

cd $SOURCE_DIR 
if [[ "$HASH" != "latest" ]]; then
    git checkout $HASH >> $WORK_DIR/git.log 2>&1
fi

#If this is a release, then we don't care about commit hash
if [[ "$BRANCH" =~ ^v[0-9]{2}\.[0-9]{2}$ ]]; then
  export PR_SETUP_FULL_HASH=$BRANCH
else
  export PR_SETUP_FULL_HASH=$(git rev-parse HEAD)
fi
#Apply patch if it exists for this branch
# TODO: Add tag in patch name (even latest)
if [ -f "$SCRIPT_DIR/branch-dependency/git-patches/$BRANCH.patch" ]; then
    echo "Patching sofa branch $BRANCH with $SCRIPT_DIR/branch-dependency/git-patches/$BRANCH.patch"
    git apply $SCRIPT_DIR/branch-dependency/git-patches/$BRANCH.patch >> $WORK_DIR/git.log 2>&1
fi

echo "Done !"
echo ""


#setup build
echo "Setuping SOFA cmake into folder $BUILD_DIR..."
echo "Logs can be found there : cmake.log"

cd $BUILD_DIR 
cmake $SOURCE_DIR -GNinja -DCMAKE_BUILD_TYPE=Release \
                  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
                  -DSOFA_TRACY=ON \
                  -DSOFA_BUILD_TESTS=OFF -DLIBRARY_SOFA_GL=ON \
                  -DSOFA_FETCH_SOFAGLFW=OFF -DPLUGIN_MULTITHREADING=ON \
                  -DSOFA_FETCH_CSPARSESOLVERS=ON -DSOFA_FETCH_SOFA_METIS=ON \
                  -DPLUGIN_CSPARSESOLVERS=ON -DPLUGIN_SOFA_METIS=ON \
                  -DSOFA_FETCH_BEAMADAPTER=ON -DPLUGIN_BEAMADAPTER=ON \
                  > $WORK_DIR/cmake.log 2>&1
echo "Done !"
echo ""

#build
echo "Building SOFA..."
echo "Logs can be found there : compilation.log"

ninja > $WORK_DIR/compilation.log 2>&1 

echo "Done !"
echo ""

#Add environment variables for the following
export PR_SETUP_SOFA_SOURCES=$SOURCE_DIR
export PR_SETUP_SOFA_BUILD=$BUILD_DIR

echo "Exported variable are : "
echo "PR_SETUP_SOFA_SOURCES=$PR_SETUP_SOFA_SOURCES"
echo "PR_SETUP_SOFA_BUILD=$PR_SETUP_SOFA_BUILD"
echo "PR_SETUP_FULL_HASH=$PR_SETUP_FULL_HASH"
echo ""
