import copy
import random
from functools import wraps

import kopf
from datadog import initialize, api as datadog_api
from kopf import HandlerRetryError

initialize()

MONITOR_ID_KEY = 'datadog_monitor_id'
KUBE_RESOURCE_UID_TAG = 'kubernetes.resource.uid'
KUBE_RESOURCE_NAME_TAG = 'kubernetes.resource.name'
KUBE_NAMESPACE_TAG = 'kubernetes.namespace'

MONITOR_NOT_FOUND = 'Monitor not found'


def handler_wrapper(max_backoff_delay=600):
    """
    Handles exponential backoff for all Handlers if/when they throw `HandlerRetryErrors`.
    Also adds `monitor_id` and `extra_tags` the wrapped handler.

    Adds `monitor_id` kwarg to each handler. Each of the Handlers in this module share behavior
    in that they must determine whether or not the corresponding datadog monitor already exists
    or not. The cached monitor id stored in `status[MONITOR_ID_KEY]` is the preferred method of
    "rediscovering" the DataDog monitor. Otherwise we attempt to rediscover it with a datadog query
    that searches monitors via tag matching.

    `extra_tags` is a set of operator managed tags that can be used to uniquely identify a Monitor.

    :param int max_backoff_delay: If provided each delay generated is capped at this amount.
    :return:
    """
    def deco(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            try:
                tags = operator_managed_tags(kwargs['namespace'], kwargs['name'], kwargs['uid'])

                monitor_id = kwargs['status'].get(MONITOR_ID_KEY, None)
                if monitor_id:
                    res = datadog_api.Monitor.get(monitor_id)
                    if 'errors' in res and res['errors'] and MONITOR_NOT_FOUND in res['errors']:
                        monitor_id = query_monitor_id(tags)
                        kwargs['patch'].setdefault('status', {})[MONITOR_ID_KEY] = monitor_id
                        if not monitor_id:
                            raise HandlerRetryError(res['errors'])
                    elif 'errors' in res and res['errors']:
                        # Failed to fetch the alarm with an error other than 404
                        HandlerRetryError(res['errors'])

                return handler(*args, monitor_id=monitor_id, extra_tags=tags, **kwargs)
            except HandlerRetryError as e:
                e.delay = jittered_backoff(kwargs.get('retry', 0), max_backoff_delay)
                raise
        return wrapper
    return deco


def jittered_backoff(retry, max_delay, _random=random):
    return _random.randint(0, min(max_delay, 2 ** retry))


def operator_managed_tags(namespace, name, uid):
    """List of tags used to query (potentially orphaned?) Monitors from DataDog."""
    return [
        f'{KUBE_RESOURCE_UID_TAG}:{uid}',
        f'{KUBE_NAMESPACE_TAG}:{namespace}',
        f'{KUBE_RESOURCE_NAME_TAG}:{name}']


def query_monitor_id(tags):
    """
    Query DataDog to see if a monitor exists with the provided tags.
    :param list[str] tags: List of tags used to query DataDog for a monitor.
    :return int: ID of DataDog monitor. None if no Monitor is found.
    """
    response = datadog_api.Monitor.search(query=' '.join(['tag:' + tag for tag in tags]))

    if 'errors' in response and response['errors']:
        raise HandlerRetryError(response['errors'])

    monitors = response.get('monitors', [])
    if monitors and len(monitors) > 0:
        return monitors[0].get('id')


def configure_monitor(monitor_config, monitor_id=None):
    """
    Idempotent method for configuring DataDog monitors.
    :param monitor_config: Ends up being json serialized and passed to DataDog apis for create
     or update.
     https://docs.datadoghq.com/api/?lang=python#create-a-monitor
     https://docs.datadoghq.com/api/?lang=python#edit-a-monitor
    :param monitor_id: Optional id of existing DataDog monitor.
    :return dict: Response from DataDog API.
    """
    if monitor_id:
        response = datadog_api.Monitor.update(monitor_id, **monitor_config)
    else:
        response = datadog_api.Monitor.create(**monitor_config)

    if 'errors' in response and response['errors']:
        raise HandlerRetryError(response['errors'])

    return response


@kopf.on.create('datadog.mzizzi', 'v1', 'monitors')
@handler_wrapper()
def on_create(spec, patch, monitor_id, extra_tags, **kwargs):
    # Changes to `spec` end up being persisted. We're modifying it to be used as a request body so
    # we should work off of a copy.
    monitor_config = copy.deepcopy(spec)
    monitor_config.setdefault('tags', []).extend(extra_tags)

    patch.setdefault('status', {})[MONITOR_ID_KEY] = \
        configure_monitor(monitor_config, monitor_id).get('id')


@kopf.on.update('datadog.mzizzi', 'v1', 'monitors')
@handler_wrapper()
def on_update(spec, patch, monitor_id, extra_tags, **kwargs):
    # Changes to `spec` end up being persisted. We're modifying it to be used as a request body so
    # we should work off of a copy.
    monitor_config = copy.deepcopy(spec)
    monitor_config.setdefault('tags', []).extend(extra_tags)

    patch.setdefault('status', {})[MONITOR_ID_KEY] = \
        configure_monitor(monitor_config, monitor_id).get('id')


@kopf.on.delete('datadog.mzizzi', 'v1', 'monitors')
@handler_wrapper()
def on_delete(monitor_id, **kwargs):
    if not monitor_id:
        return

    response = datadog_api.Monitor.delete(monitor_id)

    if 'errors' in response and response['errors']:
        raise HandlerRetryError(response['errors'])
