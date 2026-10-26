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
Fake TVmaze API

Replaces ``simple_requests.get`` and serves recorded TVmaze API responses
from JSON files in ``tests/fixtures``. Fixture files are created by ``tests/record_fixtures.py``.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple
from urllib.parse import urlencode, urlparse

import simple_requests as requests

FIXTURES_DIR = Path(__file__).resolve().parents[1] / 'fixtures'

ParamsType = Optional[Dict[str, Any]]


def fixture_name(url: str, params: ParamsType = None) -> str:
    """
    Get the name of a fixture file for an API request

    Example: ``http://api.tvmaze.com/shows/180`` with ``{'embed[]': ['cast', 'images']}``
    -> ``shows_180__embed=cast,images.json``
    """
    parts = [urlparse(url).path.strip('/').replace('/', '_')]
    for key, value in sorted((params or {}).items()):
        if isinstance(value, (list, tuple)):
            value = ','.join(value)
        parts.append(f'{key.replace("[]", "")}={value}')
    name = '__'.join(parts)
    return re.sub(r'[^\w.,=-]+', '-', name) + '.json'


class ApiCall(NamedTuple):
    url: str
    params: ParamsType
    headers: Optional[Dict[str, str]]

    @property
    def fixture_name(self) -> str:
        return fixture_name(self.url, self.params)


class FakeTVmazeApi:
    """
    Serves TVmaze API responses from fixture files

    Requests for which there is neither a fixture file nor an explicitly set response
    fail the test, so a typo in a fixture name cannot pass unnoticed.
    Use :meth:`set_error` to emulate API errors.
    """

    def __init__(self, fixtures_dir: Path = FIXTURES_DIR) -> None:
        self._fixtures_dir = fixtures_dir
        self._responses: Dict[str, Tuple[int, bytes]] = {}
        self.calls: List[ApiCall] = []

    def set_response(self, url: str, params: ParamsType = None, json_data: Any = None) -> None:
        """Set a successful response for a request instead of a fixture file"""
        self._responses[fixture_name(url, params)] = (200, json.dumps(json_data).encode('utf-8'))

    def set_error(self, url: str, params: ParamsType = None, status_code: int = 404) -> None:
        """Set an error response for a request"""
        content = json.dumps(
            {'name': 'Not Found', 'message': '', 'code': 0, 'status': status_code}
        ).encode('utf-8')
        self._responses[fixture_name(url, params)] = (status_code, content)

    def load_fixture(self, url: str, params: ParamsType = None) -> Any:
        """Load data from a fixture file for a request"""
        fixture_path = self._fixtures_dir / fixture_name(url, params)
        return json.loads(fixture_path.read_text(encoding='utf-8'))

    def get(
        self,
        url: str,
        params: ParamsType = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> requests.Response:
        self.calls.append(ApiCall(url, params, headers))
        name = fixture_name(url, params)
        if name in self._responses:
            status_code, content = self._responses[name]
            return self._make_response(url, params, status_code, content)
        fixture_path = self._fixtures_dir / name
        if not fixture_path.exists():
            raise AssertionError(
                f'Unexpected TVmaze API request: {url} {params}. '
                f'Fixture file {name} does not exist, use set_response() or set_error().'
            )
        return self._make_response(url, params, 200, fixture_path.read_bytes())

    def get_call_count(self, url: str, params: ParamsType = None) -> int:
        name = fixture_name(url, params)
        return sum(1 for call in self.calls if call.fixture_name == name)

    @staticmethod
    def _make_response(
        url: str, params: ParamsType, status_code: int, content: bytes
    ) -> requests.Response:
        response = requests.Response()
        response.status_code = status_code
        response.url = f'{url}?{urlencode(params, doseq=True)}' if params else url
        response.content = content
        return response
