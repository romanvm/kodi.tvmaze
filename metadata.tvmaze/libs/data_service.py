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
import json
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional, Dict, List, Tuple, Any, Sequence, NamedTuple, Type
from xml.etree import ElementTree as Etree

from xbmc import InfoTagVideo, Actor
from xbmcgui import ListItem

from . import tvmaze_api, cache_service as cache

InfoType = Dict[str, Any]  # pylint: disable=invalid-name

TAG_RE = re.compile(r'<[^>]+>')
SHOW_ID_REGEXPS = (
    r'(tvmaze)\.com/shows/(\d+)/[\w\-]',
    r'(thetvdb)\.com/.*?series/(\d+)',
    r'(thetvdb)\.com[\w=&\?/]+id=(\d+)',
    r'(imdb)\.com/[\w/\-]+/(tt\d+)',
)
SUPPORTED_ARTWORK_TYPES = ('poster', 'banner')
IMAGE_SIZES = ('large', 'original', 'medium')
MAX_ARTWORK_NUMBER = 10
CLEAN_PLOT_REPLACEMENTS = (
    ('<b>', '[B]'),
    ('</b>', '[/B]'),
    ('<i>', '[I]'),
    ('</i>', '[/I]'),
    ('</p><p>', '[CR]'),
)
SUPPORTED_EXTERNAL_IDS = ('tvdb', 'thetvdb', 'imdb')


class UrlParseResult(NamedTuple):
    provider: str
    show_id: str


class XmlParseResult(NamedTuple):
    title: str
    year: str
    uniqueids: Dict[str, str]


