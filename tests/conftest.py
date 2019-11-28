# coding: utf-8
from __future__ import absolute_import

import mock
import pytest


@pytest.fixture
def mock_response():
    patcher = mock.patch('libs.tvmaze.SESSION')
    response = mock.Mock()
    response.ok = True
    session = patcher.start()
    session.get.return_value = response
    yield response
    patcher.stop()
