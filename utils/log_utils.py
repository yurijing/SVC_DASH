"""Common utility functions for logging and security."""
import re
import datetime
from urllib.parse import urlparse


def timestamp():
    """Return current timestamp string for logging.

    Replaces the repeated pattern: str(datetime.datetime.now())
    across all project files.
    """
    return str(datetime.datetime.now())


def sanitize_filename(name):
    """Remove dangerous characters from filenames.

    Only allows alphanumeric, underscore, hyphen, and dot.
    All other characters (including path separators) are
    replaced with underscore to prevent path traversal.

    Args:
        name: Raw filename string (e.g. from URL parsing).

    Returns:
        Sanitized filename safe for filesystem operations.

    Examples:
        >>> sanitize_filename("../../../etc/passwd")
        '......_etc_passwd'
        >>> sanitize_filename("video_1.264")
        'video_1.264'
    """
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', name)


def validate_mpd_url(url):
    """Validate that a URL is safe for MPD fetching.

    Checks that the URL uses http or https scheme.
    Does NOT verify reachability or content type.

    Args:
        url: The MPD URL string to validate.

    Returns:
        The original URL if valid.

    Raises:
        ValueError: If the URL scheme is not http or https.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(
            "Invalid URL scheme: '{}'. Only http and https are allowed.".format(
                parsed.scheme))
    return url
