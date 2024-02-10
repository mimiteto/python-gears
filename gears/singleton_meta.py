#! /usr/bin/env python3

"""
Module provides threadsafe singleton meta class.
"""

from threading import Lock


class SingletonController(type):
    """
    We provide singleton controller here as a meta class.
    Use it to create singleton classes.
    """

    _instance: dict[type, object] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instance:
                cls._instance[cls] = super().__call__(*args, **kwargs)
            return cls._instance[cls]
