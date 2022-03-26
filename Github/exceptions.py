#== exceptions.py ==#

__all__ = (
    'APIError',
)

class APIError(Exception):
    """Base level exceptions raised by errors related to any API request or call"""
    pass