# coding: utf-8
"""
This module includes sanity tests for scraper actions

The goal is to check for basic errors like typos and such.
"""
from __future__ import absolute_import
import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(THIS_DIR)
PROJECT_DIR = os.path.join(BASE_DIR, 'metadata.tvmaze')
sys.path.append(PROJECT_DIR)

sys.argv = ['plugin://metadata.tvmaze', '1', '']

from libs import actions, cache

cache.cache_show_info = lambda _: None
cache.load_show_info_from_cache = lambda _: None


def test_show_search(mock_response):
    with open(os.path.join(THIS_DIR, 'shows-search.json'), 'rb') as fo:
        search_results = json.load(fo)
    mock_response.json.return_value = search_results
    actions.find_show('Girls', '2012')
