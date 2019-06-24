import math
from unittest.mock import patch

import pytest

from dogkop.dogkop import *


def test_operator_managed_tags():
    namespace = 'namespace'
    name = 'name'
    uid = 'uid'
    tags = operator_managed_tags(namespace=namespace, name=name, uid=uid)

    assert f'{KUBE_RESOURCE_UID_TAG}:{uid}' in tags
    assert f'{KUBE_NAMESPACE_TAG}:{namespace}' in tags
    assert f'{KUBE_RESOURCE_NAME_TAG}:{name}' in tags
    assert len(tags) == 3


@pytest.mark.parametrize('max_delay', [1, 60, 300, 600, 3600])
def test_jittered_backoff_delay_max_delay(max_delay):
    with patch('dogkop.dogkop.random.randint') as randint_mock:
        retry = math.ceil(math.log(max_delay, 2))
        jittered_backoff_delay(retry, max_delay)

        assert randint_mock.call_args[0][0] == 0
        assert randint_mock.call_args[0][1] == max_delay


@pytest.mark.parametrize('tags,query_result,expected', [
    ([], {'monitors': [{'id': 12345}]}, 12345),
    (['foo'], {'monitors': [{'id': 123}]}, 123),
    (['foo', 'bar'], {'monitors': []}, None),
])
def test_query_monitor_by_tags(tags, query_result, expected):
    with patch('dogkop.dogkop.api') as api_mock:
        api_mock.Monitor.search.return_value = query_result
        result = query_monitor_by_tags(tags)

        assert api_mock.Monitor.search.call_count == 1
        assert 'query' in api_mock.Monitor.search.call_args[1]
        query = api_mock.Monitor.search.call_args[1]['query']
        for tag in tags:
            assert f'tag:{tag}' in query
        assert result == expected


def test_query_monitor_by_tags_error():
    with pytest.raises(HandlerRetryError), patch('dogkop.dogkop.api') as api_mock:
        api_mock.Monitor.search.return_value = {'errors': ['error']}
        query_monitor_by_tags([])
