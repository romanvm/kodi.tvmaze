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

"""
Fakes for Kodi Python API built on top of Kodistubs

Kodistubs functions are no-ops, so the parts of the API that the addon depends on
are replaced with fakes that keep state and record calls. The fakes subclass
the stubs, so method signatures and ``hasattr`` feature checks match the real Kodi API.

:func:`install` must be called before any addon module is imported.
"""

import functools
import importlib
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple
from xml.etree import ElementTree as Etree

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = REPO_ROOT / 'metadata.tvmaze'

PLUGIN_URL = 'plugin://metadata.tvmaze/'
HANDLE = 1

KODI_BUILD_VERSIONS = {
    21: '21.2 (21.2.0) Git:20250101-nogitfound',
    22: '22.0-ALPHA1 (21.90.700) Git:20250601-nogitfound',
}

_info_labels: Dict[str, str] = {'System.BuildVersion': KODI_BUILD_VERSIONS[21]}
_special_paths: Dict[str, str] = {}


def _parse_addon_info() -> Dict[str, str]:
    root = Etree.parse(str(ADDON_DIR / 'addon.xml')).getroot()
    addon_id = root.attrib['id']
    return {
        'id': addon_id,
        'name': root.attrib['name'],
        'version': root.attrib['version'],
        'author': root.attrib['provider-name'],
        'path': str(ADDON_DIR),
        'profile': f'special://profile/addon_data/{addon_id}/',
    }


def _parse_default_settings() -> Dict[str, Any]:
    root = Etree.parse(str(ADDON_DIR / 'resources' / 'settings.xml')).getroot()
    settings = {}
    for setting in root.iter('setting'):
        default = setting.findtext('default') or ''
        setting_type = setting.attrib['type']
        if setting_type == 'integer':
            value = int(default or 0)
        elif setting_type == 'boolean':
            value = default == 'true'
        else:
            value = default
        settings[setting.attrib['id']] = value
    return settings


ADDON_INFO = _parse_addon_info()
DEFAULT_SETTINGS = _parse_default_settings()


class InfoTagCall(NamedTuple):
    method: str
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]


def _make_recorder(method_name: str, method: Callable) -> Callable:
    @functools.wraps(method)
    def recorder(self, *args, **kwargs):
        # Calling the stub method validates arguments against the real API signature
        result = method(self, *args, **kwargs)
        self.calls.append(InfoTagCall(method_name, args, kwargs))
        return result

    recorder.is_recorder = True
    return recorder


def _record_setters(cls):
    """Class decorator that records calls to all set*/add* methods"""
    for name in dir(cls):
        if name.startswith(('set', 'add')):
            method = getattr(cls, name)
            if callable(method) and not getattr(method, 'is_recorder', False):
                setattr(cls, name, _make_recorder(name, method))
    return cls


@_record_setters
class RecordingInfoTag(xbmc.InfoTagVideo):
    """InfoTagVideo (Kodi 21 API) that records calls to its setters"""

    def __init__(self, offscreen: bool = False) -> None:
        super().__init__(offscreen)
        self.calls: List[InfoTagCall] = []

    def get_calls(self, method: str) -> List[InfoTagCall]:
        return [call for call in self.calls if call.method == method]

    def get_args(self, method: str) -> Tuple[Any, ...]:
        """Get positional args of a method that must have been called exactly once"""
        calls = self.get_calls(method)
        assert len(calls) == 1, f'{method} was called {len(calls)} times, expected once'
        return calls[0].args

    def get_value(self, method: str) -> Any:
        """Get the first positional arg of a method that must have been called exactly once"""
        return self.get_args(method)[0]

    def was_called(self, method: str) -> bool:
        return bool(self.get_calls(method))


@_record_setters
class RecordingInfoTag22(RecordingInfoTag):
    """
    InfoTagVideo with Kodi 22 API additions

    Kodistubs for Kodi 22 are not compatible with Python 3.8,
    so the methods that are used by the addon are added by hand.
    """

    def setOriginalLanguage(self, language: str) -> bool:
        return True

    def addSeason(self, number: int, name: str = '', plot: str = '') -> None:
        pass

    def setAvailableFanart(self, images: List[Dict[str, str]]) -> None:
        pass


class FakeActor(xbmc.Actor):
    """Actor that keeps its properties"""

    def __init__(self, name: str = '', role: str = '', order: int = -1, thumbnail: str = ''):
        super().__init__(name, role, order, thumbnail)
        self._name = name
        self._role = role
        self._order = order
        self._thumbnail = thumbnail

    def getName(self) -> str:
        return self._name

    def getRole(self) -> str:
        return self._role

    def getOrder(self) -> int:
        return self._order

    def getThumbnail(self) -> str:
        return self._thumbnail

    def __repr__(self) -> str:
        return (
            f'FakeActor(name={self._name!r}, role={self._role!r}, '
            f'order={self._order!r}, thumbnail={self._thumbnail!r})'
        )


class FakeListItem(xbmcgui.ListItem):
    """ListItem that keeps its label and a single InfoTagVideo instance"""

    info_tag_class = RecordingInfoTag

    def __init__(
        self, label: str = '', label2: str = '', path: str = '', offscreen: bool = False
    ) -> None:
        super().__init__(label, label2, path, offscreen)
        self.label = label
        self.offscreen = offscreen
        self.info_tag = self.info_tag_class(offscreen)
        self.available_fanart: Optional[List[Dict[str, str]]] = None

    def getLabel(self) -> str:
        return self.label

    def getVideoInfoTag(self) -> RecordingInfoTag:
        return self.info_tag

    def setAvailableFanart(self, images: List[Dict[str, str]]) -> None:
        super().setAvailableFanart(images)
        self.available_fanart = images


