# Kubernetes Manifests

Make your own `datadog-secrets.yml`. You can use the `datadog-secrets.yml.example` file as a
starting point.

Deploying the Operator into a cluster:
```bash
oc new-project dogkop
oc apply -f rbac.yml
oc apply -f monitor-crd.yml
oc apply -f datadog-secrets.yaml
oc apply -f deployment.yml
```