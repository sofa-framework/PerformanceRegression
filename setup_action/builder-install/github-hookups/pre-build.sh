#!/bin/bash

BRANCH_OR_PR_NUMBER=$(echo $GITHUB_REF | awk -F '/' '{print $3}')
REF_TYPE=$(echo $GITHUB_REF | awk -F '/' '{print $2}')

echo "Repository owner : $GITHUB_REPOSITORY_OWNER"
echo "Ref type : $REF_TYPE"

if [ "$GITHUB_REPOSITORY_OWNER" != "sofa-framework" ] || [ "$REF_TYPE" == "pull" ]; then
echo "This commit doesn't belong to the sofa-framework repository, exiting the job"
exit 1
fi

rm -rf $RUNNER_ACTIONS_RUNNER_DIRECTORY/_work/PerformanceRegression/PerformanceRegression/*

