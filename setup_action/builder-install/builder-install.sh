#!/bin/bash

INSTALL_SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

#Install dependencies
sudo apt install -y git net-tools wget curl ca-certificates zip unzip patchelf inxi tar dbus*
sudo apt install -y libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev
sudo apt install -y build-essential software-properties-common cmake ninja-build ccache
sudo apt install -y libtinyxml2-dev libopengl0 libboost-all-dev libeigen3-dev

sudo apt install -y libpng-dev libjpeg-dev libtiff-dev libglew-dev zlib1g-dev libsuitesparse-dev
sudo apt install -y python3.12-venv python3.12-full


python3.12 -m venv SOFA
source ~/SOFA/bin/activate
python3.12 -m ensurepip
python3.12 -m pip install --upgrade pip
python3.12 -m pip install numpy scipy matplotlib pybind11==2.11.1 mypy pybind11-stubgen PyGithub

#Install Tracy
mkdir Tracy && cd Tracy
git clone --depth 1 --branch v0.11.1 https://github.com/wolfpld/tracy.git
cd tracy && TRACY_SRC=$(pwd)

cd csvexport
mkdir build && cd build
cmake ../ && make -j 4
TRACY_CSVEXPORT=$(pwd)

cd ${TRACY_SRC}/capture
mkdir build && cd build
cmake ../ && make -j 4
TRACY_CAPTURE=$(pwd)

#Install github builder
cd ~
mkdir actions-runner && cd actions-runner
RUNNER_DIR=$(pwd)
curl -o actions-runner-linux-x64-2.322.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.322.0/actions-runner-linux-x64-2.322.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.322.0.tar.gz

## Still need to configure it see https://github.com/sofa-framework/PerformanceRegression/settings/actions/runners/new



#Modify global environment
## Add pre and post build scripts
mkdir actions-scripts
cd actions-scripts
ACTION_SCRIPTS_DIR=$(pwd)
cp $INSTALL_SCRIPT_DIR/github-hookups/pre-build.sh $ACTION_SCRIPTS_DIR
cp $INSTALL_SCRIPT_DIR/github-hookups/post-build.sh $ACTION_SCRIPTS_DIR


echo "PATH=$PATH:$TRACY_CSVEXPORT:$TRACY_CAPTURE" >> $RUNNER_DIR/.env
echo "ACTIONS_RUNNER_HOOK_JOB_STARTED=$ACTION_SCRIPTS_DIR/pre-build.sh" >> $RUNNER_DIR/.env
echo "ACTIONS_RUNNER_HOOK_JOB_COMPLETED=$ACTION_SCRIPTS_DIR/post-build.sh" >> $RUNNER_DIR/.env
echo "RUNNER_ACTIONS_RUNNER_DIRECTORY=$RUNNER_DIR" >> $RUNNER_DIR/.env
