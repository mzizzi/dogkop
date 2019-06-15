#!/bin/bash
minishift start
eval $(minishift oc-env)
oc login -u system:admin