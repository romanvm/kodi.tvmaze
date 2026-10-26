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

"""Tests for "NfoUrl" action"""

import json

import pytest

from libs.tvmaze_api import SEARCH_BY_EXTERNAL_ID_URL

FIREFLY_UNIQUE_IDS = {'tvmaze': '180'}

TVSHOW_NFO_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<tvshow>
    <title>Firefly</title>
    {}
</tvshow>
"""


def assert_found_show(plugin, show_id: str) -> None:
    assert len(plugin.directory_items) == 1
    item = plugin.directory_items[0]
    assert item.url == show_id
    assert item.is_folder
    info_tag = item.list_item.getVideoInfoTag()
    assert info_tag.get_args('setUniqueIDs') == ({'tvmaze': show_id}, 'tvmaze')
    assert json.loads(info_tag.get_value('setEpisodeGuide')) == {'tvmaze': show_id}
    assert plugin.end_of_directory_calls == 1


@pytest.mark.parametrize('action', ['NfoUrl', 'nfourl'])
def test_url_nfo_with_tvmaze_url(call_router, plugin, tvmaze, action):
    call_router(action=action, nfo='https://www.tvmaze.com/shows/180/firefly')

    assert_found_show(plugin, '180')
    assert tvmaze.calls == []


@pytest.mark.parametrize(
    'nfo, provider, external_id',
    [
        ('https://thetvdb.com/?tab=series&id=78874', 'thetvdb', '78874'),
        ('https://thetvdb.com/dereferrer/series/78874', 'thetvdb', '78874'),
        ('https://www.imdb.com/title/tt0303461/', 'imdb', 'tt0303461'),
    ],
)
def test_url_nfo_with_external_id_url(call_router, plugin, tvmaze, nfo, provider, external_id):
    call_router(action='NfoUrl', nfo=nfo)

    assert_found_show(plugin, '180')
    assert tvmaze.get_call_count(SEARCH_BY_EXTERNAL_ID_URL, {provider: external_id}) == 1


def test_url_nfo_with_unknown_external_id(call_router, plugin, tvmaze):
    tvmaze.set_error(SEARCH_BY_EXTERNAL_ID_URL, {'imdb': 'tt0000000'})

    call_router(action='NfoUrl', nfo='https://www.imdb.com/title/tt0000000/')

    assert plugin.directory_items == []
    assert plugin.end_of_directory_calls == 1


def test_url_nfo_without_show_url(call_router, plugin, tvmaze):
    call_router(action='NfoUrl', nfo='https://www.example.com/firefly')

    assert plugin.directory_items == []
    assert tvmaze.calls == []
    assert plugin.end_of_directory_calls == 1


@pytest.mark.parametrize(
    'uniqueids, expected_api_call',
    [
        ('<uniqueid type="tvmaze" default="true">180</uniqueid>', None),
        (
            '<uniqueid type="imdb" default="true">tt0303461</uniqueid>',
            (SEARCH_BY_EXTERNAL_ID_URL, {'imdb': 'tt0303461'}),
        ),
        (
            '<uniqueid type="tvdb" default="true">78874</uniqueid>',
            (SEARCH_BY_EXTERNAL_ID_URL, {'thetvdb': '78874'}),
        ),
    ],
)
def test_xml_tvshow_nfo_with_unique_ids(call_router, plugin, tvmaze, uniqueids, expected_api_call):
    call_router(action='NfoUrl', nfo=TVSHOW_NFO_TEMPLATE.format(uniqueids))

    assert_found_show(plugin, '180')
    if expected_api_call is None:
        assert tvmaze.calls == []
    else:
        assert tvmaze.get_call_count(*expected_api_call) == 1


def test_xml_tvshow_nfo_prefers_imdb_over_tvdb(call_router, plugin, tvmaze):
    uniqueids = (
        '<uniqueid type="tvdb">78874</uniqueid>'
        '<uniqueid type="imdb" default="true">tt0303461</uniqueid>'
    )

    call_router(action='NfoUrl', nfo=TVSHOW_NFO_TEMPLATE.format(uniqueids))

    assert_found_show(plugin, '180')
    assert [call.fixture_name for call in tvmaze.calls] == ['lookup_shows__imdb=tt0303461.json']


def test_xml_tvshow_nfo_falls_back_to_tvdb_if_imdb_not_found(call_router, plugin, tvmaze):
    tvmaze.set_error(SEARCH_BY_EXTERNAL_ID_URL, {'imdb': 'tt0000000'})
    uniqueids = (
        '<uniqueid type="imdb" default="true">tt0000000</uniqueid>'
        '<uniqueid type="tvdb">78874</uniqueid>'
    )

    call_router(action='NfoUrl', nfo=TVSHOW_NFO_TEMPLATE.format(uniqueids))

    assert_found_show(plugin, '180')


@pytest.mark.parametrize('year_tag', ['<year>2002</year>', '<premiered>2002-09-20</premiered>'])
def test_xml_tvshow_nfo_with_title_and_year(call_router, plugin, year_tag):
    call_router(action='NfoUrl', nfo=TVSHOW_NFO_TEMPLATE.format(year_tag))

    assert_found_show(plugin, '180')


def test_xml_tvshow_nfo_with_ambiguous_title(call_router, plugin, tvmaze):
    call_router(action='NfoUrl', nfo=TVSHOW_NFO_TEMPLATE.format(''))

    # Several shows found and no year to choose from
    assert plugin.directory_items == []
    assert tvmaze.get_call_count('http://api.tvmaze.com/search/shows', {'q': 'Firefly'}) == 1
    assert plugin.end_of_directory_calls == 1


def test_xml_tvshow_nfo_ignored_with_full_nfo_setting(call_router, plugin, tvmaze, addon_settings):
    addon_settings['full_nfo'] = True

    call_router(
        action='NfoUrl',
        nfo=TVSHOW_NFO_TEMPLATE.format('<uniqueid type="tvmaze">180</uniqueid>'),
    )

    assert plugin.directory_items == []
    assert tvmaze.calls == []
    assert plugin.end_of_directory_calls == 1


def test_xml_tvshow_nfo_ignored_with_full_nfo_path_setting(call_router, plugin, tvmaze):
    call_router(
        path_settings={'full_nfo': True, 'episode_order': 0},
        action='NfoUrl',
        nfo=TVSHOW_NFO_TEMPLATE.format('<uniqueid type="tvmaze">180</uniqueid>'),
    )

    assert plugin.directory_items == []
    assert tvmaze.calls == []


def test_xml_episode_nfo_with_tvmaze_id(call_router, plugin, tvmaze):
    nfo = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<episodedetails>
    <title>Serenity</title>
    <uniqueid type="tvmaze" default="true">13005</uniqueid>
</episodedetails>
"""

    call_router(action='NfoUrl', nfo=nfo)

    assert len(plugin.directory_items) == 1
    item = plugin.directory_items[0]
    assert item.url == '13005'
    info_tag = item.list_item.getVideoInfoTag()
    assert info_tag.get_args('setUniqueIDs') == ({'tvmaze': '13005'}, 'tvmaze')
    assert not info_tag.was_called('setEpisodeGuide')
    assert tvmaze.calls == []


def test_xml_episode_nfo_without_tvmaze_id(call_router, plugin, tvmaze):
    nfo = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<episodedetails>
    <title>Serenity</title>
    <uniqueid type="tvdb" default="true">297989</uniqueid>
</episodedetails>
"""

    call_router(action='NfoUrl', nfo=nfo)

    assert plugin.directory_items == []
    assert tvmaze.calls == []
    assert plugin.end_of_directory_calls == 1


def test_xml_episode_nfo_ignored_with_full_nfo_setting(call_router, plugin, addon_settings):
    addon_settings['full_nfo'] = True
    nfo = """<episodedetails>
    <uniqueid type="tvmaze" default="true">13005</uniqueid>
</episodedetails>
"""

    call_router(action='NfoUrl', nfo=nfo)

    assert plugin.directory_items == []