class FakeWindow(xbmcgui.Window):
    """Window with properties that are shared between instances with the same ID"""

    properties: Dict[int, Dict[str, str]] = defaultdict(dict)

    def __init__(self, existingWindowId: int = -1) -> None:
        super().__init__(existingWindowId)
        self._window_id = existingWindowId

    def setProperty(self, key: str, value: str) -> None:
        # Kodi window property keys are case-insensitive
        self.properties[self._window_id][key.lower()] = value

    def getProperty(self, key: str) -> str:
        return self.properties[self._window_id].get(key.lower(), '')

    def clearProperty(self, key: str) -> None:
        self.properties[self._window_id].pop(key.lower(), None)


class FakeAddon(xbmcaddon.Addon):
    """Addon with info from addon.xml and in-memory settings"""

    settings: Dict[str, Any] = dict(DEFAULT_SETTINGS)

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id)

    def getAddonInfo(self, id: str) -> str:
        return ADDON_INFO.get(id, '')

    def getSettingBool(self, id: str) -> bool:
        return bool(self.settings[id])

    def getSettingInt(self, id: str) -> int:
        return int(self.settings[id])

    def getSettingString(self, id: str) -> str:
        return str(self.settings[id])

    def getSetting(self, id: str) -> str:
        value = self.settings[id]
        if isinstance(value, bool):
            return 'true' if value else 'false'
        return str(value)


class DirectoryItem(NamedTuple):
    url: str
    list_item: FakeListItem
    is_folder: bool


class ResolvedUrl(NamedTuple):
    succeeded: bool
    list_item: FakeListItem


class PluginRecorder:
    """Records results that the addon passes to Kodi via xbmcplugin functions"""

    def __init__(self) -> None:
        self.directory_items: List[DirectoryItem] = []
        self.resolved_urls: List[ResolvedUrl] = []
        self.end_of_directory_calls = 0

    @property
    def resolved(self) -> Optional[ResolvedUrl]:
        """The only setResolvedUrl result or None"""
        assert len(self.resolved_urls) <= 1, 'setResolvedUrl was called more than once'
        return self.resolved_urls[0] if self.resolved_urls else None

    def addDirectoryItem(
        self,
        handle: int,
        url: str,
        listitem: xbmcgui.ListItem,
        isFolder: bool = False,
        totalItems: int = 0,
    ) -> bool:
        assert handle == HANDLE, f'Invalid handle: {handle}'
        assert isinstance(listitem, FakeListItem)
        assert isinstance(url, str), f'Invalid url: {url!r}'
        self.directory_items.append(DirectoryItem(url, listitem, isFolder))
        return True

    def setResolvedUrl(self, handle: int, succeeded: bool, listitem: xbmcgui.ListItem) -> None:
        assert handle == HANDLE, f'Invalid handle: {handle}'
        assert isinstance(listitem, FakeListItem)
        self.resolved_urls.append(ResolvedUrl(succeeded, listitem))

    def endOfDirectory(
        self,
        handle: int,
        succeeded: bool = True,
        updateListing: bool = False,
        cacheToDisc: bool = True,
    ) -> None:
        assert handle == HANDLE, f'Invalid handle: {handle}'
        self.end_of_directory_calls += 1

    def install(self, monkeypatch) -> None:
        for name in ('addDirectoryItem', 'setResolvedUrl', 'endOfDirectory'):
            monkeypatch.setattr(xbmcplugin, name, getattr(self, name))


def _get_info_label(cLine: str) -> str:
    return _info_labels.get(cLine, '')


def _translate_path(path: str) -> str:
    for special_path, real_path in _special_paths.items():
        if path.startswith(special_path):
            return real_path + path[len(special_path) :]
    return path


def _mkdir(path: str) -> bool:
    os.makedirs(path, exist_ok=True)
    return True


def set_special_path(special_path: str, real_path: str) -> None:
    _special_paths[special_path.rstrip('/')] = real_path.rstrip('/')


def reset() -> None:
    """Reset the state of Kodi fakes"""
    FakeAddon.settings = dict(DEFAULT_SETTINGS)
    FakeWindow.properties.clear()
    _special_paths.clear()


def install() -> None:
    """
    Replace Kodistubs functions and classes with fakes and import the addon

    Some addon modules read Kodi state at import time
    (e.g. ``KODI_VERSION`` and ``HANDLE``), so this must be called before
    importing anything from ``libs``.
    """
    xbmc.getInfoLabel = _get_info_label
    xbmc.Actor = FakeActor
    xbmcaddon.Addon = FakeAddon
    xbmcgui.ListItem = FakeListItem
    xbmcgui.Window = FakeWindow
    xbmcvfs.translatePath = _translate_path
    xbmcvfs.exists = os.path.exists
    xbmcvfs.mkdir = _mkdir
    xbmcvfs.mkdirs = _mkdir
    if str(ADDON_DIR) not in sys.path:
        sys.path.insert(0, str(ADDON_DIR))
    original_argv = sys.argv
    sys.argv = [PLUGIN_URL, str(HANDLE), '']
    try:
        importlib.import_module('libs.actions')
    finally:
        sys.argv = original_argv
