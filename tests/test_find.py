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

"""Tests for "find" action"""

import json

from libs.tvmaze_api import SEARCH_URL


def test_find_show_returns_all_search_results(call_router, plugin, tvmaze):
    call_router(action='find', title='Firefly')

    assert tvmaze.get_call_count(SEARCH_URL, {'q': 'Firefly'}) == 1
    assert [item.url for item in plugin.directory_items] == [
        '180',
        '41101',
        '91069',
        '47868',
        '29781',
    ]
    assert [item.list_item.getLabel() for item in plugin.directory_items] == [
        'Firefly (2002)',
        'Firefly Lane (2021)',
        'Firefly Wedding (2026)',
        'Balala the Fairies: Ocean Magic (2018)',
        'Ateşböceği (2017)',
    ]
    assert all(item.is_folder for item in plugin.directory_items)
    assert all(item.list_item.offscreen for item in plugin.directory_items)
    assert plugin.end_of_directory_calls == 1


def test_find_show_sets_basic_show_info(call_router, plugin):
    call_router(action='find', title='Firefly')

    info_tag = plugin.directory_items[0].list_item.getVideoInfoTag()
    assert info_tag.get_value('setYear') == 2002
    assert info_tag.get_args('addAvailableArtwork') == (
        'https://static.tvmaze.com/uploads/images/medium_portrait/1/2600.jpg',
        'thumb',
    )
    assert info_tag.get_args('setUniqueIDs') == (
        {'tvmaze': '180', 'tvrage': '3548', 'tvdb': '78874', 'imdb': 'tt0303461'},
        'tvmaze',
    )
    # Episode guide is set only in "getdetails" action
    assert not info_tag.was_called('setEpisodeGuide')


def test_find_show_filters_by_year(call_router, plugin):
    call_router(action='find', title='Firefly', year='2021')

    assert [item.url for item in plugin.directory_items] == ['41101']
    assert plugin.directory_items[0].list_item.getLabel() == 'Firefly Lane (2021)'


def test_find_show_returns_all_results_if_year_does_not_match(call_router, plugin):
    call_router(action='find', title='Firefly', year='1999')

    assert len(plugin.directory_items) == 5


def test_find_show_without_premiere_date(call_router, plugin, tvmaze):
    search_results = tvmaze.load_fixture(SEARCH_URL, {'q': 'Firefly'})[:1]
    del search_results[0]['show']['premiered']
    del search_results[0]['show']['image']
    tvmaze.set_response(SEARCH_URL, {'q': 'Firefly'}, search_results)

    call_router(action='find', title='Firefly', year='2002')

    assert len(plugin.directory_items) == 1
    list_item = plugin.directory_items[0].list_item
    assert list_item.getLabel() == 'Firefly'
    info_tag = list_item.getVideoInfoTag()
    assert not info_tag.was_called('setYear')
    assert not info_tag.was_called('addAvailableArtwork')


def test_find_show_nothing_found(call_router, plugin, tvmaze):
    tvmaze.set_response(SEARCH_URL, {'q': 'Nonexistent show'}, [])

    call_router(action='find', title='Nonexistent show')

    assert plugin.directory_items == []
    assert plugin.end_of_directory_calls == 1


def test_find_show_api_error(call_router, plugin, tvmaze, caplog):
    tvmaze.set_error(SEARCH_URL, {'q': 'Firefly'}, status_code=500)

    call_router(action='find', title='Firefly')

    assert plugin.directory_items == []
    assert plugin.end_of_directory_calls == 1
    assert 'TVmaze returned an error: HTTPError: 500' in caplog.text


def test_find_show_sends_user_agent(call_router, tvmaze):
    call_router(action='find', title='Firefly')

    headers = tvmaze.calls[0].headers
    assert headers['User-Agent'].startswith('Kodi scraper for tvmaze.com by Roman V.M. v.')
    assert headers['Accept'] == 'application/json'
    # Make sure that JSON in a fixture file is valid
    assert json.dumps(tvmaze.load_fixture(SEARCH_URL, {'q': 'Firefly'}))
