# DataDog Operator

Manage [DataDog](https://www.datadoghq.com/) Monitor resources from within Kubernetes.

To be able to make the most of Kubernetes, you need a set of cohesive APIs to extend in order to
service and manage your applications. dogkop brings the management of DataDog Monitor resources
into Kubernetes. Deploying Monitoring resources is no longer an afterthought as they can be
defined using the same templates that define the your application.

These CRDs, coupled with DataDog's Kubernetes node agent and prometheus autodiscovery, provide
seamless management of both application and infrastructure metrics for your services.

**Disclaimer:** The code is littered with TODOs and should be considered for demonstration purposes
only.

Built using the [Kubernetes Operator Pythonic Framework](https://github.com/zalando-incubator/kopf)

## Introduction

Provisioning the same Monitor that DataDog's [Create a monitor](https://docs.datadoghq.com/api/?lang=python#create-a-monitor)
API docs describe using a Kubernetes custom resource.

```yaml
apiVersion: datadog.mzizzi/v1
kind: Monitor
metadata:
  name: my-monitor
spec:
  type: metric alert
  query: avg(last_5m):sum:system.net.bytes_rcvd{host:host0} > 100
  name: Bytes received on host0
  message: We may need to add web hosts if this is consistently high.
  tags:
    - foo:bar
  options:
    notify_no_data: True,
    no_data_timeframe: 20
```

## Running the Operator

You'll need DataDog creds. You can get them [here](https://www.datadoghq.com/free-datadog-trial/).
You can skip setting up an agent for now. (Even though the signup process makes it seem required.)
These to run dogkop in dev mode:

```bash
oc apply -f manifests/monitor-crd.yml
export DATADOG_API_KEY=$myDatadogApiKey
export DATADOG_APP_KEY=$myDatadogAppKey
python3.7 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
kopf run datadog_operator.py
```

See [manifests](manifests/) for information for installing the Operator as a
Kubernetes deployment.

## Tutorial

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
dog monitor show_
all --monitor_tags=kube_resource_id:62ad94bf-8fbf-11e9-a09c-5254007ee77c
```

## Testing

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
python -m pytest tests
```