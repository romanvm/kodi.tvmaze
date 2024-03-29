# Copyright (C) 2019, Roman Miroshnychenko aka Roman V.M. <roman1972@gmail.com>
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

"""Misc utils"""
import logging
from typing import Text, Any, Dict

import xbmc
from xbmcaddon import Addon

ADDON = Addon()
ADDON_ID = ADDON.getAddonInfo('id')
VERSION = ADDON.getAddonInfo('version')

LOG_FORMAT = '[{addon_id} v.{addon_version}] {filename}:{lineno} - {message}'

EPISODE_ORDER_MAP = {
    0: 'default',
    1: 'dvd_release',
    2: 'verbatim_order',
    3: 'country_premiere',
    4: 'streaming_premiere',
    5: 'broadcast_premiere',
    6: 'language_premiere',
}


class KodiLogHandler(logging.Handler):
    """
    Logging handler that writes to the Kodi log with correct levels

    It also adds {addon_id} and {addon_version} variables available to log format.
    """
    LEVEL_MAP = {
        logging.NOTSET: xbmc.LOGNONE,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.INFO: xbmc.LOGINFO,
        logging.WARN: xbmc.LOGWARNING,
        logging.WARNING: xbmc.LOGWARNING,
        logging.ERROR: xbmc.LOGERROR,
        logging.CRITICAL: xbmc.LOGFATAL,
    }

    def emit(self, record):
        record.addon_id = ADDON_ID
        record.addon_version = VERSION
        message = self.format(record)
        kodi_log_level = self.LEVEL_MAP.get(record.levelno, xbmc.LOGDEBUG)
        xbmc.log(message, level=kodi_log_level)


def initialize_logging():
    """
    Initialize the root logger that writes to the Kodi log

    After initialization, you can use Python logging facilities as usual.
    """
    logging.basicConfig(
        format=LOG_FORMAT,
        style='{',
        level=logging.DEBUG,
        handlers=[KodiLogHandler()],
        force=True
    )


def get_episode_order(path_settings: Dict[Text, Any]) -> str:
    episode_order_enum = path_settings.get('episode_order')
    if episode_order_enum is None:
        episode_order_enum = ADDON.getSettingInt('episode_order')
    episode_order = EPISODE_ORDER_MAP.get(episode_order_enum, 'default')
    return episode_order
