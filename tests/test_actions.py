# coding: utf-8
"""
This module includes sanity tests for scraper actions

The goal is to check for basic errors like typos and such.
"""
# pylint: disable=missing-docstring
from __future__ import absolute_import

import io
import os
import sys

import pytest
from six.moves import urllib_parse

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(THIS_DIR)
PROJECT_DIR = os.path.join(BASE_DIR, 'metadata.tvmaze')
sys.path.append(PROJECT_DIR)

sys.argv = ['plugin://metadata.tvmaze', '1', '']

from libs import actions, cache  # pylint: disable=wrong-import-position

cache.cache_show_info = lambda _: None
cache.load_show_info_from_cache = lambda _: None


@pytest.mark.usefixtures('mock_response')
def test_show_search():
    actions.find_show('Girls', '2012')


@pytest.mark.usefixtures('mock_response')
def test_get_show_from_nfo():
    with io.open(os.path.join(THIS_DIR, 'tvshow.nfo'), 'r', encoding='utf-8') as fo:
        nfo = fo.read()
    actions.get_show_id_from_nfo(nfo)


@pytest.mark.usefixtures('mock_response')
def test_get_details():
    actions.get_details('82')


@pytest.mark.usefixtures('mock_response')
def test_get_episode_list():
    actions.get_episode_list('82')


@pytest.mark.usefixtures('mock_response')
def test_get_episode_details():
    encoded_ids = urllib_parse.urlencode({'show_id': '82', 'episode_id': '4952'})
    actions.get_episode_details(encoded_ids)


@pytest.mark.usefixtures('mock_response')
def test_get_artwork():
    actions.get_artwork('82')
