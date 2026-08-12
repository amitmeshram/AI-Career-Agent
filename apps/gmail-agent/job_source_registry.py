import logging
import re
from urllib.parse import parse_qs, urlparse

from portal_config import GLOBAL_BLOCKED_PATTERNS, PORTALS


LOGGER = logging.getLogger(__name__)
_UNKNOWN_HOSTS_LOGGED = set()


def hostname_matches(hostname, domain):
    hostname = (hostname or "").lower().rstrip(".")
    domain = (domain or "").lower().rstrip(".")
    return hostname == domain or hostname.endswith(f".{domain}")


def detect_portal(url):
    hostname = (urlparse(url or "").hostname or "").lower()

    for portal_name, config in PORTALS.items():
        domain_match = any(
            hostname_matches(hostname, domain)
            for domain in config.get("domains", [])
        )
        pattern_match = any(
            re.search(pattern, hostname, flags=re.IGNORECASE)
            for pattern in config.get("domain_patterns", [])
        )

        if domain_match or pattern_match:
            return portal_name

    if hostname and hostname not in _UNKNOWN_HOSTS_LOGGED:
        LOGGER.debug(
            "Unknown job portal domain '%s' for URL: %s",
            hostname,
            url,
        )
        _UNKNOWN_HOSTS_LOGGED.add(hostname)

    return "unknown"


def is_valid_job_url(url):
    parsed = urlparse(url or "")
    path_and_query = parsed.path
    if parsed.query:
        path_and_query = f"{path_and_query}?{parsed.query}"
    lowered = path_and_query.lower()

    portal = detect_portal(url)
    if portal == "unknown":
        return False

    config = PORTALS[portal]
    blocked_patterns = [
        *GLOBAL_BLOCKED_PATTERNS,
        *config.get("blocked_patterns", []),
    ]
    if any(pattern.lower() in lowered for pattern in blocked_patterns):
        return False

    if portal == "glassdoor" and not is_valid_glassdoor_job_url(parsed):
        return False

    patterns = config.get("job_path_patterns", [])
    if not patterns:
        return True

    return any(
        re.search(pattern, parsed.path or "", flags=re.IGNORECASE)
        for pattern in patterns
    )


def get_browser_profile(portal):
    return PORTALS.get(portal, {}).get("profile_dir")


def get_scraper_name(portal):
    return PORTALS.get(portal, {}).get("scraper", "generic")


def is_valid_glassdoor_job_url(parsed):
    path = parsed.path or ""

    if re.fullmatch(r"/partner/jobListing\.htm", path, flags=re.IGNORECASE):
        return bool(parse_qs(parsed.query).get("jobListingId"))

    if re.fullmatch(r"/Job/[^/]+\.htm", path, flags=re.IGNORECASE):
        if re.search(r"(?:-jobs-|SRCH_)", path, flags=re.IGNORECASE):
            return False

        query = parse_qs(parsed.query)
        return bool(query.get("jl") or query.get("jobListingId") or "JV_" in path)

    return False
