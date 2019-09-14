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

"""Functions to interact with TV Maze API"""

from __future__ import absolute_import
from pprint import pformat
from requests.exceptions import HTTPError
from . import cache
from .utils import get_requests_session, get_cache_directory, logger
from .data_utils import process_episode_list

SEARCH_URL = 'http://api.tvmaze.com/search/shows'
SEARCH_BU_EXTERNAL_ID_URL = 'http://api.tvmaze.com/lookup/shows'
SHOW_INFO_URL = 'http://api.tvmaze.com/shows/{}'
EPISODE_INFO_URL = 'http://api.tvmaze.com/episodes/{}'

SESSION = get_requests_session()
CACHE_DIR = get_cache_directory()


def _load_info(url, params=None):
    """
    Load info from TV Maze

    :param url: API endpoint URL
    :param params: URL query params
    :return: API response
    :raises requests.exceptions.HTTPError: if any error happens
    """
    logger.debug('Calling URL "{}" with params {}'.format(url, params))
    response = SESSION.get(url, params=params)
    if not response.ok:
        response.raise_for_status()
    json_response = response.json()
    logger.debug('TV Maze response:\n{}'.format(pformat(json_response)))
    return json_response


def search_show(title):
    """
    Search a single TV show

    :param title: TV show title to search
    :return: a dict with show data
    :raises requests.exceptions.HTTPError:
    """
    return _load_info(SEARCH_URL, {'q': title})


def filter_by_year(shows, year):
    """
    Filter a show by year

    :param shows: the list of shows from TV Maze
    :param year: premiere year
    :return: a found show or None
    """
    for show in shows:
        if show['show'].get('premiered', '').startswith(str(year)):
            return show
    return None


def load_show_info(show_id, full_info=True, use_cache=True):
    """
    Get full info for a single show

    :param show_id: TV Maze show ID
    :param full_info: load full info with cast, seasons and episodes
    :param use_cache: try to load cached info
    :return: show info
    :raises requests.exceptions.HTTPError:
    """
    show_info = None
    if use_cache:
        show_info = cache.load_show_info_from_cache(show_id)
    if show_info is None:
        url = SHOW_INFO_URL.format(show_id)
        params = None
        if full_info:
            params = {'embed[]': ['cast', 'seasons', 'episodes', 'crew']}
        show_info = _load_info(url, params)
        if full_info:
            process_episode_list(show_info)
            cache.cache_show_info(show_info)
        if show_info['externals'] is not None:
            if 'imdb' in show_info['externals']:
                cache.set_external_id_mapping(
                    show_info['externals']['imdb'], show_info['id']
                )
            if 'thetvdb' in show_info['externals']:
                cache.set_external_id_mapping(
                    show_info['externals']['thetvdb'], show_info['id']
                )
    return show_info


def load_show_info_by_external_id(provider, show_id):
    """
    Load show info by external ID (TheTVDB or IMDB)

    :param provider: 'imdb' or 'thetvdb'
    :param show_id: show ID in the respective provider
    :return: show info or None
    """
    query = {provider: show_id}
    try:
        return _load_info(SEARCH_BU_EXTERNAL_ID_URL, query)
    except HTTPError:
        return None


def load_episode_info(show_id, episode_id):
    """
    Load episode info

    :param show_id:
    :param episode_id:
    :return: episode info dict
    """
    show_info = load_show_info(show_id, use_cache=True)
    try:
        episode_info = show_info['episodes'][int(episode_id)]
    except KeyError:
        url = EPISODE_INFO_URL.format(episode_id)
        episode_info = _load_info(url)
    return episode_info
