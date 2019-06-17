import copy
from functools import wraps

import kopf
from datadog import initialize, api as datadog_api
from kopf import HandlerRetryError
from kopf.structs.status import get_retry_count

initialize()
# datadog_api._mute = False

MONITOR_ID_KEY = 'datadog_monitor_id'
KUBE_RESOURCE_ID_KEY = 'kube_resource_id'

MONITOR_NOT_FOUND = 'Monitor not found'


def exponential_backoff(delay=2, backoff=2, max_delay=300):
    """
    Customizable exponential backoff strategy.
    :param float delay: Initial (base) delay.
    :param float backoff: base of the exponent to use for exponential backoff.
    :param int max_delay: If provided each delay generated is capped at this amount.
    :return
    """
    def deco(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            try:
                return handler(*args, **kwargs)
            except HandlerRetryError as e:
                # FIXME: `handler`, in this case, is just a callable. It doesn't have all of the
                #  attrs that `get_retry_count` needs.
                sleep = delay * backoff ** get_retry_count(body=kwargs['body'], handler=handler)
                e.delay = sleep if max_delay is None else min(sleep, max_delay)
                raise
        return wrapper
    return deco


@kopf.on.create('datadog.mzizzi', 'v1', 'monitors')
def on_create(spec, patch, uid, **kwargs):
    # TODO: should we further validate spec or let datadog kick back an error if things are off?

    # Track the kubernetes resource id of this object as a tag on the monitor in datadog. Attempt
    # to do this politely by making a copy of the dict.
    request_body = copy.deepcopy(spec)
    request_body.setdefault('tags', []).append(f'{KUBE_RESOURCE_ID_KEY}:{uid}')

    response = datadog_api.Monitor.create(**request_body)

    # store the id of the datadog monitor in the kube resource's status field
    patch.setdefault('status', {})[MONITOR_ID_KEY] = response['id']


@kopf.on.update('datadog.mzizzi', 'v1', 'monitors')
def on_update(status, spec, uid, **kwargs):
    # TODO: handle case where monitor doesn't exist. Either because status[MONITOR_ID_KEY] is
    #  missing or the monitor itself is missing on the DataDog side.

    # Track the kubernetes resource id of this object as a tag on the monitor in datadog. Attempt
    # to do this politely by making a copy of the dict.
    request_body = copy.deepcopy(spec)
    request_body.setdefault('tags', []).append(f'{KUBE_RESOURCE_ID_KEY}:{uid}')

    monitor_id = status.get(MONITOR_ID_KEY, None)

    if not monitor_id:
        # TODO: status field missing. Someone(thing?) modified the resource such that we can no
        #  longer determine what monitor to update.
        #    * complain via somehow via kube events / status?
        #    * create a new monitor?
        #    * search datadog for an alarm with a matching uid?
        pass

    # update using the monitor id that's cached in this resource's status field
    response = datadog_api.Monitor.update(status[MONITOR_ID_KEY], **request_body)

    if 'errors' in response and response['errors']:
        # TODO: fix the datadog SDK such that we know what type of error occurred. As of now we
        #  don't know if the failure is "retryable" or if it's pointless to keep trying. The datadog
        #  SDK only returns an error object. http status code would be more helpful in determining
        #  how to proceed.
        pass

    return


@kopf.on.delete('datadog.mzizzi', 'v1', 'monitors')
def on_delete(status, patch, logger, **kwargs):
    monitor_id = status.get(MONITOR_ID_KEY, None)

    if not monitor_id:
        # TODO: status field missing. Someone(thing?) modified the resource such that we can no
        #  longer determine what monitor to update.
        #    * complain via somehow via kube events / status?
        #    * create a new monitor?
        #    * search datadog for an alarm with a matching uid?
        logger.debug(
            f'Monitor resource missing "{MONITOR_ID_KEY}" key. Monitor may be orphaned '
            'in DataDog.')
        return

    response = datadog_api.Monitor.delete(monitor_id)

    if 'errors' in response and response['errors']:
        # TODO: fix the datadog SDK such that we know what type of error occurred. As of now we
        #  don't know if the failure is "retryable" or if it's pointless to keep trying. The
        #  datadog SDK only returns an error object. http status code would be more helpful in
        #  determining how to proceed. The best we cane do for now is to string compare bits and
        #  pieces of the response until we can get hands on the underlying status code.
        #  GitHub issue: https://github.com/DataDog/datadogpy/issues/408
        if MONITOR_NOT_FOUND in response['errors']:
            logger.debug(f'datadog monitor {monitor_id} already deleted')
            return

        # TODO: exponential backoff

        # FIXME: This will flood events if backoff isn't aggressive:
        #  https://github.com/zalando-incubator/kopf/issues/117
        raise HandlerRetryError(response['errors'])
