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

"""Tests for "getepisodelist" and "getepisodedetails" actions"""

import json
import time
from typing import Dict
from urllib.parse import parse_qsl, unquote

import pytest

from libs.tvmaze_api import (
    ALTERNATE_EPISODES_URL,
    ALTERNATE_LISTS_URL,
    EPISODE_INFO_URL,
    EPISODE_LIST_URL,
    SEARCH_BY_EXTERNAL_ID_URL,
    SHOW_INFO_URL,
)

EPISODE_LIST_PARAMS = {'specials': '1'}
SHOW_INFO_PARAMS = {'embed[]': ['cast', 'seasons', 'images', 'crew']}
SHERLOCK_EPISODEGUIDE = json.dumps({'tvmaze': '335', 'tvdb': '176941', 'imdb': 'tt1475582'})
FIREFLY_EPISODEGUIDE = json.dumps({'tvmaze': '180', 'tvdb': '78874', 'imdb': 'tt0303461'})
DVD_ORDER = 1


def decode_url(url: str) -> Dict[str, str]:
    return dict(parse_qsl(unquote(url)))


def get_episodes(plugin):
    """Get (episode ID, season, episode, title) for each episode in a list"""
    episodes = []
    for item in plugin.directory_items:
        ids = decode_url(item.url)
        episodes.append(
            (ids['episode_id'], ids['season'], ids['episode'], item.list_item.getLabel())
        )
    return episodes


def test_get_episode_list(call_router, plugin, tvmaze):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 1
    # No alternate order is requested by default
    assert tvmaze.get_call_count(ALTERNATE_LISTS_URL.format(335)) == 0
    assert get_episodes(plugin) == [
        ('32178', '1', '1', 'A Study in Pink'),
        ('32179', '1', '2', 'The Blind Banker'),
        ('32180', '1', '3', 'The Great Game'),
        ('32181', '2', '1', 'A Scandal in Belgravia'),
        ('32182', '2', '2', 'The Hounds of Baskerville'),
        ('32183', '2', '3', 'The Reichenbach Fall'),
        ('32184', '3', '1', 'The Empty Hearse'),
        ('32185', '3', '2', 'The Sign of Three'),
        ('32186', '3', '3', 'His Last Vow'),
        # Significant specials keep their season and do not have a number
        ('401163', '4', 'None', 'The Abominable Bride'),
        ('941297', '4', '1', 'The Six Thatchers'),
        ('941298', '4', '2', 'The Lying Detective'),
        ('1004191', '4', '3', 'The Final Problem'),
        # Other specials are moved to season 0 and numbered by airdate
        ('839178', '0', '1', 'Unaired Pilot'),
        ('1785540', '0', '2', 'Unlocking Sherlock'),
        ('839479', '0', '3', 'Sherlock Uncovered'),
        ('32189', '0', '4', 'Many Happy Returns'),
        ('1785539', '0', '5', 'Unlocking Sherlock (2013)'),
    ]
    assert all(decode_url(item.url)['show_id'] == '335' for item in plugin.directory_items)
    assert all(item.is_folder for item in plugin.directory_items)
    assert plugin.end_of_directory_calls == 1


def test_get_episode_list_sets_basic_episode_info(call_router, plugin):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    info_tag = plugin.directory_items[0].list_item.getVideoInfoTag()
    assert info_tag.get_value('setTitle') == 'A Study in Pink'
    assert info_tag.get_value('setSeason') == 1
    assert info_tag.get_value('setEpisode') == 1
    special_info_tag = plugin.directory_items[-1].list_item.getVideoInfoTag()
    # Season 0 is not set because it's falsy
    assert not special_info_tag.was_called('setSeason')
    assert special_info_tag.get_value('setEpisode') == 5


def test_get_episode_list_sets_air_date(call_router, plugin):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    # Kodi reads InfoTagVideo first aired date from episode list items
    info_tag = plugin.directory_items[0].list_item.getVideoInfoTag()
    assert info_tag.get_value('setFirstAired') == '2010-07-25'
    special_info_tag = plugin.directory_items[-1].list_item.getVideoInfoTag()
    assert special_info_tag.get_value('setFirstAired') == '2013-12-25'


def test_get_episode_list_without_air_date(call_router, plugin, tvmaze):
    episode_list = tvmaze.load_fixture(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS)
    # Unaired episodes have an empty airdate
    episode_list[0]['airdate'] = ''
    tvmaze.set_response(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS, episode_list)

    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    info_tag = plugin.directory_items[0].list_item.getVideoInfoTag()
    assert not info_tag.was_called('setFirstAired')
    assert info_tag.get_value('setTitle') == 'A Study in Pink'


