# coding: utf-8
# pylint: disable=missing-docstring
from __future__ import absolute_import

import json
import os

import mock
import pytest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_url(url, params=None):  # pylint: disable=unused-argument
    response = mock.Mock()
    response.ok = True
    if 'search/shows' in url:
        path = os.path.join(THIS_DIR, 'shows-search.json')
    elif url.endswith('/episodes'):
        path = os.path.join(THIS_DIR, 'episodes.json')
    else:
        path = os.path.join(THIS_DIR, 'show-info.json')
    with open(path, 'rb') as fo:
        info_json = json.load(fo)
    response.json.return_value = info_json
    return response


@pytest.fixture
def mock_response():
    patcher = mock.patch('libs.tvmaze.SESSION')
    session = patcher.start()
    session.get = get_url
    yield
    patcher.stop()
