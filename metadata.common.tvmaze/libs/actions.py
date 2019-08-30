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

_HANDLE = int(sys.argv[1])


def find_show(title, year=None):
    """Find a show by title"""
    shows = tvmaze.search_show(title)
    if year is not None:
        show = tvmaze.filter_by_year(shows, year)
        shows = [show] if show else ()
    for show in shows:
        show_name = u'{} ({})'.format(show['show']['name'], show['show']['premiered'][:4])
        li = xbmcgui.ListItem(show_name, offscreen=True)
        li.setArt({'thumb': show['show']['image']['medium']})
        xbmcplugin.addDirectoryItem(
            _HANDLE,
            url=str(show['show']['id']),
            listitem=li,
            isFolder=True
        )


def get_details(show_id):
    pass


def get_episode_list(path):
    pass


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
    xbmcplugin.endOfDirectory(_HANDLE)
