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

"""Tests for addon call routing and settings"""

import pytest

from libs.actions import router
from libs.kodi_utils import Settings

FIREFLY_EPISODEGUIDE = '{"tvmaze": "180"}'
DVD_ORDER = 1


def test_router_unknown_action(call_router, plugin):
    with pytest.raises(RuntimeError, match='Invalid addon call'):
        call_router(action='unknown')

    assert plugin.end_of_directory_calls == 0


def test_router_without_path_settings(plugin):
    router('action=find&title=Firefly')

    assert len(plugin.directory_items) == 5
    assert plugin.end_of_directory_calls == 1


def test_path_settings_override_addon_settings(call_router, plugin, addon_settings):
    addon_settings['episode_order'] = 0

    call_router(
        path_settings={'episode_order': DVD_ORDER, 'full_nfo': False},
        action='getepisodelist',
        url=FIREFLY_EPISODEGUIDE,
    )

    assert Settings().get_value_int('episode_order') == DVD_ORDER
    assert plugin.directory_items[0].list_item.getLabel() == 'Serenity'


def test_path_settings_are_not_shared_between_calls(call_router, plugin):
    # With reuselanguageinvoker the Settings singleton survives between addon calls,
    # so path settings of one media source must not leak into another one
    call_router(path_settings={'episode_order': DVD_ORDER}, action='find', title='Firefly')
    call_router(action='getepisodelist', url=FIREFLY_EPISODEGUIDE)

    assert plugin.directory_items[-14].list_item.getLabel() == 'The Train Job'


def test_addon_settings_are_used_without_path_settings(call_router, plugin, addon_settings):
    addon_settings['episode_order'] = DVD_ORDER

    call_router(action='getepisodelist', url=FIREFLY_EPISODEGUIDE)

    assert plugin.directory_items[0].list_item.getLabel() == 'Serenity'
