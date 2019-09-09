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
import six
from collections import OrderedDict, namedtuple

TAG_RE = re.compile(r'<[^>]+>')
SHOW_ID_REGEXPS = (
    re.compile(r'(tvmaze)\.com/shows/(\d+)/[\w\-]', re.I),
    re.compile(r'(thetvdb)\.com/series/(\d+)', re.I),
    re.compile(r'(thetvdb)\.com[\w=&\?/]+id=(\d+)', re.I),
    re.compile(r'(imdb)\.com/[\w/]+/(tt\d+)', re.I),
)

UrlParseResult = namedtuple('UrlParseResult', ['provider', 'show_id'])
UniqueIds = namedtuple('UniqueIds', ['ids', 'default_id'])

SUPPORTED_UNIQUE_IDS = {'imdb', 'tvdb', 'tmdb', 'anidb'}


def process_episode_list(show_info):
    """Convert embedded episode list to a dict"""
    episodes = OrderedDict()
    for episode in show_info['_embedded']['episodes']:
        episodes[episode['id']] = episode
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
    for index, item in enumerate(show_info['_embedded']['cast'], 1):
        cast.append(
            {
                'name': item['person']['name'],
                'role': item['character']['name'],
                'thumbnail': item['person']['image']['medium'],
                'order': index,
            }
        )
    return cast


def _get_unique_ids(show_info):
    """Extract unique ID in various online databases"""
    unique_ids = {}
    for key, value in six.iteritems(show_info['externals']):
        if key in SUPPORTED_UNIQUE_IDS:
            unique_ids[key] = str(value)
    default_id = ''
    if 'thetvdb' in unique_ids:
        default_id = 'thetvdb'
    elif 'imdb' in unique_ids:
        default_id = 'imdb'
    return UniqueIds(unique_ids, default_id)


def get_show_artwork(show_info):
    # Extract available images for a show
    artwork = {
        'thumb': show_info['image']['medium'],
        'poster': show_info['image']['original'],
    }
    return artwork


def add_main_show_info(list_item, show_info):
    """Add main show info to a list item"""
    plot = _clean_plot(show_info['summary'])
    video = {
        'genre': show_info['genres'],
        'country': show_info['network']['country']['name'],
        'year': int(show_info['premiered'][:4]),
        'rating': show_info['rating']['average'],
        'plot': plot,
        'plotoutline': plot,
        'duration': show_info['runtime'] * 60,
        'title': show_info['name'],
        'tvshowtitle': show_info['name'],
        'premiered': show_info['premiered'],
        'studio': show_info['network']['name'],
        'status': show_info['status'],
        'mediatype': 'tvshow',
        'episodeguide': str(show_info['id'])
    }
    list_item.setInfo('video', video)
    for season in show_info['_embedded']['seasons']:
        list_item.addSeason(season['number'], season['name'])
    unique_ids = _get_unique_ids(show_info)
    list_item.setUniqueIDs(unique_ids.ids, unique_ids.default_id)
    artwork = get_show_artwork(show_info)
    list_item.addAvailableArtwork(artwork['thumb'], 'thumb')
    list_item.addAvailableArtwork(artwork['poster'], 'poster')
    list_item.setCast(_get_cast(show_info))
    return list_item


def add_episode_info(list_item, episode_info, full_info=True):
    """Add episode info to a list item"""
    video = {
        'title': episode_info['name'],
        'season': episode_info['season'],
        'episode': episode_info['number'],
        'aired': episode_info['airdate'],
        'mediatype': 'episode',
    }
    if full_info:
        video['plot'] = video['plotoutline'] = _clean_plot(episode_info['summary'])
        video['duration'] = episode_info['runtime'] * 60
        video['premiered'] = episode_info['airdate']
    list_item.setInfo('video', video)
    if episode_info['image']:
        list_item.addAvailableArtwork(episode_info['image']['original'], 'thumb')
    return list_item


def parse_nfo_url(nfo_url):
    """Extract show ID from NFO URL"""
    for regexp in SHOW_ID_REGEXPS:
        show_id_match = regexp.search(nfo_url)
        if show_id_match:
            return UrlParseResult(show_id_match.group(1), show_id_match.group(2))
    return None
