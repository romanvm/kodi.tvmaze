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

"""Cache-related functionality"""

import os
from six import raise_from
from six.moves import cPickle as pickle
from .utils import get_cache_directory, logger

CACHE_DIR = get_cache_directory()
IMDB_MAP_FILE = os.path.join(CACHE_DIR, 'imdb-map.pickle')


class TvMazeCacheError(Exception):
    pass


def cache_show_info(show_info):
    """
    Save show_info dict to cache
    """
    file_name = str(show_info['id']) + '.pickle'
    with open(os.path.join(CACHE_DIR, file_name), 'wb') as fo:
        pickle.dump(show_info, fo, protocol=2)


def load_show_info_from_cache(show_id):
    """
    Load show info from a local cache

    :param show_id: show ID on TV Maze
    :return: show_info dict
    :raises TvMazeCacheError: if show_info cannot be loaded from cache
    """
    file_name = str(show_id) + '.pickle'
    try:
        with open(os.path.join(CACHE_DIR, file_name), 'rb') as fo:
            return pickle.load(fo)
    except (IOError, pickle.PickleError) as exc:
        logger.debug('Cache error: {} {}'.format(type(exc), exc))
        raise_from(TvMazeCacheError(), exc)


def set_imdb_mapping(imdb_id, tvmaze_id):
    """Save mapping of IMDB ID to TV Maze ID"""
    try:
        with open(IMDB_MAP_FILE, 'rb') as fo:
            imdb_map = pickle.load(fo)
    except (IOError, pickle.PickleError):
        imdb_map = {}
    if imdb_id not in imdb_map:
        imdb_map[imdb_id] = tvmaze_id
        with open(IMDB_MAP_FILE, 'wb') as fo:
            pickle.dump(imdb_map, fo, protocol=2)


def get_imdb_mapping(imdb_id):
    """Get TV Maze show ID by IMDB ID"""
    try:
        with open(IMDB_MAP_FILE, 'rb') as fo:
            imdb_map = pickle.load(fo)
            return imdb_map[imdb_id]
    except (IOError, KeyError, pickle.PickleError):
        return None
