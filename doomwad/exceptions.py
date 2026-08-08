class DoomWadError(Exception):
    """Base exception for all doomwad errors."""


class InvalidWadError(DoomWadError):
    """Raised when a file is not a well-formed WAD."""


class LumpNotFoundError(DoomWadError):
    """Raised when a requested lump does not exist."""
