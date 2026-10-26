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

"""Tests for "getdetails" and "getartwork" actions"""

import json
import os

import pytest
import xbmcvfs

from fakes import kodi
from libs.tvmaze_api import SEARCH_BY_EXTERNAL_ID_URL, SHOW_INFO_URL

SHOW_INFO_PARAMS = {'embed[]': ['cast', 'seasons', 'images', 'crew']}
FIREFLY_SHOW_URL = SHOW_INFO_URL.format(180)
FIREFLY_UNIQUE_IDS = {'tvmaze': '180', 'tvrage': '3548', 'tvdb': '78874', 'imdb': 'tt0303461'}
IMAGES_URL = 'https://static.tvmaze.com/uploads/images/'


def get_resolved_info_tag(plugin) -> kodi.RecordingInfoTag:
    assert plugin.resolved is not None, 'setResolvedUrl was not called'
    assert plugin.resolved.succeeded
    return plugin.resolved.list_item.getVideoInfoTag()


def get_artwork(info_tag: kodi.RecordingInfoTag, art_type: str, season: int = -1):
    return [
        call.args[0]
        for call in info_tag.get_calls('addAvailableArtwork')
        if call.args[1] == art_type and call.kwargs.get('season', -1) == season
    ]


def test_get_details_by_show_id(call_router, plugin, tvmaze):
    call_router(action='getdetails', url='180')

    info_tag = get_resolved_info_tag(plugin)
    assert plugin.resolved.list_item.getLabel() == 'Firefly'
    assert tvmaze.get_call_count(FIREFLY_SHOW_URL, SHOW_INFO_PARAMS) == 1
    assert info_tag.get_value('setTitle') == 'Firefly'
    assert info_tag.get_value('setTvShowTitle') == 'Firefly'
    assert info_tag.get_value('setTvShowStatus') == 'Ended'
    assert info_tag.get_value('setMediaType') == 'tvshow'
    assert info_tag.get_value('setGenres') == ['Drama', 'Adventure', 'Science-Fiction']
    assert info_tag.get_value('setCountries') == ['United States']
    assert info_tag.get_value('setStudios') == ['FOX']
    assert info_tag.get_value('setYear') == 2002
    assert info_tag.get_value('setPremiered') == '2002-09-20'
    assert info_tag.get_value('setWriters') == ['Joss Whedon']
    assert info_tag.get_args('setUniqueIDs') == (FIREFLY_UNIQUE_IDS, 'tvmaze')
    assert json.loads(info_tag.get_value('setEpisodeGuide')) == FIREFLY_UNIQUE_IDS
    rating_call = info_tag.get_calls('setRating')[0]
    assert rating_call.args == (9.0,)
    assert rating_call.kwargs == {'type': 'tvmaze', 'isdefault': True}
    assert plugin.end_of_directory_calls == 1


def test_get_details_cleans_plot(call_router, plugin):
    call_router(action='getdetails', url='180')

    info_tag = get_resolved_info_tag(plugin)
    plot = info_tag.get_value('setPlot')
    assert plot.startswith('Five hundred years in the future, a renegade crew')
    assert '<' not in plot
    assert info_tag.get_value('setPlotOutline') == plot


def test_get_details_sets_cast(call_router, plugin):
    call_router(action='getdetails', url='180')

    cast = get_resolved_info_tag(plugin).get_value('setCast')
    assert len(cast) == 9
    assert [actor.getOrder() for actor in cast] == list(range(1, 10))
    first_actor = cast[0]
    assert first_actor.getName() == 'Nathan Fillion'
    assert first_actor.getRole() == 'Captain Malcolm "Mal" Reynolds'
    assert first_actor.getThumbnail().startswith(IMAGES_URL)


def test_get_details_sets_artwork(call_router, plugin):
    call_router(action='getdetails', url='180')

    info_tag = get_resolved_info_tag(plugin)
    thumbs = get_artwork(info_tag, 'thumb')
    assert len(thumbs) == 1
    assert thumbs[0].endswith('/1/2600.jpg')
    posters = get_artwork(info_tag, 'poster')
    # Main show image + the same image from the list of show images
    assert len(posters) == 2
    assert all(url.endswith('/1/2600.jpg') for url in posters)
    assert len(get_artwork(info_tag, 'banner')) == 2
    assert len(get_artwork(info_tag, 'poster', season=1)) == 1
    # Kodi 21 does not have InfoTagVideo.setAvailableFanart
    fanart = plugin.resolved.list_item.available_fanart
    assert len(fanart) == 4
    assert all(item['image'].startswith(IMAGES_URL) for item in fanart)


def test_get_details_sorts_main_images_first(call_router, plugin, tvmaze):
    show_info = tvmaze.load_fixture(FIREFLY_SHOW_URL, SHOW_INFO_PARAMS)
    show_info['_embedded']['images'].reverse()
    tvmaze.set_response(FIREFLY_SHOW_URL, SHOW_INFO_PARAMS, show_info)

    call_router(action='getdetails', url='180')

    info_tag = get_resolved_info_tag(plugin)
    # The main poster (marked as "main") goes first after the show "image"
    assert get_artwork(info_tag, 'poster')[1] == f'{IMAGES_URL}original_untouched/1/2600.jpg'