@pytest.mark.parametrize(
    'episodeguide, expected_api_call',
    [
        (json.dumps({'tvdb': '176941'}), (SEARCH_BY_EXTERNAL_ID_URL, {'thetvdb': '176941'})),
        # Legacy formats
        ('335', None),
        (
            'https://www.tvmaze.com/shows/335/sherlock',
            (SHOW_INFO_URL.format(335), SHOW_INFO_PARAMS),
        ),
        (
            'https://thetvdb.com/?tab=series&id=176941',
            (SEARCH_BY_EXTERNAL_ID_URL, {'thetvdb': '176941'}),
        ),
    ],
)
def test_get_episode_list_episodeguide_formats(
    call_router, plugin, tvmaze, episodeguide, expected_api_call
):
    call_router(action='getepisodelist', url=episodeguide)

    assert len(plugin.directory_items) == 18
    assert decode_url(plugin.directory_items[0].url)['show_id'] == '335'
    if expected_api_call is not None:
        assert tvmaze.get_call_count(*expected_api_call) == 1


@pytest.mark.parametrize(
    'episodeguide, log_message',
    [
        ('335', 'Invalid episodeguide format: 335 (a numeric string)'),
        ('https://www.tvmaze.com/shows/335/sherlock', 'probably URL'),
    ],
)
def test_get_episode_list_warns_about_legacy_episodeguide(
    call_router, caplog, episodeguide, log_message
):
    call_router(action='getepisodelist', url=episodeguide)

    assert any(
        record.levelname == 'WARNING' and log_message in record.getMessage()
        for record in caplog.records
    )


@pytest.mark.parametrize(
    'episodeguide', [json.dumps({'imdb': 'tt0000000'}), '{invalid json', 'not a show url']
)
def test_get_episode_list_unresolvable_episodeguide(call_router, plugin, tvmaze, episodeguide):
    tvmaze.set_error(SEARCH_BY_EXTERNAL_ID_URL, {'imdb': 'tt0000000'})

    call_router(action='getepisodelist', url=episodeguide)

    assert plugin.directory_items == []
    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 0
    assert plugin.end_of_directory_calls == 1


def test_get_episode_list_api_error(call_router, plugin, tvmaze):
    tvmaze.set_error(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS, status_code=500)

    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    assert plugin.directory_items == []
    assert plugin.end_of_directory_calls == 1


def test_get_episode_list_uses_memory_cache(call_router, plugin, tvmaze):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 1
    assert len(plugin.directory_items) == 36
    first_list = [item.url for item in plugin.directory_items[:18]]
    second_list = [item.url for item in plugin.directory_items[18:]]
    assert first_list == second_list


def test_get_episode_list_memory_cache_holds_one_show(call_router, tvmaze):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)
    call_router(action='getepisodelist', url=FIREFLY_EPISODEGUIDE)
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 2
    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(180), EPISODE_LIST_PARAMS) == 1


def test_get_episode_list_memory_cache_expires(call_router, tvmaze, monkeypatch):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)
    current_time = time.monotonic()
    monkeypatch.setattr('libs.cache_service.time.monotonic', lambda: current_time + 601)
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 2


def test_get_episode_list_dvd_order(call_router, plugin, tvmaze, addon_settings):
    addon_settings['episode_order'] = DVD_ORDER

    call_router(action='getepisodelist', url=FIREFLY_EPISODEGUIDE)

    assert tvmaze.get_call_count(ALTERNATE_LISTS_URL.format(180)) == 1
    assert tvmaze.get_call_count(ALTERNATE_EPISODES_URL.format(1), {'embed': 'episodes'}) == 1
    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(180), EPISODE_LIST_PARAMS) == 0
    episodes = get_episodes(plugin)
    assert len(episodes) == 14
    assert episodes[:3] == [
        ('13005', '1', '1', 'Serenity'),
        ('12995', '1', '2', 'The Train Job'),
        ('12996', '1', '3', 'Bushwhacked'),
    ]
    assert [episode[2] for episode in episodes] == [str(number) for number in range(1, 15)]


def test_get_episode_list_default_order(call_router, plugin):
    call_router(action='getepisodelist', url=FIREFLY_EPISODEGUIDE)

    episodes = get_episodes(plugin)
    assert episodes[0] == ('12995', '1', '1', 'The Train Job')
    assert episodes[10] == ('13005', '1', '11', 'Serenity')


def test_get_episode_list_dvd_order_path_setting(call_router, plugin):
    call_router(
        path_settings={'episode_order': DVD_ORDER, 'full_nfo': False},
        action='getepisodelist',
        url=FIREFLY_EPISODEGUIDE,
    )

    assert get_episodes(plugin)[0] == ('13005', '1', '1', 'Serenity')


def test_get_episode_list_falls_back_to_default_order(call_router, plugin, tvmaze, addon_settings):
    # Sherlock does not have DVD order
    addon_settings['episode_order'] = DVD_ORDER

    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    assert tvmaze.get_call_count(ALTERNATE_LISTS_URL.format(335)) == 1
    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 1
    assert len(plugin.directory_items) == 18


