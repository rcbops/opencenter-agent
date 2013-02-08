# Exceptions that RoushAgent raises


class FileNotFound(Exception):
    """Raised when a file is missing."""
    pass


class NoConfigFound(Exception):
    """Raised when a config file has no contents."""
    pass