class BaseInfoTagPropertySetter(ABC):

    def __init__(self,
                 media_info: InfoType,
                 info_tag_method: str,
                 tvmaze_property: Optional[str] = None) -> None:
        self._media_info = media_info
        self._property_value = media_info.get(tvmaze_property)
        self._info_tag_method = info_tag_method

    @abstractmethod
    def should_set(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def set_info_tag_property(self, info_tag: InfoTagVideo) -> None:
        raise NotImplementedError


class SimpleInfoTagPropertySetter(BaseInfoTagPropertySetter):
    """
    Sets a media property from a dictionary returned by TVmaze API to
    xbmc.InfoTagVideo class instance
    """

    def should_set(self) -> bool:
        return bool(self._property_value)

    def get_method_args(self) -> Sequence[Any]:
        return (self._property_value,)

    def set_info_tag_property(self, info_tag: InfoTagVideo) -> None:
        args = self.get_method_args()
        method = getattr(info_tag, self._info_tag_method)
        method(*args)


class PlotSetter(SimpleInfoTagPropertySetter):

    def get_method_args(self) -> Sequence[Any]:
        cleaned_plot = _clean_plot(self._property_value)
        return (cleaned_plot,)


class MediaTypeSetter(SimpleInfoTagPropertySetter):

    def should_set(self) -> bool:
        return True

    def get_method_args(self) -> Sequence[Any]:
        return ('tvshow',)


class EpisodeGuideSetter(SimpleInfoTagPropertySetter):

    def should_set(self) -> bool:
        return True

    def _get_unique_ids(self) -> Dict[str, str]:
        """Extract unique ID in various online databases"""
        if unique_ids := self._media_info.get('unique_ids'):
            return unique_ids
        unique_ids = {'tvmaze': str(self._media_info['id'])}
        externals = self._media_info.get('externals') or {}
        for key, value in externals.items():
            if key == 'thetvdb':
                key = 'tvdb'
            unique_ids[key] = str(value)
        self._media_info['unique_ids'] = unique_ids
        return unique_ids

    def get_method_args(self) -> Sequence[Any]:
        unique_ids = self._get_unique_ids()
        return (json.dumps(unique_ids),)


class UniqueIDsSetter(EpisodeGuideSetter):

    def get_method_args(self) -> Sequence[Any]:
        unique_ids = self._get_unique_ids()
        return unique_ids, 'tvmaze'


class CountrySetter(SimpleInfoTagPropertySetter):

    def should_set(self) -> bool:
        channel = self._media_info.get('network')
        if channel is None:
            channel = self._media_info.get('webChannel')
        if channel is None:
            return False
        country = channel.get('country')
        if country is None:
            return False
        return True

    def get_method_args(self) -> Sequence[Any]:
        channel = self._media_info.get('network') or self._media_info.get('webChannel')
        return ([channel['country']['name']],)


class StudioSetter(SimpleInfoTagPropertySetter):

    def should_set(self) -> bool:
        channel = self._media_info.get('network')
        if channel is None:
            channel = self._media_info.get('webChannel')
        if channel is None:
            return False
        return True

    def get_method_args(self) -> Sequence[Any]:
        channel = self._media_info.get('network') or self._media_info.get('webChannel')
        return ([channel['name']],)


class YearSetter(SimpleInfoTagPropertySetter):

    def get_method_args(self) -> Sequence[Any]:
        year = self._property_value[:4]
        return (int(year),)

class PremieredSetter(SimpleInfoTagPropertySetter):

    def get_method_args(self) -> Sequence[Any]:
        return (self._property_value,)


class CreatorsSetter(SimpleInfoTagPropertySetter):

    def should_set(self) -> bool:
        return bool(self._media_info.get('_embedded', {}).get('crew'))

    def _get_credits(self) -> List[str]:
        """Extract show creator(s) from show info"""
        credits_ = []
        for item in self._media_info['_embedded']['crew']:
            if item['type'].lower() == 'creator':
                credits_.append(item['person']['name'])
        return credits_

    def get_method_args(self) -> Sequence[Any]:
        credits = self._get_credits()
        return (credits,)


class CastSetter(SimpleInfoTagPropertySetter):

    def should_set(self) -> bool:
        return bool(self._media_info.get('_embedded', {}).get('cast'))

    def get_method_args(self) -> Sequence[Any]:
        cast = []
        for index, item in enumerate(self._media_info['_embedded']['cast'], 1):
            data = {
                'name': item['person']['name'],
                'role': item['character']['name'],
                'order': index,
            }
            thumb = None
            if item['character'].get('image') is not None:
                thumb = _extract_artwork_url(item['character']['image'])
            if not thumb and item['person'].get('image') is not None:
                thumb = _extract_artwork_url(item['person']['image'])
            if thumb:
                data['thumbnail'] = thumb
            cast.append(Actor(**data))
        return (cast,)


class AvailableArtworkSetter(BaseInfoTagPropertySetter):

    def should_set(self) -> bool:
        return True

    def set_info_tag_property(self, info_tag: InfoTagVideo) -> None:
        set_available_artwork_method = getattr(info_tag, self._info_tag_method)
        image = self._media_info.get('image') or {}
        image_url = _extract_artwork_url(image)
        if image_url:
            set_available_artwork_method(image_url, 'poster')
        artwork = _extract_artwork(self._media_info)
        for artwork_type, artwork_list in artwork.items():
            for item in artwork_list[:MAX_ARTWORK_NUMBER]:
                resolutions = item.get('resolutions') or {}
                url = _extract_artwork_url(resolutions)
                if artwork_type in SUPPORTED_ARTWORK_TYPES and url:
                    set_available_artwork_method(url, artwork_type)


class RatingSetter(BaseInfoTagPropertySetter):

    def should_set(self) -> bool:
        return True

    def set_info_tag_property(self, info_tag: InfoTagVideo) -> None:
        set_rating_method = getattr(info_tag, self._info_tag_method)
        imdb_rating = self._media_info.get('imdb_rating')
        default_rating = self._media_info.get('default_rating') or 'TVmaze'
        is_imdb_default = default_rating == 'IMDB' and imdb_rating is not None
        if self._property_value is not None and self._property_value['average'] is not None:
            rating = float(self._media_info['rating']['average'])
            set_rating_method(rating, type='tvmaze', isdefault=not is_imdb_default)
        if imdb_rating is not None:
            set_rating_method(imdb_rating['rating'], imdb_rating['votes'], type='imdb',
                       isdefault=is_imdb_default)


class SeasonInfoSetter(BaseInfoTagPropertySetter):

    def should_set(self) -> bool:
        return bool(self._media_info.get('_embedded', {}).get('seasons'))

    def set_info_tag_property(self, info_tag: InfoTagVideo) -> None:
        add_season_method = getattr(info_tag, self._info_tag_method)
        for season in self._media_info['_embedded']['seasons']:
            add_season_method(season['number'], season.get('name') or '')
            image = season.get('image')
            if image is not None:
                url = _extract_artwork_url(image)
                if url:
                    info_tag.addAvailableArtwork(url, 'poster', season=season['number'])


SHOW_MEDIA_PROPERTY_SETTERS: List[Tuple[str, Type[SimpleInfoTagPropertySetter],  Optional[str]]] = [
    ('setPlot', PlotSetter, 'summary'),
    ('setPlotOutline', PlotSetter, 'summary'),
    ('setGenres', SimpleInfoTagPropertySetter, 'genres'),
    ('setTitle', SimpleInfoTagPropertySetter, 'name'),
    ('setTvShowTitle', SimpleInfoTagPropertySetter, 'name'),
    ('status', 'setTvShowStatus', SimpleInfoTagPropertySetter, 'status'),
    ('setMediaType', MediaTypeSetter, None),
    ('setEpisodeGuide', EpisodeGuideSetter, None),
    ('setUniqueIDs', UniqueIDsSetter, None),
    ('setCountries', CountrySetter, None),
    ('setStudios', StudioSetter, None),
    ('setYear', YearSetter, 'premiered'),
    ('setPremiered', PremieredSetter, 'premiered'),
    ('setWriters', CreatorsSetter, None),
    ('setCast', CastSetter, None),
    ('addAvailableArtwork', AvailableArtworkSetter, None),
    ('setRating', RatingSetter, 'rating'),
    ('addSeason', SeasonInfoSetter, None),
]


def _process_episode_list(episode_list: List[InfoType]) -> Dict[str, InfoType]:
    """Convert embedded episode list to a dict"""
    processed_episodes = {}
    specials_list = []
    for episode in episode_list:
        # xbmc/video/VideoInfoScanner.cpp ~ line 1010
        # "episode 0 with non-zero season is valid! (e.g. prequel episode)"
        if episode['number'] is not None or episode.get('type') == 'significant_special':
            # In some orders episodes with the same ID may occur more than once,
            # so we need a unique key.
            key = f'{episode["id"]}_{episode["season"]}_{episode["number"]}'
            processed_episodes[key] = episode
        else:
            specials_list.append(episode)
    specials_list.sort(key=lambda ep: ep['airdate'])
    for ep_number, special in enumerate(specials_list, 1):
        special['season'] = 0
        special['number'] = ep_number
        key = f'{special["id"]}_{special["season"]}_{special["number"]}'
        processed_episodes[key] = special
    return processed_episodes


def get_episodes_map(show_id: str, episode_order: str) -> Optional[Dict[str, InfoType]]:
    processed_episodes = cache.load_episodes_map_from_cache(show_id)
    if not processed_episodes:
        episode_list = tvmaze_api.load_episode_list(show_id, episode_order)
        if episode_list:
            processed_episodes = _process_episode_list(episode_list)
            cache.cache_episodes_map(show_id, processed_episodes)
    return processed_episodes or {}


def get_episode_info(show_id: str,
                     episode_id: str,
                     season: str,
                     episode: str,
                     episode_order: str) -> Optional[InfoType]:
    """
    Load episode info

    :param show_id:
    :param episode_id:
    :param season:
    :param episode:
    :param episode_order:
    :return: episode info or None
    """
    episode_info = None
    episodes_map = get_episodes_map(show_id, episode_order)
    if episodes_map is not None:
        try:
            key = f'{episode_id}_{season}_{episode}'
            episode_info = episodes_map[key]
        except KeyError as exc:
            logging.error('Unable to retrieve episode info: %s', exc)
    if episode_info is None:
        episode_info = tvmaze_api.load_episode_info(episode_id)
    return episode_info


def _clean_plot(plot: str) -> str:
    """Replace HTML tags with Kodi skin tags"""
    for repl in CLEAN_PLOT_REPLACEMENTS:
        plot = plot.replace(repl[0], repl[1])
    plot = TAG_RE.sub('', plot)
    return plot


def _extract_artwork_url(resolutions: Dict[str, str]) -> str:
    """Extract image URL from the list of available resolutions"""
    url = ''
    for image_size in IMAGE_SIZES:
        url = resolutions.get(image_size) or ''
        if isinstance(url, dict):
            url = url.get('url') or ''
            if url:
                break
    return url


def _extract_artwork(show_info: InfoType) -> Dict[str, List[Dict[str, Any]]]:
    artwork = defaultdict(list)
    for item in show_info['_embedded']['images']:
        artwork[item['type']].append(item)
    return artwork


def set_list_item_fanart(media_info: InfoType, list_item: ListItem) -> None:
    kodi_fanart = []
    artwork = _extract_artwork(media_info)
    fanart = artwork.get('background')
    if not fanart:
        return
    for item in fanart[:MAX_ARTWORK_NUMBER]:
        resolutions = item.get('resolutions') or {}
        url = _extract_artwork_url(resolutions)
        if url:
            kodi_fanart.append({'image': url})
    if kodi_fanart:
        list_item.setAvailableFanart(kodi_fanart)


def add_basic_show_info(list_item: ListItem, show_info: InfoType) -> None:
    info_tag = list_item.getVideoInfoTag()
    UniqueIDsSetter(show_info, 'setUniqueIDs', None).set_info_tag_property(info_tag)


def add_full_show_info(list_item: ListItem, show_info: InfoType) -> None:
    """Add main show info to a list item"""
    info_tag = list_item.getVideoInfoTag()
    for info_tag_method, setter_class, tvmaze_property in SHOW_MEDIA_PROPERTY_SETTERS:
        setter = setter_class(show_info, info_tag_method, tvmaze_property)
        if setter.should_set():
            setter.set_info_tag_property(info_tag)
    set_list_item_fanart(show_info, list_item)


def add_episode_info(list_item: ListItem,
                     episode_info: InfoType,
                     full_info: bool = True) -> ListItem:
    """Add episode info to a list item"""
    video = {
        'title': episode_info['name'],
        'season': episode_info['season'],
        'episode': episode_info['number'],
        'mediatype': 'episode',
    }
    if episode_info['airdate'] is not None:
        video['aired'] = episode_info['airdate']
    if full_info:
        summary = episode_info.get('summary')
        if summary is not None:
            video['plot'] = video['plotoutline'] = _clean_plot(summary)
        if episode_info['runtime'] is not None:
            video['duration'] = episode_info['runtime'] * 60
        image = episode_info.get('image') or {}
        image_url = _extract_artwork_url(image)
        if image_url:
            list_item.addAvailableArtwork(image_url, 'thumb')
        list_item.setUniqueIDs({'tvmaze': str(episode_info['id'])}, 'tvmaze')
    list_item.setInfo('video', video)
    return list_item


def parse_url_nfo_contents(nfo: str) -> Optional[UrlParseResult]:
    """Extract show ID from NFO file contents"""
    for regexp in SHOW_ID_REGEXPS:
        show_id_match = re.search(regexp, nfo, re.I)
        if show_id_match is not None:
            provider = show_id_match.group(1)
            show_id = show_id_match.group(2)
            logging.debug('Matched show ID %s by regexp "%s"', show_id, regexp)
            return UrlParseResult(provider, show_id)
    logging.debug('Unable to find show ID in an NFO file')
    return None


def parse_url_nfo(nfo: str) -> Optional[InfoType]:
    show_info = None
    url_parse_result = parse_url_nfo_contents(nfo)
    if url_parse_result is not None:
        if url_parse_result.provider == 'tvmaze':
            show_info = {'id': int(url_parse_result.show_id)}
        else:
            show_info = tvmaze_api.load_show_info_by_external_id(
                url_parse_result.provider,
                url_parse_result.show_id
            )
    return show_info


def parse_xml_nfo_contents(nfo: str) -> XmlParseResult:
    root = Etree.fromstring(nfo)
    title = ''
    year = ''
    uniqueids = {}
    title_tag = root.find('title')
    if title_tag is not None:
        title = title_tag.text
    year_tag = root.find('year')
    if year_tag is not None:
        year = year_tag.text
    if not year:
        premiered_tag = root.find('premiered')
        if premiered_tag is not None:
            year = premiered_tag.text[:4]
    for uniqueid_tag in root.findall('uniqueid'):
        provider = uniqueid_tag.attrib.get('type')
        if provider is not None:
            if provider == 'tvdb':
                provider = 'thetvdb'
            uniqueids[provider] = uniqueid_tag.text
    return XmlParseResult(title, year, uniqueids)


def parse_tvshow_xml_nfo(nfo: str) -> Optional[InfoType]:
    show_info = None
    xml_parse_result = parse_xml_nfo_contents(nfo)
    if 'tvmaze' in xml_parse_result.uniqueids:
        show_info = {'id': int(xml_parse_result.uniqueids['tvmaze'])}
    elif 'imdb' in xml_parse_result.uniqueids:
        show_info = tvmaze_api.load_show_info_by_external_id(
            'imdb',
            xml_parse_result.uniqueids['imdb']
        )
    elif 'thetvdb' in xml_parse_result.uniqueids:
        show_info = tvmaze_api.load_show_info_by_external_id(
            'thetvdb',
            xml_parse_result.uniqueids['thetvdb']
        )
    if show_info is None and xml_parse_result.title:
        search_results = search_show(xml_parse_result.title, xml_parse_result.year)
        if search_results and len(search_results) == 1:
            show_info = search_results[0]
    return show_info


def parse_episode_xml_nfo(nfo: str) -> Optional[InfoType]:
    episode_info = None
    parse_result = parse_xml_nfo_contents(nfo)
    if 'tvmaze' in parse_result.uniqueids:
        episode_info = {'id': int(parse_result.uniqueids['tvmaze'])}
    return episode_info


def _filter_by_year(shows: List[InfoType], year: str) -> Optional[InfoType]:
    """
    Filter a show by year

    :param shows: the list of shows from TVmaze
    :param year: premiere year
    :return: a found show or None
    """
    for show in shows:
        premiered = show.get('premiered') or ''
        if premiered and premiered.startswith(str(year)):
            return show
    return None


def search_show(title: str, year: str) -> Sequence[InfoType]:
    logging.debug('Searching for TV show %s (%s)', title, year)
    raw_search_results = tvmaze_api.search_show(title)
    search_results = [res['show'] for res in raw_search_results]
    if len(search_results) > 1 and year:
        search_result = _filter_by_year(search_results, year)
        search_results = (search_result,) if search_result else ()
    return search_results


def parse_json_episogeguide(episodeguide: str) -> Optional[str]:
    try:
        uniqueids = json.loads(episodeguide)
    except ValueError:
        return None
    show_id = uniqueids.get('tvmaze')
    if show_id is not None:
        return show_id
    for external_id_type in SUPPORTED_EXTERNAL_IDS:
        external_id = uniqueids.get(external_id_type)
        if external_id is None:
            continue
        if external_id == 'tvdb':
            external_id = 'thetvdb'
        show_info = tvmaze_api.load_show_info_by_external_id(external_id_type, external_id)
        if show_info:
            return str(show_info['id'])
    return None


def parse_url_episodeguide(episodeguide: str) -> Optional[str]:
    show_id = None
    parse_result = parse_url_nfo_contents(episodeguide)
    if not parse_result:
        return None
    if parse_result.provider == 'tvmaze':
        show_info = tvmaze_api.load_show_info(parse_result.show_id)
    else:
        show_info = tvmaze_api.load_show_info_by_external_id(
            parse_result.provider,
            parse_result.show_id
        )
    if show_info:
        show_id = str(show_info['id'])
    return show_id


def set_show_artwork(show_info: InfoType, list_item: ListItem) -> ListItem:
    """Set available images for a show"""
    fanart_list = []
    artwork = _extract_artwork(show_info)
    for artwork_type, artwork_list in artwork.items():
        for item in artwork_list[:MAX_ARTWORK_NUMBER]:
            resolutions = item.get('resolutions') or {}
            url = _extract_artwork_url(resolutions)
            if artwork_type in SUPPORTED_ARTWORK_TYPES and url:
                list_item.addAvailableArtwork(url, artwork_type)
            elif artwork_type == 'background' and url:
                fanart_list.append({'image': url})
    if fanart_list:
        list_item.setAvailableFanart(fanart_list)
    return list_item
