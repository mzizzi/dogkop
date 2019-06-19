import copy
import random
from functools import wraps

import kopf
from datadog import initialize, api as datadog_api
from kopf import HandlerRetryError, HandlerFatalError

initialize()
# datadog_api._mute = False

MONITOR_ID_KEY = 'datadog_monitor_id'
KUBE_RESOURCE_UID_TAG = 'kubernetes.resource.uid'
KUBE_RESOURCE_NAME_TAG = 'kubernetes.resource.name'
KUBE_NAMESPACE_TAG = 'kubernetes.namespace'


def handler_wrapper(max_backoff_delay=600):
    """
    Handles exponential backoff for all Handlers if/when they throw `HandlerRetryErrors`.
    Also adds `monitor_id` and `extra_tags` the wrapped handler.
    :param int max_backoff_delay: If provided each delay generated is capped at this amount.
    :return
    """
    def deco(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            try:
                tags = operator_managed_tags(kwargs['namespace'], kwargs['name'], kwargs['uid'])
                monitor_id = kwargs['status'].get(MONITOR_ID_KEY, None) or query_monitor_id(tags)
                return handler(*args, monitor_id=monitor_id, extra_tags=tags, **kwargs)
            except HandlerRetryError as e:
                e.delay = jittered_backoff(kwargs.get('retry', 0), max_backoff_delay)
                raise
        return wrapper
    return deco


def jittered_backoff(retry, max_delay, _random=random):
    return _random.randint(0, min(max_delay, 2 ** retry))


def operator_managed_tags(namespace, name, uid):
    """
    List of tags used to query (potentially orphaned?) Monitors from DataDog.
    :param namespace:
    :param name:
    :param uid:
    :return:
    """
    return [
        f'{KUBE_RESOURCE_UID_TAG}:{uid}',
        f'{KUBE_NAMESPACE_TAG}:{namespace}',
        f'{KUBE_RESOURCE_NAME_TAG}:{name}']


def query_monitor_id(tags):
    """
    Query DataDog to see if a monitor exists with the provided tags.
    :param tags:
    :return:
    """
    response = datadog_api.Monitor.search(query=' '.join(['tag:' + tag for tag in tags]))

    if 'errors' in response and response['errors']:
        raise HandlerRetryError(response['errors'])

    monitors = response.get('monitors', [])
    if monitors and len(monitors) > 0:
        return monitors[0].get('id')


def configure_monitor(spec, monitor_id, extra_tags):
    """
    Idempotent method for Configure
    :param spec:
    :param patch:
    :param monitor_id:
    :param extra_tags:
    :return:
    """
    request_body = copy.deepcopy(spec)
    request_body.setdefault('tags', []).extend(extra_tags)

    if monitor_id:
        response = datadog_api.Monitor.update(monitor_id, **request_body)
    else:
        response = datadog_api.Monitor.create(**request_body)

    if 'errors' in response and response['errors']:
        raise HandlerRetryError(response['errors'])

    return response


@kopf.on.create('datadog.mzizzi', 'v1', 'monitors')
@handler_wrapper()
def on_create(spec, patch, monitor_id, extra_tags, **kwargs):
    patch.setdefault('status', {})[MONITOR_ID_KEY] = \
        configure_monitor(spec, monitor_id, extra_tags).get('id')


@kopf.on.update('datadog.mzizzi', 'v1', 'monitors')
@handler_wrapper()
def on_update(spec, patch, monitor_id, extra_tags, **kwargs):
    patch.setdefault('status', {})[MONITOR_ID_KEY] = \
        configure_monitor(spec, monitor_id, extra_tags).get('id')


@kopf.on.delete('datadog.mzizzi', 'v1', 'monitors')
@handler_wrapper()
def on_delete(monitor_id, **kwargs):
    if not monitor_id:
        return

    response = datadog_api.Monitor.delete(monitor_id)

    if 'errors' in response and response['errors']:
        raise HandlerRetryError(response['errors'])
