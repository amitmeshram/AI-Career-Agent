import base64
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup

from link_extractor import extract_urls_from_text, normalize_url, is_real_job_link
from job_source_registry import detect_portal
from portal_config import PORTALS
from paths import DATA_DIR, GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MAX_GMAIL_RESULTS_TO_INSPECT = 50


def get_gmail_service():
    creds = None

    if GMAIL_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                print("Gmail token expired or revoked. Re-authenticating...")
                GMAIL_TOKEN_FILE.unlink(missing_ok=True)
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(GMAIL_CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(GMAIL_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def extract_href_links_from_html(html):
    links = []

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href") or "").strip()
        if href.startswith("http"):
            links.append(href)

    return links


ACTION_LINK_TEXTS = {
    "",
    "apply",
    "apply now",
    "view all jobs",
    "view details",
    "view job",
    "view more jobs",
    "privacy policy",
    "unsubscribe",
}

POSTING_AGE_PATTERN = re.compile(
    r"\b(?:just posted|yesterday|\d+\+?\s*(?:d|day|days|h|hr|hrs|hour|hours)\s*ago|\d+d|today)\b",
    flags=re.IGNORECASE,
)
SALARY_PATTERN = re.compile(
    r"(?:[$â‚¹]\s?[\w.,]+(?:\s*-\s*[$â‚¹]?\s?[\w.,]+)?(?:\s*/\s*(?:hr|hour|year|yr))?|"
    r"[$â‚¹]\s?[\w.,]+\s*-\s*[$â‚¹]?\s?[\w.,]+|"
    r"\b\d+[LK]\s*-\s*\d+[LK]\b)",
    flags=re.IGNORECASE,
)
RATING_PATTERN = re.compile(r"\b\d(?:\.\d)?\s*â˜…")
COMMON_LOCATION_PATTERN = re.compile(
    r"\b("
    r"Riyadh|Mumbai|India|Saudi Arabia|Jeddah|Dammam|Dubai|Abu Dhabi|Doha|Qatar|"
    r"Kuwait|Bahrain|Oman|Remote|Hybrid|United States|New York|Naperville,\s*IL|"
    r"Chicago,\s*IL|United Kingdom|London|Bengaluru|Bangalore|Hyderabad|Pune|Delhi|"
    r"Sharjah"
    r")\b",
    flags=re.IGNORECASE,
)
BAYT_JOB_PATH_PATTERN = re.compile(
    r"/(?:en|ar)/(?:[^/]+/)?jobs/(?P<slug>[^/]+)-\d+(?:/|$)",
    flags=re.IGNORECASE,
)
BAYT_COUNTRY_PATTERN = re.compile(
    r"\b(UAE|United Arab Emirates|Saudi Arabia|Qatar|Kuwait|Bahrain|Oman|India)\b",
    flags=re.IGNORECASE,
)
GENERIC_REJECT_PATTERNS = {
    "unsubscribe": ["unsubscribe", "opt-out", "optout"],
    "privacy": ["privacy"],
    "terms": ["terms", "conditions"],
    "preferences": ["preference", "preferences", "email-settings", "emailsettings"],
    "logo": ["logo"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".webp", "image", "pixel"],
    "social": ["facebook", "twitter", "x.com", "instagram", "linkedin.com/company", "youtube"],
    "help": ["/help", "help centre", "help center", "support"],
    "settings": ["settings", "account"],
    "tracking pixel": ["tracking-pixel", "trackingpixel", "open.gif", "beacon"],
    "login": ["login", "signin", "sign-in"],
    "register": ["register", "signup", "sign-up"],
    "blog": ["/blog", "blog"],
    "career-advice": ["career-advice", "career advice", "advice"],
}
GENERIC_JOB_TERMS = [
    "job",
    "jobs",
    "role",
    "roles",
    "position",
    "vacancy",
    "hiring",
    "apply",
    "project manager",
    "manager",
    "engineer",
    "developer",
    "analyst",
    "consultant",
]
GENERIC_ACTION_TEXTS = {
    "view job",
    "view role",
    "view details",
    "apply",
    "apply now",
}


def clean_email_text(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    return value.strip(" -|â€¢Â·")


def clean_email_lines(value):
    lines = []
    for line in re.split(r"[\r\n]+", value or ""):
        line = clean_email_text(line)
        if line and line not in lines:
            lines.append(line)
    return lines


def normalize_bullets(value):
    return (
        (value or "")
        .replace("Ã¢â‚¬Â¢", " â€¢ ")
        .replace("Ã‚Â·", " â€¢ ")
        .replace("Â·", " â€¢ ")
        .replace("â€¢", " â€¢ ")
    )


def is_action_link_text(value):
    return clean_email_text(value).lower() in ACTION_LINK_TEXTS


def portal_from_url(url):
    portal = detect_portal(url)
    if portal != "unknown":
        return portal

    hostname = (urlparse(url or "").hostname or "").lower()
    if "indeed." in hostname:
        return "indeed"
    if "ziprecruiter." in hostname:
        return "ziprecruiter"
    if "glassdoor." in hostname:
        return "glassdoor"
    return portal


def find_job_card_text(anchor):
    best_text = clean_email_text(anchor.get_text(" ", strip=True))
    best_score = len(best_text)

    node = anchor
    for _ in range(8):
        node = node.parent
        if not node:
            break

        text = clean_email_text(node.get_text(" ", strip=True))
        if not text:
            continue

        link_count = len(node.find_all("a", href=True))
        if len(text) > 1000:
            continue

        score = len(text) + (25 if link_count > 1 else 0)
        if score > best_score:
            best_text = text
            best_score = score

        if len(text) >= 80 and link_count > 1:
            break

    return best_text


def find_nearby_visible_text(anchor):
    node = anchor
    for _ in range(6):
        node = node.parent
        if not node:
            break

        text = node.get_text("\n", strip=True)
        if text and len(text) <= 1200:
            return text

    return anchor.get_text("\n", strip=True)


def subject_location(subject):
    match = re.search(r"\bin\s+([A-Z][A-Za-z .,'-]+?)(?:\s+for you|\s+is now|\s*$)", subject or "")
    if match:
        return clean_email_text(match.group(1))
    return ""


def subject_role_company(subject):
    match = re.match(
        r"^(?P<role>.+?)\s+at\s+(?P<company>.+?)(?:\.|\s+and\s+|\s+\d+\s+more\b|$)",
        subject or "",
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""

    return clean_email_text(match.group("role")), clean_email_text(match.group("company"))


def remove_noise(value):
    value = clean_email_text(normalize_bullets(value))
    value = RATING_PATTERN.sub("", value)
    value = SALARY_PATTERN.sub("", value)
    value = POSTING_AGE_PATTERN.sub("", value)
    value = re.sub(r"\b(?:Easy Apply|Easily apply|Employer Est\.|Glassdoor Est\.|Full-Time|Part-Time|In-person|Be Seen First|New|Apply Now|View Details)\b", "", value, flags=re.IGNORECASE)
    value = value.replace("â˜…", " ")
    return clean_email_text(value)


def extract_location_from_text(text, subject=""):
    subject_loc = subject_location(subject)
    if subject_loc and re.search(rf"\b{re.escape(subject_loc)}\b", text or "", flags=re.IGNORECASE):
        return subject_loc

    matches = list(COMMON_LOCATION_PATTERN.finditer(text or ""))
    if matches:
        return clean_email_text(matches[-1].group(1))

    cleaned = remove_noise(text)
    city_state_matches = re.findall(
        r"\b([A-Z][A-Za-z .'-]+,\s*[A-Z]{2})\b",
        cleaned,
    )
    if city_state_matches:
        return clean_email_text(city_state_matches[-1])

    suffix = re.search(r"\b([A-Z][A-Za-z]+(?:,\s*[A-Z]{2})?|[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})$", cleaned)
    return clean_email_text(suffix.group(1)) if suffix else ""


def parse_indeed_metadata(anchor_texts, card_text, subject):
    role = first_role_text(anchor_texts)
    location = extract_location_from_text(card_text, subject)
    company = ""

    if role and not company:
        remainder = clean_email_text(re.sub(re.escape(role), "", card_text, count=1, flags=re.IGNORECASE))
        if location:
            company = clean_email_text(remainder.split(location, 1)[0])
        else:
            company = clean_email_text(re.split(r"\b(?:Easy Apply|Easily apply)\b", remainder, flags=re.IGNORECASE)[0])

    return clean_metadata(role, company, location)


def parse_glassdoor_metadata(anchor_texts, card_text, subject):
    text = remove_noise(card_text)
    location = extract_location_from_text(text, subject)

    match = re.match(r"^(?P<company>.+?)\s+\d(?:\.\d)?\s+(?P<rest>.+)$", card_text or "")
    if match:
        company = clean_email_text(match.group("company"))
        role_text = remove_noise(match.group("rest"))
    else:
        company = ""
        role_text = text

    if location and role_text.lower().endswith(location.lower()):
        role_text = clean_email_text(role_text[: -len(location)])

    return clean_metadata(first_role_text(anchor_texts) if not company else role_text, company, location)


def parse_ziprecruiter_metadata(anchor_texts, card_text, subject):
    role = first_role_text(anchor_texts)
    raw_text = clean_email_text(normalize_bullets(card_text))
    if role and role in raw_text:
        raw_text = raw_text.split(role, 1)[1]
        raw_text = f"{role} {raw_text}"
    raw_text = re.split(
        r"\s+(?:View Details|Apply Now|View More Jobs|Privacy Policy|Unsubscribe)\b",
        raw_text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = remove_noise(raw_text)
    location = extract_location_from_text(text, subject)
    company = ""

    if role:
        remainder = clean_email_text(re.sub(re.escape(role), "", text, count=1, flags=re.IGNORECASE))
        if location:
            company = clean_email_text(remainder.split(location, 1)[0])
            company = clean_email_text(company.split("â€¢", 1)[0])
        else:
            company = clean_email_text(re.split(r"\s+(?:Medical|Vision|Dental|Life|Retirement|\$)", remainder, flags=re.IGNORECASE)[0])

    return clean_metadata(role, company, location)


def humanize_bayt_slug(slug):
    replacements = {
        "amp": "&",
        "it": "IT",
        "icx": "ICX",
        "dm": "DM",
        "g": "G",
    }
    words = []

    for token in re.split(r"-+", slug or ""):
        normalized = token.lower()
        if normalized in replacements:
            words.append(replacements[normalized])
        elif normalized.isdigit():
            words.append(normalized)
        else:
            words.append(normalized.capitalize())

    title = " ".join(words)
    title = re.sub(r"\bG\s+(\d+)\b", r"G+\1", title)
    title = title.replace(" & ", " & ")
    return clean_email_text(title)


def bayt_title_from_url(url):
    match = BAYT_JOB_PATH_PATTERN.search(urlparse(url or "").path or "")
    if not match:
        return ""

    return humanize_bayt_slug(match.group("slug"))


def comparable_tokens(value):
    return [
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if token not in {"and", "amp"}
    ]


def strip_bayt_title_prefix(anchor_text, job_title):
    anchor_text = clean_email_text(anchor_text)
    title_tokens = comparable_tokens(job_title)
    anchor_matches = list(re.finditer(r"[A-Za-z0-9]+", anchor_text))

    if not title_tokens or len(anchor_matches) < len(title_tokens):
        return anchor_text

    anchor_tokens = [
        token
        for token in (match.group(0).lower() for match in anchor_matches)
        if token not in {"and", "amp"}
    ]
    if anchor_tokens[: len(title_tokens)] != title_tokens:
        return anchor_text

    end_index = anchor_matches[len(title_tokens) - 1].end()
    return clean_email_text(anchor_text[end_index:])


def bayt_country_from_parts(parts):
    for part in parts:
        match = BAYT_COUNTRY_PATTERN.search(remove_noise(part))
        if match:
            country = match.group(1)
            return "UAE" if country.lower() == "united arab emirates" else country
    return ""


def split_bayt_company_location(remainder):
    parts = [
        remove_noise(part)
        for part in normalize_bullets(remainder).split("â€¢")
        if remove_noise(part)
    ]
    if not parts:
        return "", ""

    first_part = parts[0]
    country = bayt_country_from_parts(parts[1:])
    location = extract_location_from_text(first_part)
    company = first_part

    if location and first_part.lower().endswith(location.lower()):
        company = clean_email_text(first_part[: -len(location)])

    if country and location and country.lower() not in location.lower():
        location = f"{location}, {country}"
    elif country and not location:
        location = country

    return company, location


def parse_bayt_metadata(anchor_texts, card_text, subject, url):
    job_title = bayt_title_from_url(url) or first_role_text(anchor_texts)
    anchor_text = first_role_text(anchor_texts) or card_text
    remainder = strip_bayt_title_prefix(anchor_text, job_title)
    company, location = split_bayt_company_location(remainder)

    if not location:
        location = extract_location_from_text(card_text, subject)

    return clean_metadata(job_title, company, location)


def first_role_text(anchor_texts):
    candidates = [
        clean_email_text(text)
        for text in anchor_texts
        if text and not is_action_link_text(text)
    ]
    if not candidates:
        return ""

    return min(candidates, key=len)


def clean_metadata(role, company, location):
    role = remove_noise(role)
    company = remove_noise(company)
    location = remove_noise(location)

    if company and role and company.lower() == role.lower():
        company = ""
    if location and role and location.lower() == role.lower():
        location = ""

    return {
        "job_title": role,
        "company": company,
        "location": location,
    }


def parse_candidate_metadata(portal, anchor_texts, card_text, subject, url=""):
    if portal == "indeed":
        return parse_indeed_metadata(anchor_texts, card_text, subject)
    if portal == "glassdoor":
        return parse_glassdoor_metadata(anchor_texts, card_text, subject)
    if portal == "ziprecruiter":
        return parse_ziprecruiter_metadata(anchor_texts, card_text, subject)
    if portal == "bayt":
        return parse_bayt_metadata(anchor_texts, card_text, subject, url)

    return clean_metadata(first_role_text(anchor_texts), "", extract_location_from_text(card_text, subject))


def generic_job_title_from_lines(lines, anchor_text):
    anchor_text = clean_email_text(anchor_text)
    if anchor_text and anchor_text.lower() not in GENERIC_ACTION_TEXTS:
        return anchor_text

    for line in lines:
        lowered = line.lower()
        if lowered in GENERIC_ACTION_TEXTS:
            continue
        if any(noise in lowered for noise in ["unsubscribe", "privacy"]):
            continue
        if any(term in lowered for term in GENERIC_JOB_TERMS):
            return line

    return ""


def parse_generic_email_metadata(anchor_text, nearby_text, subject):
    lines = clean_email_lines(nearby_text)
    role = generic_job_title_from_lines(lines, anchor_text)
    location = extract_location_from_text(nearby_text, subject)
    company = ""

    if role:
        role_index = next(
            (index for index, line in enumerate(lines) if line.lower() == role.lower()),
            -1,
        )
        if role_index >= 0:
            for line in lines[role_index + 1:]:
                cleaned = remove_noise(line)
                lowered = cleaned.lower()
                if not cleaned or lowered in GENERIC_ACTION_TEXTS:
                    continue
                if location and lowered == location.lower():
                    continue
                if any(term in lowered for term in ["posted", "ago", "apply"]):
                    continue
                company = cleaned
                break

    return clean_metadata(role, company, location)


def classify_email_link(url, anchor_text="", nearby_text="", portal=None):
    normalized = normalize_url(url)
    portal = portal or portal_from_url(normalized)
    combined = f"{normalized} {anchor_text or ''} {nearby_text or ''}".lower()

    for reason, patterns in GENERIC_REJECT_PATTERNS.items():
        if any(pattern in combined for pattern in patterns):
            return {
                "accepted": False,
                "reason": reason,
                "url": normalized,
                "portal": portal,
            }

    if portal == "iimjobs" and not is_real_job_link(normalized):
        return {
            "accepted": False,
            "reason": "iimjobs_non_canonical_job_link",
            "url": normalized,
            "portal": portal,
        }

    looks_job_related = any(term in combined for term in GENERIC_JOB_TERMS)
    if portal != "unknown" and (is_real_job_link(normalized) or looks_job_related):
        return {
            "accepted": True,
            "reason": "job_related_configured_portal",
            "url": normalized,
            "portal": portal,
        }

    return {
        "accepted": False,
        "reason": "unknown_or_not_job_related",
        "url": normalized,
        "portal": portal,
    }


def build_generic_email_candidates(body, sender="", subject="", date=""):
    soup = BeautifulSoup(body or "", "html.parser")
    by_url = {}
    rejected_links = []
    unknown_links = []
    total_links_found = 0

    for tag in soup.find_all("a", href=True):
        raw_url = str(tag.get("href") or "").strip()
        if not raw_url.startswith("http"):
            continue

        total_links_found += 1
        normalized = normalize_url(raw_url)
        portal = portal_from_url(normalized)
        anchor_text = clean_email_text(tag.get_text(" ", strip=True))
        nearby_text = find_nearby_visible_text(tag)
        classification = classify_email_link(
            normalized,
            anchor_text=anchor_text,
            nearby_text=nearby_text,
            portal=portal,
        )

        if not classification["accepted"]:
            entry = {
                "url": normalized,
                "reason": classification["reason"],
                "anchor_text": anchor_text,
                "portal": portal,
            }
            if portal == "unknown":
                unknown_links.append(entry)
            else:
                rejected_links.append(entry)
            continue

        metadata = parse_generic_email_metadata(anchor_text, nearby_text, subject)
        if not (metadata.get("job_title") or is_real_job_link(normalized)):
            rejected_links.append(
                {
                    "url": normalized,
                    "reason": "insufficient_job_metadata",
                    "anchor_text": anchor_text,
                    "portal": portal,
                }
            )
            continue

        existing = by_url.setdefault(
            normalized,
            {
                "url": normalized,
                "portal": portal,
                "email_sender": sender,
                "email_subject": subject,
                "email_date": date,
                "anchor_text": anchor_text,
                "email_card_text": clean_email_text(nearby_text),
                "job_title": "",
                "company": "",
                "location": "",
                "metadata_source": "generic_email_fallback",
            },
        )
        if len(nearby_text) > len(existing.get("email_card_text", "")):
            existing["anchor_text"] = anchor_text
            existing["email_card_text"] = clean_email_text(nearby_text)
            existing.update(metadata)
        elif not existing.get("job_title"):
            existing.update(metadata)

    candidates = [
        candidate
        for candidate in by_url.values()
        if should_keep_candidate(candidate)
    ]
    diagnostics = {
        "total_links_found": total_links_found,
        "accepted_count": len(candidates),
        "rejected_links": rejected_links,
        "unknown_links": unknown_links,
        "visible_text_sample": clean_email_text(soup.get_text(" ", strip=True))[:1000],
    }
    return candidates, diagnostics


def safe_diagnostic_filename(subject):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", (subject or "job-alert").lower()).strip("-")
    return f"{stamp}-{slug[:60] or 'job-alert'}.json"


def write_parser_failure_diagnostic(sender, subject, date, diagnostics):
    try:
        folder = DATA_DIR / "parser_failures"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / safe_diagnostic_filename(subject)
        payload = {
            "sender": sender,
            "subject": subject,
            "date": date,
            "total_links_found": diagnostics.get("total_links_found", 0),
            "accepted_count": diagnostics.get("accepted_count", 0),
            "rejected_links": diagnostics.get("rejected_links", []),
            "unknown_links": diagnostics.get("unknown_links", []),
            "visible_text_sample": diagnostics.get("visible_text_sample", ""),
        }
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, sort_keys=True)
        print(f"Parser failure diagnostic written: {path}")
    except Exception as exc:
        print(f"Parser failure diagnostic write skipped: {exc}")


def has_minimum_email_metadata(candidate):
    return bool(
        candidate.get("job_title")
        and (candidate.get("company") or candidate.get("location"))
    )


def is_configured_portal_candidate(candidate):
    return (
        candidate.get("portal") != "unknown"
        and is_real_job_link(candidate.get("url", ""))
    )


def should_keep_candidate(candidate):
    if candidate.get("portal") == "iimjobs" and not is_real_job_link(candidate.get("url", "")):
        return False

    return (
        candidate.get("portal") == "linkedin"
        or has_minimum_email_metadata(candidate)
        or is_configured_portal_candidate(candidate)
    )


def extract_job_candidates_from_html(html, sender="", subject="", date=""):
    soup = BeautifulSoup(html or "", "html.parser")
    by_url = {}

    for tag in soup.find_all("a", href=True):
        raw_url = str(tag.get("href") or "").strip()
        if not raw_url.startswith("http"):
            continue

        url = normalize_url(raw_url)
        if not is_real_job_link(url):
            continue

        portal = portal_from_url(url)
        anchor_text = clean_email_text(tag.get_text(" ", strip=True))
        card_text = find_job_card_text(tag)

        existing = by_url.setdefault(
            url,
            {
                "url": url,
                "portal": portal,
                "email_sender": sender,
                "email_subject": subject,
                "email_date": date,
                "anchor_texts": [],
                "email_card_text": "",
                "job_title": "",
                "company": "",
                "location": "",
                "metadata_source": "email_card",
            },
        )

        if anchor_text and anchor_text not in existing["anchor_texts"]:
            existing["anchor_texts"].append(anchor_text)

        if len(card_text) > len(existing.get("email_card_text", "")):
            existing["email_card_text"] = card_text

    candidates = []
    for candidate in by_url.values():
        metadata = parse_candidate_metadata(
            candidate["portal"],
            candidate["anchor_texts"],
            candidate.get("email_card_text", ""),
            subject,
            candidate.get("url", ""),
        )
        candidate.update(metadata)
        candidate["anchor_text"] = " | ".join(candidate.pop("anchor_texts", []))
        candidates.append(candidate)

    return candidates


def print_zero_candidate_link_diagnostics(body):
    hrefs = extract_href_links_from_html(body)
    known_portal_links = []
    valid_job_links = []

    for href in hrefs:
        normalized = normalize_url(href)
        if portal_from_url(normalized) != "unknown":
            known_portal_links.append(normalized)
        if is_real_job_link(normalized):
            valid_job_links.append(normalized)

    print(
        "Link diagnostics: "
        f"hrefs={len(hrefs)}, "
        f"known_portal_hrefs={len(set(known_portal_links))}, "
        f"valid_job_hrefs={len(set(valid_job_links))}"
    )

    samples = sorted(set(known_portal_links))[:5]
    if samples:
        print("Sample known portal links:")
        for sample in samples:
            print(f"  {sample}")

def get_email_body(payload):
    body_parts = []

    def extract_parts(parts):
        for part in parts:
            mime_type = part.get("mimeType", "")

            data = part.get("body", {}).get("data")

            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

                    if mime_type in ["text/plain", "text/html"]:
                        body_parts.append(decoded)

                except Exception:
                    pass

            if part.get("parts"):
                extract_parts(part["parts"])

    if payload.get("parts"):
        extract_parts(payload["parts"])
    else:
        data = payload.get("body", {}).get("data")

        if data:
            try:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                body_parts.append(decoded)
            except Exception:
                pass

    return "\n".join(body_parts)


def gmail_job_alert_query():
    subject_terms = [
        "subject:(job alert)",
        "subject:(recommended jobs)",
        "subject:(new jobs)",
        "subject:(new job match)",
        "subject:(jobs for you)",
        "subject:(career opportunity)",
    ]
    sender_terms = [
        f"from:({sender})"
        for sender in configured_sender_patterns()
    ]
    return f"({' OR '.join([*subject_terms, *sender_terms])}) newer_than:10d"


def candidate_from_url(url, sender="", subject="", date=""):
    url = normalize_url(url)
    return {
        "url": url,
        "portal": portal_from_url(url),
        "email_sender": sender,
        "email_subject": subject,
        "email_date": date,
        "anchor_text": "",
        "email_card_text": "",
        "job_title": "",
        "company": "",
        "location": "",
        "metadata_source": "url_only",
    }


def get_recent_job_alert_candidates(max_results=10):
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q=gmail_job_alert_query(),
        maxResults=MAX_GMAIL_RESULTS_TO_INSPECT,
    ).execute()

    messages = results.get("messages", [])

    print(f"Emails found for inspection: {len(messages)}")
    print(f"Valid job alert email target: {max_results}")

    all_candidates = {}
    valid_job_alert_emails = 0

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")

        body = get_email_body(msg_data["payload"])
        # Debug logging disabled

        if not is_job_alert_email(sender, subject, body):
            print("\n--------------------")
            print("Skipped: Not a real job alert email")
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print(f"Date: {date}")
            continue

        valid_job_alert_emails += 1
        
        candidates = extract_job_candidates_from_html(
            body,
            sender=sender,
            subject=subject,
            date=date,
        )

        candidate_urls = {candidate["url"] for candidate in candidates}
        for text_link in extract_urls_from_text(body):
            normalized = normalize_url(text_link)
            if normalized in candidate_urls:
                continue
            if is_real_job_link(normalized):
                candidates.append(candidate_from_url(normalized, sender, subject, date))
                candidate_urls.add(normalized)

        candidates = [
            candidate
            for candidate in candidates
            if should_keep_candidate(candidate)
        ]
        fallback_diagnostics = None
        if not candidates:
            candidates, fallback_diagnostics = build_generic_email_candidates(
                body,
                sender=sender,
                subject=subject,
                date=date,
            )
        
        print("\n--------------------")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Date: {date}")
        print(f"Job candidates found: {len(candidates)}")
        if not candidates:
            print_zero_candidate_link_diagnostics(body)
            if fallback_diagnostics is not None:
                write_parser_failure_diagnostic(
                    sender,
                    subject,
                    date,
                    fallback_diagnostics,
                )

        for candidate in candidates:
            url = candidate["url"]
            existing = all_candidates.get(url)
            if (
                not existing
                or len(candidate.get("email_card_text", ""))
                > len(existing.get("email_card_text", ""))
            ):
                all_candidates[url] = candidate

            title = candidate.get("job_title") or "Not Available"
            company = candidate.get("company") or "Not Available"
            location = candidate.get("location") or "Not Mentioned"
            print(f"- {url}")
            print(f"  {title} | {company} | {location}")

        if valid_job_alert_emails >= max_results:
            break

    unique_candidates = [
        all_candidates[url]
        for url in sorted(all_candidates)
    ]

    print("\n====================")
    print(f"Valid job alert emails processed: {valid_job_alert_emails}")
    print(f"Total unique job candidates found: {len(unique_candidates)}")

    return unique_candidates


def get_recent_job_alerts(max_results=10):
    return [
        candidate["url"]
        for candidate in get_recent_job_alert_candidates(max_results=max_results)
    ]

EXCLUDED_JOB_ALERT_SENDERS = {
    "messages-noreply@linkedin.com",
    "updates-noreply@linkedin.com",
}

EXTRA_TRUSTED_JOB_SENDER_PATTERNS = [
    # Global job boards
    "linkedin.com",
    "jobalerts-noreply@linkedin.com",
    "jobs-listings@linkedin.com",
    "jobs-noreply@linkedin.com",
    "donotreply@jobalert.indeed.com",
    "indeed.com",
    "jobalert.indeed.com",
    "noreply@glassdoor.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "alerts@ziprecruiter.com",
    "monster.com",
    "careerbuilder.com",

    # ATS / company career platforms
    "workday",
    "myworkdayjobs",
    "greenhouse",
    "greenhouse.io",
    "lever",
    "lever.co",
    "smartrecruiters",
    "ashby",
    "ashbyhq",
    "icims",
    "taleo",
    "oraclecloud",
    "successfactors",
    "sapsf",
    "workable",
    "jobvite",

    # GCC / MENA
    "bayt.com",
    "gulftalent.com",
    "naukrigulf.com",
    "founditgulf.com",
    "monstergulf.com",
    "laimoon.com",
    "mihnati.com",

    # India / South Asia
    "naukri.com",
    "foundit.in",
    "timesjobs.com",
    "shine.com",
    "iimjobs.com",
    "instahyre.com",

    # Europe / Germany
    "stepstone",
    "xing.com",
    "eures.europa.eu",
    "arbeitsagentur.de",
    "arbeitnow.com",

    # Remote / startup / tech
    "wellfound.com",
    "remoteok.com",
    "weworkremotely.com",
    "flexjobs.com",
    "otta.com",
    "dice.com",
    "builtin.com",
    "ai-jobs.net",
]


def configured_sender_patterns():
    patterns = []

    for config in PORTALS.values():
        patterns.extend(config.get("email_senders", []))
        patterns.extend(config.get("domains", []))

    return sorted(set(pattern for pattern in patterns if pattern))


def is_trusted_job_sender(sender):
    sender_lower = (sender or "").lower()
    trusted_patterns = [
        *EXTRA_TRUSTED_JOB_SENDER_PATTERNS,
        *configured_sender_patterns(),
    ]
    return any(pattern in sender_lower for pattern in trusted_patterns)

def has_job_opening_subject(subject):
    subject_lower = (subject or "").lower().strip()
    opening_patterns = [
        r"^.+\bopening at\b.+$",
        r"^.+\bjob opening at\b.+$",
    ]
    return any(
        re.search(pattern, subject_lower, flags=re.IGNORECASE)
        for pattern in opening_patterns
    )

def is_job_alert_email(sender, subject, body):
    sender = sender or ""
    subject = subject or ""
    body = body or ""

    sender_lower = sender.lower()
    subject_lower = subject.lower()
    combined = f"{sender_lower} {subject_lower} {body[:1000].lower()}"

    if any(excluded in sender_lower for excluded in EXCLUDED_JOB_ALERT_SENDERS):
        return False

    trusted_sender = is_trusted_job_sender(sender)
    job_opening_subject = has_job_opening_subject(subject)

    if trusted_sender and job_opening_subject:
        return True

    positive_signals = [
        "job alert",
        "jobs matching",
        "job match",
        "new job match",
        "recommended jobs",
        "new jobs",
        "jobs for you",
        "apply now",
        "view job",
        "job opening",
        "vacancy",
        "hiring",
        "position",
        "job alerts",
        "job listings",
        "job ads",
        "saved job",
        "saved jobs",
        "View Details",
        "some jobs",
        "today's jobs",
        "job ads",
        "jobs applied",
        "viewed jobs",
    ]

    negative_signals = [
        "employers are skipping your cv",
        "update your cv",
        "cv freshness",
        "complete your profile",
        "profile views",
        "who viewed your profile",
        "blog",
        "salary survey",
        "career advice",
        "newsletter",
        "noticed you",
    ]

    if any(signal in combined for signal in negative_signals):
        return False

    if any(signal in subject_lower for signal in positive_signals):
        return True

    if trusted_sender and any(signal in combined for signal in positive_signals):
        return True
    
    return False
if __name__ == "__main__":
    get_recent_job_alerts()

