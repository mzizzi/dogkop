# demo-app

A simple deployment of [prometheus-example-app](https://github.com/brancz/prometheus-example-app/blob/master/main.go).
The application exposes a prometheus metrics endpoint at `/metrics`. The deployment is annotated
with [datadog's kubernetes autodiscovery annotations](https://www.datadoghq.com/blog/monitor-prometheus-metrics/#monitoring-kubernetes-clusters-and-containerized-services)
in order to be automatically have metrics scraped by datadog's [kubernetes node agent](https://docs.datadoghq.com/agent/kubernetes/).

Assumes namespace `myproject` for the demo app.