def test_get_episode_list_alternate_lists_api_error(call_router, plugin, tvmaze, addon_settings):
    addon_settings['episode_order'] = DVD_ORDER
    tvmaze.set_error(ALTERNATE_LISTS_URL.format(180), status_code=500)

    call_router(action='getepisodelist', url=FIREFLY_EPISODEGUIDE)

    assert get_episodes(plugin)[0] == ('12995', '1', '1', 'The Train Job')


def test_get_episode_details_after_episode_list(call_router, plugin, tvmaze):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)
    episode_url = plugin.directory_items[0].url

    call_router(action='getepisodedetails', url=episode_url)

    # The episode list is loaded from the memory cache
    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 1
    assert plugin.resolved is not None
    assert plugin.resolved.succeeded
    list_item = plugin.resolved.list_item
    assert list_item.getLabel() == 'A Study in Pink'
    info_tag = list_item.getVideoInfoTag()
    assert info_tag.get_value('setTitle') == 'A Study in Pink'
    assert info_tag.get_value('setSeason') == 1
    assert info_tag.get_value('setEpisode') == 1
    assert info_tag.get_value('setMediaType') == 'episode'
    assert info_tag.get_value('setFirstAired') == '2010-07-25'
    assert info_tag.get_value('setDuration') == 90 * 60
    assert info_tag.get_args('setUniqueIDs') == ({'tvmaze': '32178'}, 'tvmaze')
    plot = info_tag.get_value('setPlot')
    assert plot
    assert '<p>' not in plot
    assert info_tag.get_value('setPlotOutline') == plot
    thumb_url, art_type = info_tag.get_args('addAvailableArtwork')
    assert art_type == 'thumb'
    assert thumb_url.startswith('https://static.tvmaze.com/uploads/images/')
    assert plugin.end_of_directory_calls == 2


@pytest.mark.parametrize(
    'episode_index, expected',
    [
        (-1, ('Unlocking Sherlock (2013)', 0, 5)),
        (9, ('The Abominable Bride', 4, None)),
    ],
)
def test_get_episode_details_specials(call_router, plugin, episode_index, expected):
    call_router(action='getepisodelist', url=SHERLOCK_EPISODEGUIDE)

    call_router(action='getepisodedetails', url=plugin.directory_items[episode_index].url)

    assert plugin.resolved.succeeded
    info_tag = plugin.resolved.list_item.getVideoInfoTag()
    title, season, episode = expected
    assert info_tag.get_value('setTitle') == title
    if season:
        assert info_tag.get_value('setSeason') == season
    else:
        assert not info_tag.was_called('setSeason')
    if episode:
        assert info_tag.get_value('setEpisode') == episode
    else:
        assert not info_tag.was_called('setEpisode')


def test_get_episode_details_loads_episode_list(call_router, plugin, tvmaze):
    url = 'show_id%3D335%26episode_id%3D32186%26season%3D3%26episode%3D3'

    call_router(action='getepisodedetails', url=url)

    assert tvmaze.get_call_count(EPISODE_LIST_URL.format(335), EPISODE_LIST_PARAMS) == 1
    assert plugin.resolved.succeeded
    assert plugin.resolved.list_item.getLabel() == 'His Last Vow'


def test_get_episode_details_dvd_order(call_router, plugin, addon_settings):
    addon_settings['episode_order'] = DVD_ORDER
    call_router(action='getepisodelist', url=FIREFLY_EPISODEGUIDE)

    call_router(action='getepisodedetails', url=plugin.directory_items[0].url)

    info_tag = plugin.resolved.list_item.getVideoInfoTag()
    assert info_tag.get_value('setTitle') == 'Serenity'
    assert info_tag.get_value('setSeason') == 1
    assert info_tag.get_value('setEpisode') == 1


def test_get_episode_details_falls_back_to_episode_info(call_router, plugin, tvmaze, caplog):
    # Episode is not in the episode list with such season/episode numbers
    url = 'show_id%3D180%26episode_id%3D13005%26season%3D1%26episode%3D99'

    call_router(action='getepisodedetails', url=url)

    assert tvmaze.get_call_count(EPISODE_INFO_URL.format(13005)) == 1
    assert 'Unable to retrieve episode info' in caplog.text
    assert plugin.resolved.succeeded
    info_tag = plugin.resolved.list_item.getVideoInfoTag()
    assert info_tag.get_value('setTitle') == 'Serenity'
    assert info_tag.get_value('setEpisode') == 11


def test_get_episode_details_not_found(call_router, plugin, tvmaze):
    tvmaze.set_error(EPISODE_INFO_URL.format(999999))
    url = 'show_id%3D180%26episode_id%3D999999%26season%3D1%26episode%3D99'

    call_router(action='getepisodedetails', url=url)

    assert plugin.resolved is not None
    assert not plugin.resolved.succeeded
    assert plugin.end_of_directory_calls == 1
