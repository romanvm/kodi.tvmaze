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

"""
Record TVmaze API responses as test fixtures

This script calls the real TVmaze API, so it must not be run in CI.
Run it manually from the repository root and review the changes in fixture files::

    .venv/bin/python tests/record_fixtures.py

Shows used in tests:

- Firefly (180): a small show with DVD alternate episode order.
- Sherlock (335): a show with specials and without DVD episode order.
"""

import json
import time

from fakes import kodi
from fakes.tvmaze import fixture_name, FIXTURES_DIR

kodi.install()

from libs.tvmaze_api import (  # noqa: E402
    _load_info,
    ALTERNATE_EPISODES_URL,
    ALTERNATE_LISTS_URL,
    EPISODE_INFO_URL,
    EPISODE_LIST_URL,
    SEARCH_BY_EXTERNAL_ID_URL,
    SEARCH_URL,
    SHOW_INFO_URL,
)

# The same params as in libs.tvmaze_api
SHOW_INFO_PARAMS = {'embed[]': ['cast', 'seasons', 'images', 'crew']}
EPISODE_LIST_PARAMS = {'specials': '1'}
ALTERNATE_EPISODES_PARAMS = {'embed': 'episodes'}

FIREFLY_ID = 180
FIREFLY_DVD_LIST_ID = 1
SHERLOCK_ID = 335

REQUESTS = (
    (SEARCH_URL, {'q': 'Firefly'}),
    (SEARCH_URL, {'q': 'Sherlock'}),
    (SHOW_INFO_URL.format(FIREFLY_ID), SHOW_INFO_PARAMS),
    (SHOW_INFO_URL.format(SHERLOCK_ID), SHOW_INFO_PARAMS),
    (EPISODE_LIST_URL.format(FIREFLY_ID), EPISODE_LIST_PARAMS),
    (EPISODE_LIST_URL.format(SHERLOCK_ID), EPISODE_LIST_PARAMS),
    (ALTERNATE_LISTS_URL.format(FIREFLY_ID), None),
    (ALTERNATE_LISTS_URL.format(SHERLOCK_ID), None),
    (ALTERNATE_EPISODES_URL.format(FIREFLY_DVD_LIST_ID), ALTERNATE_EPISODES_PARAMS),
    # "Serenity" pilot, Firefly S01E11 in the default order
    (EPISODE_INFO_URL.format(13005), None),
    (SEARCH_BY_EXTERNAL_ID_URL, {'thetvdb': '78874'}),
    (SEARCH_BY_EXTERNAL_ID_URL, {'imdb': 'tt0303461'}),
    (SEARCH_BY_EXTERNAL_ID_URL, {'thetvdb': '176941'}),
)

MAX_SEARCH_RESULTS = 5
MAX_CREW = 5

# TVmaze API rate limit is 20 calls per 10 seconds
REQUEST_INTERVAL_SECONDS = 0.6


def trim(url, data):
    """Trim large lists to keep fixtures readable"""
    if url == SEARCH_URL:
        return data[:MAX_SEARCH_RESULTS]
    if isinstance(data, dict) and 'crew' in data.get('_embedded', {}):
        crew = data['_embedded']['crew']
        creators = [item for item in crew if item['type'].lower() == 'creator']
        others = [item for item in crew if item['type'].lower() != 'creator']
        data['_embedded']['crew'] = (creators + others)[: max(MAX_CREW, len(creators))]
    return data


def main():
    FIXTURES_DIR.mkdir(exist_ok=True)
    for url, params in REQUESTS:
        name = fixture_name(url, params)
        print(f'Recording {name}')
        data = trim(url, _load_info(url, params))
        with (FIXTURES_DIR / name).open('w', encoding='utf-8') as fo:
            json.dump(data, fo, indent=2, ensure_ascii=False)
            fo.write('\n')
        time.sleep(REQUEST_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
