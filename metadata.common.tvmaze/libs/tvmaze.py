# coding: utf-8
#
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

from __future__ import absolute_import
import os
from requests_cache import CachedSession
import xbmc
import xbmcvfs

cache_dir = os.path.join(xbmc.translatePath('special://temp'), 'tvmaze')
if not xbmcvfs.exists(cache_dir):
    xbmcvfs.mkdir(cache_dir)
cache_db = os.path.join(cache_dir, 'tvmaze')

HEADERS = {
    'User-Agent': 'Kodi scraper for tvmaze.com by Roman V.M.; roman1972@gmail.com',
    'Accept': 'application/json',
}

SINGLE_SEARCH = 'http://api.tvmaze.com/singlesearch/shows'


class NotFoundError(Exception):
    pass


def load_info(url, params=None):
    session = CachedSession(cache_db)
    session.headers.update(HEADERS)
    resp = session.get(url, params=params)
    if resp.status_code == 404:
        raise NotFoundError
    return resp.json()


def search_show(title, year=None):
    """
    Search a single TV show

    :param title:
    :type title: str
    :param year:
    :type year: str
    :return: a dict with show data
    :rtype: dict
    :raises NotFoundError:
    """
    if year is not None:
        title += ' ' + year
    return load_info(SINGLE_SEARCH, {'q': title})


def get_show_details(url):
    """

    :param url:
    :return:
    """
    return load_info(url, {'embed': 'cast'})


def get_eposode_list(url):
    """

    :param url:
    :return:
    """
    return load_info(url)
