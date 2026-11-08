import os


def debug(*args, **kwargs):
    # Only prints when OBSCURA_DEBUG=1. Never leave this on in production,
    # because debug output can contain private values.
    if os.getenv("OBSCURA_DEBUG", "0") == "1":
        print(*args, **kwargs)
