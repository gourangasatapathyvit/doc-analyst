"""Thread-safe Singleton Decorator.

Usage:
    from core.patterns import singleton

    @singleton
    class MyService:
        def __init__(self):
            self.cache = {}
"""
import threading
from functools import wraps


def singleton(cls):
    """Thread-safe Singleton Decorator with double-checked locking."""
    instances = {}
    lock = threading.Lock()

    @wraps(cls)
    def wrapper(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return wrapper
