# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import sys
from libs.actions import router
from web_pdb import catch_post_mortem

if __name__ == '__main__':
    with catch_post_mortem():
        router(router(sys.argv[2][1:]))
