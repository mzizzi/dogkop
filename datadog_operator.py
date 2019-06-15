import os

import kopf
from datadog import initialize, api as datadog_api

initialize(
    api_key=os.environ.get('DATADOG_API_KEY'),
    app_key=os.environ.get('DATADOG_APP_KEY'))

MONITOR_ID_KEY = 'datadog_monitor_id'
KUBE_RESOURCE_ID_KEY = 'kube_resource_id'


@kopf.on.create('datadog.mzizzi', 'v1', 'monitors')
def on_create(spec, patch, uid, **kwargs):
    # Track the kubernetes resource id of this object as a tag on the monitor in
    # datadog.

    # TODO: re-enable this once problems described in update are solved.
    # spec.setdefault('tags', []).append(f'{KUBE_RESOURCE_ID_KEY}:{uid}')

    response = datadog_api.Monitor.create(**spec)

    # store the id of the datadog monitor in the kube resource's status field
    patch.setdefault('status', {})[MONITOR_ID_KEY] = response['id']


@kopf.on.update('datadog.mzizzi', 'v1', 'monitors')
def on_update(status, spec, uid, **kwargs):
    # TODO: maintain kubernetes resource id on the monitor as a tag in datadog
    #  This current causes an infinite event loop in kubernetes if uncommented
    # spec.setdefault('tags', []).append(f'{KUBE_RESOURCE_ID_KEY}:{uid}')

    monitor_id = status.get(MONITOR_ID_KEY, None)

    if not monitor_id:
        # TODO: status field missing. Someone(thing?) modified the resource such
        #  that we can no longer determine what monitor to update.
        #   * complain via somehow via kube events / status?
        #   * create a new monitor?
        #   * search datadog for an alarm with a matching uid?
        pass

    # update using the monitor id that's cached in this resource's status
    # field
    response = datadog_api.Monitor.update(status[MONITOR_ID_KEY], **spec)

    if 'errors' in response and response['errors']:
        # TODO: fix the datadog SDK such that we know what type of error
        #  occurred. As of now we don't know if the failure is "retryable" or
        #  if it's pointless to keep trying. The datadog SDK only returns
        #  an error object. http status code would be more helpful in
        #  determining how to proceed.
        pass


@kopf.on.delete('datadog.mzizzi', 'v1', 'monitors')
def on_delete(status, spec, uid, **kwargs):
    # TODO: figure out how kopf interacts with kubernetes finalizers on resource
    # deletion. More info here:
    # https://kubernetes.io/docs/tasks/access-kubernetes-api/custom-resources/custom-resource-definitions/#finalizers

    monitor_id = status.get(MONITOR_ID_KEY, None)

    if not monitor_id:
        # TODO: status field missing. Someone(thing?) modified the resource such
        #  that we can no longer determine what monitor to update.
        #   * complain via somehow via kube events / status?
        #   * create a new monitor?
        #   * search datadog for an alarm with a matching uid?
        pass

    response = datadog_api.Monitor.delete(monitor_id)

    if 'errors' in response and response['errors']:
        # TODO: fix the datadog SDK such that we know what type of error
        #  occurred. As of now we don't know if the failure is "retryable" or
        #  if it's pointless to keep trying. The datadog SDK only returns
        #  an error object. http status code would be more helpful in
        #  determining how to proceed.
        pass
