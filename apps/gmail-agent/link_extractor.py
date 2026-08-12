import re
from html import unescape
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

from job_source_registry import is_valid_job_url


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "trk",
    "refid",
    "trackingid",
    "email",
    "email_name",
    "emailtoken",
    "usertoken",
    "mid",
    "mcid",
}

INDEED_KEEP_PARAMS = {
    "jk",
}


def hostname_matches(hostname, domain):
    hostname = (hostname or "").lower().rstrip(".")
    domain = (domain or "").lower().rstrip(".")
    return hostname == domain or hostname.endswith(f".{domain}")


def extract_urls_from_text(text):
    url_pattern = r'https?://[^\s<>"\']+'
    urls = re.findall(url_pattern, text or "")

    cleaned_urls = []

    for url in urls:
        url = url.strip()
        normalized = normalize_url(url)

        if is_real_job_link(normalized):
            cleaned_urls.append(normalized)

    return sorted(set(cleaned_urls))


def normalize_url(url):
    url = unescape((url or "").strip())

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    # LinkedIn email job links
    if hostname_matches(hostname, "linkedin.com") and "/comm/jobs/view/" in path:
        job_id = path.split("/comm/jobs/view/")[1].split("/")[0]
        return f"https://www.linkedin.com/jobs/view/{job_id}"

    # LinkedIn direct job links
    if hostname_matches(hostname, "linkedin.com") and "/jobs/view/" in path:
        job_id = path.split("/jobs/view/")[1].split("/")[0]
        return f"https://www.linkedin.com/jobs/view/{job_id}"

    # IIMJobs email links wrap the real job in a cm.iimjobs.com redirect.
    # Keep only canonical job detail URLs; homepage/course/apply redirects
    # must not enter the scrape/evaluation cycle.
    if hostname_matches(hostname, "iimjobs.com"):
        redirect = parse_qs(parsed.query).get("redirect", [""])[0]
        if redirect:
            return normalize_url(redirect)

        job_match = re.match(r"^/j/([^/?#]+-\d+)(?:/|$)", path, flags=re.IGNORECASE)
        if job_match:
            return f"https://www.iimjobs.com/j/{job_match.group(1)}"

    # Indeed job links: preserve job identity parameter only
    query_params = parse_qsl(parsed.query, keep_blank_values=False)

    if hostname_matches(hostname, "indeed.com"):
        kept_params = [
            (key, value)
            for key, value in query_params
            if key.lower() in INDEED_KEEP_PARAMS
        ]
    else:
        kept_params = [
            (key, value)
            for key, value in query_params
            if key.lower() not in TRACKING_PARAMS
        ]

    normalized = urlunparse((
        parsed.scheme,
        netloc,
        path,
        "",
        urlencode(kept_params),
        ""
    ))

    return normalized.rstrip("/")


def is_real_job_link(url):
    return is_valid_job_url(normalize_url(url))