def test_get_details_image_sizes(call_router, plugin):
    call_router(action='getdetails', url='180')

    info_tag = get_resolved_info_tag(plugin)
    # "image" fields (show, season, cast) use "medium" size as a trade-off between size and quality
    medium_poster_url = f'{IMAGES_URL}medium_portrait/1/2600.jpg'
    assert get_artwork(info_tag, 'thumb') == [medium_poster_url]
    assert get_artwork(info_tag, 'poster')[0] == medium_poster_url
    assert '/medium_portrait/' in get_artwork(info_tag, 'poster', season=1)[0]
    assert '/medium_portrait/' in info_tag.get_value('setCast')[0].getThumbnail()
    # Images from the list of show images use "original" size
    assert get_artwork(info_tag, 'poster')[1] == f'{IMAGES_URL}original_untouched/1/2600.jpg'


@pytest.mark.parametrize('kodi_version', [21, 22], indirect=True)
def test_get_details_kodi_version_specific_info(call_router, plugin, kodi_version):
    call_router(action='getdetails', url='180')

    info_tag = get_resolved_info_tag(plugin)
    season_args = info_tag.get_args('addSeason')
    if kodi_version >= 22:
        assert info_tag.get_value('setOriginalLanguage') == 'English'
        assert season_args[:2] == (1, '')
        assert season_args[2].startswith("Captain Malcolm 'Mal' Reynolds")
        assert '<' not in season_args[2]
        assert len(info_tag.get_value('setAvailableFanart')) == 4
        assert plugin.resolved.list_item.available_fanart is None
    else:
        assert not info_tag.was_called('setOriginalLanguage')
        assert season_args == (1, '')
        assert len(plugin.resolved.list_item.available_fanart) == 4


def test_get_details_without_network(call_router, plugin, tvmaze):
    show_info = tvmaze.load_fixture(FIREFLY_SHOW_URL, SHOW_INFO_PARAMS)
    show_info['network'] = None
    show_info['webChannel'] = {'id': 1, 'name': 'Netflix', 'country': None}
    show_info['rating'] = {'average': None}
    show_info['image'] = None
    tvmaze.set_response(FIREFLY_SHOW_URL, SHOW_INFO_PARAMS, show_info)

    call_router(action='getdetails', url='180')

    info_tag = get_resolved_info_tag(plugin)
    assert info_tag.get_value('setStudios') == ['Netflix']
    assert not info_tag.was_called('setCountries')
    assert not info_tag.was_called('setRating')
    assert get_artwork(info_tag, 'thumb') == []


def test_get_details_uses_file_cache(call_router, plugin, tvmaze):
    call_router(action='getdetails', url='180')
    call_router(action='getdetails', url='180')

    assert tvmaze.get_call_count(FIREFLY_SHOW_URL, SHOW_INFO_PARAMS) == 1
    assert len(plugin.resolved_urls) == 2
    assert all(resolved.succeeded for resolved in plugin.resolved_urls)
    cache_file = os.path.join(
        xbmcvfs.translatePath('special://temp'), 'scrapers', 'metadata.tvmaze', '180.json'
    )
    assert os.path.exists(cache_file)


@pytest.mark.parametrize(
    'unique_ids, expected_api_call',
    [
        ({'tvmaze': '180'}, None),
        ({'tvdb': '78874'}, (SEARCH_BY_EXTERNAL_ID_URL, {'thetvdb': '78874'})),
        ({'imdb': 'tt0303461'}, (SEARCH_BY_EXTERNAL_ID_URL, {'imdb': 'tt0303461'})),
    ],
)
def test_get_details_by_unique_ids(call_router, plugin, tvmaze, unique_ids, expected_api_call):
    call_router(action='getdetails', uniqueIDs=json.dumps(unique_ids))

    info_tag = get_resolved_info_tag(plugin)
    assert info_tag.get_value('setTitle') == 'Firefly'
    if expected_api_call is not None:
        assert tvmaze.get_call_count(*expected_api_call) == 1


def test_get_details_by_unresolvable_unique_ids(call_router, plugin, tvmaze, caplog):
    tvmaze.set_error(SEARCH_BY_EXTERNAL_ID_URL, {'imdb': 'tt0000000'})

    call_router(action='getdetails', uniqueIDs=json.dumps({'imdb': 'tt0000000'}))

    assert plugin.resolved is not None
    assert not plugin.resolved.succeeded
    assert 'Unable to determine TVmaze show ID' in caplog.text
    assert plugin.end_of_directory_calls == 1


def test_get_details_show_not_found(call_router, plugin, tvmaze):
    tvmaze.set_error(SHOW_INFO_URL.format(999999), SHOW_INFO_PARAMS)

    call_router(action='getdetails', url='999999')

    assert plugin.resolved is not None
    assert not plugin.resolved.succeeded
    assert plugin.end_of_directory_calls == 1


def test_get_artwork(call_router, plugin):
    call_router(action='getartwork', id='180')

    info_tag = get_resolved_info_tag(plugin)
    assert len(get_artwork(info_tag, 'poster')) == 2
    assert len(get_artwork(info_tag, 'banner')) == 2
    assert len(plugin.resolved.list_item.available_fanart) == 4
    # Only artwork is set
    assert not info_tag.was_called('setTitle')


def test_get_artwork_without_show_id(call_router, plugin, tvmaze):
    call_router(action='getartwork')

    assert plugin.resolved is not None
    assert not plugin.resolved.succeeded
    assert tvmaze.calls == []
