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
from .utils import get_requests_session

__all__ = ['search_show']

SEARCH = 'http://api.tvmaze.com/search/shows'
SHOW_INFO = 'http://api.tvmaze.com/shows/{}'
SESSION = get_requests_session()


def _load_info(url, params=None):
    # type: (str, dict) -> dict
    """
    Load info from TV Maze

    :param url: API endpoint URL
    :param params: URL query params
    :return: API response
    :raises requests.exceptions.HTTPError: if any error happens
    """
    response = SESSION.get(url, params=params)
    if not response.ok:
        response.raise_for_status()
    return response.json()


def search_show(title):
    # type: (str) -> dict
    """
    Search a single TV show

    :param title: TV show title to search
    :return: a dict with show data
    :raises requests.exceptions.HTTPError:
    """
    return _load_info(SEARCH, {'q': title})


def get_show_info(show_id):
    # type: (int) -> dict
    """
    Get full info for a single show

    :param show_id: TV Maze show ID
    :return: full show info
    :raises requests.exceptions.HTTPError:
    """
    url = SHOW_INFO.format(show_id)
    return _load_info(url, {'embed[]': ['cast', 'seasons', 'episodes']})
