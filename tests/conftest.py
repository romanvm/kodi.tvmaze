# Copyright (C) 2026, Roman Miroshnychenko aka Roman V.M.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import logging
import sys
from decimal import Decimal
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlencode

import pytest

from fakes import kodi

# Must be called before any addon module is imported
kodi.install()

import simple_requests  # noqa: E402

from fakes.tvmaze import FakeTVmazeApi  # noqa: E402
from libs import actions, cache_service, info_tag_property_setters, kodi_utils  # noqa: E402

CallRouter = Callable[..., None]


@pytest.fixture(autouse=True)
def kodi_env(tmp_path, monkeypatch, caplog):
    """Reset Kodi state between tests"""
    kodi.reset()
    temp_dir = tmp_path / 'kodi_temp'
    temp_dir.mkdir()
    kodi.set_special_path('special://temp', str(temp_dir))
    monkeypatch.setattr(kodi_utils.Settings, '_instance', None)
    monkeypatch.setattr(cache_service.MemoryCache, '_instance', None)
    monkeypatch.setattr(sys, 'argv', [kodi.PLUGIN_URL, str(kodi.HANDLE), ''])
    caplog.set_level(logging.DEBUG)
    yield
    kodi.reset()


@pytest.fixture(autouse=True)
def tvmaze(monkeypatch) -> FakeTVmazeApi:
    """Fake TVmaze API that serves responses from fixture files"""
    api = FakeTVmazeApi()
    monkeypatch.setattr(simple_requests, 'get', api.get)
    return api


@pytest.fixture(autouse=True)
def plugin(monkeypatch) -> kodi.PluginRecorder:
    """Results returned by the addon to Kodi via xbmcplugin functions"""
    recorder = kodi.PluginRecorder()
    recorder.install(monkeypatch)
    return recorder


@pytest.fixture
def addon_settings() -> Dict[str, Any]:
    """Addon settings, initialized with defaults from settings.xml"""
    return kodi.FakeAddon.settings


@pytest.fixture
def kodi_version(request, monkeypatch) -> int:
    """
    Emulate a Kodi version (21 by default)

    Use with indirect parametrization:
    ``@pytest.mark.parametrize('kodi_version', [21, 22], indirect=True)``
    """
    version = getattr(request, 'param', 21)
    decimal_version = Decimal(kodi.KODI_BUILD_VERSIONS[version][:4])
    monkeypatch.setattr(kodi_utils, 'KODI_VERSION', decimal_version)
    monkeypatch.setattr(info_tag_property_setters, 'KODI_VERSION', decimal_version)
    info_tag_class = kodi.RecordingInfoTag22 if version >= 22 else kodi.RecordingInfoTag
    monkeypatch.setattr(kodi.FakeListItem, 'info_tag_class', info_tag_class)
    return version


@pytest.fixture
def call_router(monkeypatch) -> CallRouter:
    """
    Call the addon the same way as Kodi does

    Keyword arguments are URL-encoded into a paramstring.
    ``path_settings`` dict is passed as JSON ``pathSettings`` parameter
    (Kodi always passes it).
    """

    def _call_router(path_settings: Optional[Dict[str, Any]] = None, **params: str) -> None:
        params['pathSettings'] = json.dumps(path_settings or {})
        paramstring = urlencode(params)
        monkeypatch.setattr(sys, 'argv', [kodi.PLUGIN_URL, str(kodi.HANDLE), f'?{paramstring}'])
        actions.router(paramstring)

    return _call_router
