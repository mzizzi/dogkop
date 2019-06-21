#!/bin/bash
oc project myproject
while :; do curl "http://"$(oc -n myproject get route webserver -o json | jq -r .spec.host); done