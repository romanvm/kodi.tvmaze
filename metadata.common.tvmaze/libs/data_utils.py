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

"""Functions to process data"""

import re

TAG_RE = re.compile(r'<[^>]+>')
SUPPORTED_UNIQUE_IDS = {'imdb', 'tvdb', 'tmdb', 'anidb'}


def process_episode_list(show_info):
    """Convert embedded episode list to a dict"""
    episodes = {ep['id']: ep for ep in show_info['_embedded']['episodes']}
    show_info['episodes'] = episodes
    del show_info['_embedded']['episodes']


def _clean_plot(plot):
    """Replace HTML tags with Kodi skin tags"""
    plot = plot.replace('<b>', '[B]').replace('</b>', '[/B]')
    plot = plot.replace('<i>', '[I]').replace('</i>', '[/I]')
    plot = plot.replace('</p><p>', '[CR]')
    plot = TAG_RE.sub('', plot)
    return plot


def _get_cast(show_info):
    """Extract cast from show info dict"""
    cast = []
    for item in show_info['_embedded']['cast']:
        cast.append((item['person']['name'], item['character']['name']))
    return cast


def _get_unique_ids(show_info):
    """Extract unique ID in various online databases"""
    unique_ids = {}
    for key, value in show_info['externals']:
        if key in SUPPORTED_UNIQUE_IDS:
            unique_ids[key] = str(value)
    return unique_ids


def _add_seasons(list_item, show_info):
    for season in show_info['_embedded']['seasons']:
        list_item.addSeason(season['number'], season['name'])
    return list_item


def _add_show_artwork(list_item, show_info):
    artwork = {
        'thumb': show_info['image']['medium'],
        'poster': show_info['image']['original'],
    }
    list_item.setArt(artwork)
    return list_item


def add_main_show_info(list_item, show_info):
    """Add main show info to a list item"""
    video = {
        'genre': show_info['genres'],
        'country': show_info['network']['country'],
        'year': int(show_info['premiered'][:4]),
        'rating': show_info['rating']['average'],
        'plot': _clean_plot(show_info['summary']),
        'castandrole': _get_cast(show_info),
        'duration': show_info['runtime'] * 60,
        'title': show_info['name'],
        'tvshowtitle': show_info['name'],
        'premiered': show_info['premiered'],
        'studio': show_info['network']['name'],
        'status': show_info['status'],
        'mediatype': 'tvshow',
    }
    list_item.setInfo('video', video)
    list_item.setUniqueIDs(_get_unique_ids(show_info))
    list_item = _add_seasons(list_item, show_info)
    list_item = _add_show_artwork(list_item, show_info)
    return list_item
