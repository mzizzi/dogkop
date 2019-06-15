# DataDog Operator

Manage [DataDog](https://www.datadoghq.com/) resources from within Kubernetes. Currently only
supports DataDog Monitors.

**Warning:** The code is littered with TODOs and should be considered for demonstration purposes
only. There are a lot of edge cases that aren't accounted for that will lead to endless event
processing loops in your cluster and orphaned resources in your DataDog account.

Built using [Kubernetes Operator Pythonic Framework](https://github.com/zalando-incubator/kopf)

## Custom Resource Definitions

To install the CRD:
```bash
oc apply -f monitor-crd.yml
```

To remove the CRD:
```bash
oc delete crd monitors.datadog.mzizzi
oc delete -f monitor-crd.yml
```

## Running the Operator

You'll need DataDog creds. You can get them [here](https://www.datadoghq.com/free-datadog-trial/).
You can skip setting up an agent for now. (Even though the signup process makes it seem required.)

### Locally

```bash
export DATADOG_API_KEY=$myDatadogApiKey
export DATADOG_APP_KEY=$myDatadogAppKey
python3.7 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
kopf run datadog_operator.py
```

## Proof of Concept

Assumes you're running minishift, the CRD is installed, and the operator is running.

Create a DataDog monitor via a kubernetes custom resource.
```bash
oc apply -f examples/monitor.yml
```

Take a look at the resource in kubernetes. Note the ID of the DataDog monitor is stored in the
status field.
```bash
oc get mon my-monitor -o yaml

# explicitly fetching the monitor id
oc get mon my-monitor -o json | jq .status.datadog_monitor_id
```

Check the [DataDog Manage Monitors UI](https://app.datadoghq.com/monitors/manage) and find your
newly created monitor. Alternatively use the DataDog CLI to ensure that the monitor was really
created over at DataDog. If you've already walked through installing everything in
`requirements.txt` then the `dog` CLI porgram should already be available. More on configuring
the CLI [here](https://docs.datadoghq.com/developers/guide/dogshell-asdf-use-datadog-s-api-from-terminal-shell/).
```bash
dog monitor show $(oc get mon my-monitor -o json | jq .status.datadog_monitor_id)
```

Let's make sure tags we set in `examples/monitor.yml` made into DataDog. Note that
`kube_resource_id` captures the ID of the corresponding kube resource. Potentially helpful for
identifying orphans down the road?
```bash
dog monitor show $(oc get mon my-monitor -o json | jq .status.datadog_monitor_id) | jq .tags
[
  "foo:bar",
  "kube_resource_id:62ad94bf-8fbf-11e9-a09c-5254007ee77c"
]
```

Replace tag `foo:bar` with `fizz:buzz`:
```bash
oc apply -f examples/monitor-update.yml
dog monitor show $(oc get mon my-monitor -o json | jq .status.datadog_monitor_id) | jq .tags
[
  "fizz:buzz",
  "kube_resource_id:62ad94bf-8fbf-11e9-a09c-5254007ee77c"
]
```

Delete the monitor from kubernetes and ensure that it's deleted in DataDog:
```bash
oc delete mon my-monitor
dog monitor show_all --monitor_tags=kube_resource_id:62ad94bf-8fbf-11e9-a09c-5254007ee77c
```