#! /usr/bin/env python3

"""
Exposes package version
"""

import os

# pragma no cover

with open(
    os.path.dirname(os.path.abspath(__file__)) + "/../VERSION",
    'r',
    encoding='utf-8'
) as f:
    __version__ = f.read().strip()

with open(
    os.path.dirname(os.path.abspath(__file__)) + "/../README.md",
    'r',
    encoding='utf-8'
) as f:
    __description__ = f.read()

with open(
    os.path.dirname(os.path.abspath(__file__)) + "/../requirements.txt",
    'r',
    encoding='utf-8'
) as f:
    print(f.read())
