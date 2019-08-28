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
import sys
from six.moves import urllib_parse
import xbmcgui
import xbmcplugin
from . import tvmaze

_handle = int(sys.argv[1])


def find_show(title, year=None):
    try:
        result = tvmaze.search_show(title, year)
    except tvmaze.NotFoundError:
        pass
    else:
        li = xbmcgui.ListItem(result['name'], thumbnailImage=result['image']['original'])
        xbmcplugin.addDirectoryItem(_handle, url=result['_links']['self']['href'], listitem=li)


def get_details(url):
    try:
        result = tvmaze.get_show_details(url)
    except tvmaze.NotFoundError:
        pass
    else:
        li = xbmcgui.ListItem(result['name'])
        li.setProperty('video.ratings', '1')
        li.setProperty('video.rating1', str(result['rating']['average']))
        li.setProperty('video.unique_id', result['id'])
        li.setProperty('video.plot_outline', result['summary'])
        li.setProperty('video.plot', result['summary'])
        li.setProperty('video.duration_minutes', str(result['runtime']))
        li.setProperty('video.premiere_year', result['permiered'][:4])
        li.setProperty('video.status', result['status'])
        li.setProperty('video.first_aired', result['permiered'])
        li.setProperty('video.genre', ', '.join(result.get('genres') or []))
        li.setProperty('video.country', result['network']['country']['name'])
        li.setProperty('video.actors', str(len(result['_embedded']['cast'])))
        for i, item in enumerate(result['_embedded']['cast']):
            li.setProperty('video.actor{}.name'.format(i), item['person']['name'])
            li.setProperty('video.actor{}.role'.format(i), item['character']['name'])
            li.setProperty('video.actor{}.thumb'.format(i), item['person']['image']['original'])
        li.setProperty('video.studio', result['network']['name'])
        li.setProperty('video.episode_guide_url', url + '/episodes')
        xbmcplugin.setResolvedUrl(_handle, True, li)


def get_episode_list(path):
    result = tvmaze.get_eposode_list(path)
    for ep in result:
        li = xbmcgui.ListItem(ep['name'])
        li.setProperty('video.episode', str(ep['number']))
        li.setProperty('video.season', str(ep['season']))
        li.setProperty('video.ratings', '1')
        li.setProperty('video.rating1.value', '5')
        li.setProperty('video.rating1.votes', '100')
        li.setProperty('video.user_rating', '5')
        li.setProperty('video.unique_id', '123')
        li.setProperty('video.plot_outline', 'Outline yo')
        li.setProperty('video.plot', 'Plot yo')
        li.setProperty('video.tag_line', 'Tag yo')
        li.setProperty('video.duration_minutes', '110')
        li.setProperty('video.mpaa', 'T')
        li.setProperty('video.first_aired', '2007-01-01')
        li.setProperty('video.thumbs', '2')
        li.setProperty('video.thumb1.url', 'DefaultBackFanart.png')
        li.setProperty('video.thumb1.aspect', '1.78')
        li.setProperty('video.thumb2.url',
                        '/home/akva/Pictures/hawaii-shirt.png')
        li.setProperty('video.thumb2.aspect', '2.35')
        li.setProperty('video.genre', 'Action / Comedy')
        li.setProperty('video.country', 'Norway / Sweden / China')
        li.setProperty('video.writing_credits', 'None / Want / To Admit It')
        li.setProperty('video.director', 'spiff / spiff2')
        li.setProperty('video.actors', '2')
        li.setProperty('video.actor1.name', 'spiff')
        li.setProperty('video.actor1.role', 'himself')
        li.setProperty('video.actor1.sort_order', '2')
        li.setProperty('video.actor1.thumb', '/home/akva/Pictures/fish.jpg')
        li.setProperty('video.actor1.thumb_aspect', 'poster')
        li.setProperty('video.actor2.name', 'monkey')
        li.setProperty('video.actor2.role', 'orange')
        li.setProperty('video.actor2.sort_order', '1')
        li.setProperty('video.actor1.thumb_aspect', '1.78')
        li.setProperty('video.actor2.thumb', '/home/akva/Pictures/coffee.jpg')
        li.setProperty('video.date_added', '2016-01-01')


def get_episode_details(path):
    pass


def router(paramstring):
    """
    Route addon calls

    :param paramstring: url-encoded query string
    :type paramstring: str
    :raises ValueError: on unknown call action
    """
    params = dict(urllib_parse.parse_qsl(paramstring))
    if params['action'] == 'find':
        find_show(params['title'], params.get('year'))
    elif params['action'] == 'getdetails':
        get_details(params['url'])
    elif params['action'] == 'getepisodelist':
        get_episode_list(params['url'])
    elif params['action'] == 'getepisodedetails':
        get_episode_details(params['url'])
    else:
        raise ValueError('Invalid addon call: {}'.format(sys.argv))
    xbmcplugin.endOfDirectory(_handle)
