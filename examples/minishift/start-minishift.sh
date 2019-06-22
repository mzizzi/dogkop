#!/bin/bash
MINISHIFT_GITHUB_API_TOKEN=$(cat ~/.git_token) minishift start
eval $(minishift oc-env)
oc login -u system:admin