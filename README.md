# Performance regression testing for SOFA

This repository is meant for testing computatioin speed of SOFA Framework. It is constituted of two parts :
1. Scripts to generate computation statistics
2. Script to display the results in a dashboard

The repository serves also as an archive because all te generated results are saved in the folder `old_results` by the action

This plugin has been built to work on Ubuntu, but it might work properly on other OS, it just hasn't been tested.

## Use the action

This script is meant to be launched on a physical self-hosted runner to make sure the running conditions are reproducible. To launch the statistic generation, a workflow-dispatch is available.
Inputs are simple:
1. Sofa branch name (master by default)
2. Commit id (empty by default) --> if none given the tip of the branch is taken

The action is meant to work only with master and releases branches.
The action will then perform the statistic geenration and push them on the repository.



## Use on your own computer

### Statistics generation

#### Dependencies
If you want to run the statistic generation on your own computer, those are the dependencies :
- **SOFA:** Dependencies to build SOFA without openGl, Qt, and no plugin. See https://sofa-framework.github.io/doc/getting-started/build/linux/
- **Tracy:** a compiled version of the tracy-cvsexporter and tracy-capture. Make sure they are the same version of the one used by SOFA and directly accessible (add their directory to your path). If the one from SOFA changes, it might be good to dump the version in the patches (see branch-dependency/git-patches) to be able to still build and test old releases.
- **ccache:** By default ccache is used, it is recommended to have it installed
- **Python3:** Version 3.12 + PyGithub
- **inxi:** to dump hardware info


#### How to
The statistics are run through the `main.sh` script :

*brief:* This script is used to launch the full pipeline of performance testing for one specific commit or branch.
It is parametrized by three files :
- perf.scenes : List of  "${scene name} ${starting time step to record} ${nax time step} ${number of scene launch}
- default.timers : timers to be used for statistics for scenes that uses a DefaultAnimationLoop. It allows to redefine the timer name using the syntax TimeNameInStats=TimerNameInSOFA. You can also use simple addition and subtraction of timer names on the right-hand side (e.g : "CollisionDetection=CollisionEndEvent-CollisionBeginEvent" or "ProjectAndMechaMap=ProjectAndPropagateDx+ProjectAndPropagateXAndV"). Subtraction uses timestamp and addition time spawn. This has been added to be able to have a unified notation between those timers an the ones from FreeMotionAnimaitonLoop scenes
- freemotion.timers : Same than the last one but for scenes with FreeMotionAnimationLoop

*inputs:*
- workdir     (required): directory used to store all working files. Where folders build, sofa, and output will be created.
- sofa-branch (required): branch to test
- commit-hash (optional): specific commit to test, if none is given, the tip of the branch will be tested.

*env:*
- RO_GITHUB_TOKEN: a read only github token

*outputs:*
- log files in the folder $WORK_DIR/logs
- computed statistic : in a file named after the commit hash with the commit date and time (or the release version if only a branch is given and its name follows the release naming convention vXX.XX). e.g. sha_yyyy-mm-dd_hh-mm-ss.csv. The statistics are formated in a matrix which lines are the scenes names defined in perf.scenes and column are the results of the cartesian product between the timer names present in the files `default.timers` and `freemotion.timers` and all the type of statistics defined in generate_statistics/methods.py:computeSingleData.
- hardware info : hardware information of the computer who generated the results. Same naming convention except that no date or time is added.

Note that the statistic file and hard info file are copied in the repository in folder old_results to be ready to commit them

### Dashboard
If you just want to display the archived results you can only launch the dashboard script in `dashboard/dashboard.py`.
There are two ways of launching it :
1. Using directly python3 to run the script. This will result in a dashoboard being accessible on 127.0.0.1:8050
2. Using docker compose. You'll have two solution, either using the pre generated image by ging in the folder `dashboard/docker/` and running `docker compose up redis` or by building it yourself buy running `docker compose build && docker compose up local`

#### Dependencies
Dependencies depends on how you run it:
1. If runing through python3, you'll need to install all the dependencies in the file `dashboard/docker/requirements.txt` by calling `python3 -m pip install -r requirements.txt`, you can skip `gunicorn`.
2. If runing through docker, you'll need docker desktop and docker compose. See https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository

For both:
*env:*
- RO_GITHUB_TOKEN: a read only github token
