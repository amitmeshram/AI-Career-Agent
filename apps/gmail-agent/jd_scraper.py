from datetime import datetime
import json
import os
import re
import time
from pathlib import Path

from jd_cleaner import clean_job_text
from job_source_registry import detect_portal, get_browser_profile
from paths import BROWSER_PROFILES_DIR, CAREER_OPS_ROOT, SCRAPED_JOBS_FILE
from portal_config import PORTALS
from playwright.sync_api import sync_playwright


def ensure_linkedin_english(page, timeout_ms=5000):
    deadline = time.monotonic() + (timeout_ms / 1000)

    def remaining_timeout(default_ms=500):
        remaining_ms = int((deadline - time.monotonic()) * 1000)
        return max(100, min(default_ms, remaining_ms))

    def has_time():
        return time.monotonic() < deadline

    try:
        selectors = [
            (
                "xpath=//select[contains(translate(@aria-label, "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                "'language')]"
            ),
            (
                "xpath=//select[contains(translate(@name, "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                "'language')]"
            ),
            (
                "xpath=//select[contains(translate(@id, "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                "'language')]"
            ),
            "footer select",
        ]

        language_select = None

        for selector in selectors:
            if not has_time():
                print("LinkedIn language selection timed out; continuing.")
                return False

            locator = page.locator(selector)
            count = min(locator.count(), 5)

            for index in range(count):
                if not has_time():
                    print("LinkedIn language selection timed out; continuing.")
                    return False

                candidate = locator.nth(index)
                try:
                    if candidate.is_visible(timeout=remaining_timeout()):
                        language_select = candidate
                        break
                except Exception:
                    continue

            if language_select:
                break

        if not language_select:
            return False

        selected = language_select.evaluate(
            """
            select => {
                const option = select.options[select.selectedIndex];
                return {
                    value: select.value || "",
                    label: option ? (option.textContent || "").trim() : ""
                };
            }
            """
        )
        selected_label = (selected.get("label") or "").strip()
        selected_value = (selected.get("value") or "").strip()

        if (
            "english" in selected_label.lower()
            or selected_value.lower().startswith("en")
        ):
            print("LinkedIn language already English.")
            return True

        options = language_select.evaluate(
            """
            select => Array.from(select.options).map(option => ({
                value: option.value || "",
                label: (option.textContent || "").trim()
            }))
            """
        )
        english_options = [
            option
            for option in options
            if option.get("label") == "English (English)"
        ]
        if not english_options:
            english_options = [
                option
                for option in options
                if "english" in (option.get("label") or "").lower()
            ]

        if not english_options:
            print("LinkedIn language selection failed; English option not found.")
            return False

        selected_english = False
        try:
            language_select.select_option(
                label=english_options[0].get("label"),
                timeout=remaining_timeout(1500),
            )
            selected_english = True
        except Exception:
            option_value = english_options[0].get("value")
            if option_value and has_time():
                language_select.select_option(
                    value=option_value,
                    timeout=remaining_timeout(1500),
                )
                selected_english = True

        if not selected_english:
            print("LinkedIn language selection failed; continuing.")
            return False

        if has_time():
            try:
                page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=remaining_timeout(2500),
                )
            except Exception:
                pass

        if has_time():
            page.wait_for_timeout(remaining_timeout(1000))

        print("LinkedIn language changed to English.")
        return True

    except Exception:
        print("LinkedIn language selection failed; continuing.")
        return False


def scrape_job_description(url):
    portal = detect_portal(url)
    portal_config = PORTALS.get(portal, {})
    default_headless = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
    headless = portal_config.get("headless", default_headless)
    browser_channel = portal_config.get("browser_channel")
    profile_dir = get_browser_profile(portal)
    if profile_dir:
        profile_dir = Path(profile_dir)
        if not profile_dir.is_absolute():
            profile_dir = CAREER_OPS_ROOT / profile_dir
    else:
        profile_dir = BROWSER_PROFILES_DIR / portal
    print(f"Detected portal: {portal}")

    with sync_playwright() as p:
        browser_options = dict(
            user_data_dir=str(profile_dir),
            headless=headless,
        )
        if portal == "linkedin":
            browser_options["locale"] = "en-US"
            browser_options["extra_http_headers"] = {
                "Accept-Language": "en-US,en;q=0.9"
            }
        if browser_channel:
            browser_options["channel"] = browser_channel

        browser = p.chromium.launch_persistent_context(**browser_options)

        page = browser.new_page()

        try:
            page.goto(url, timeout=60000)
            page.wait_for_timeout(7000)
            if portal == "linkedin":
                ensure_linkedin_english(page)

            title = page.title()
            text = page.inner_text("body")

            parsed_title = parse_job_details(portal, url, title, text)
            parsed_title["location"] = translate_location_to_english(
                parsed_title.get("location", "")
            )

            browser.close()

            if is_blocked_or_login_page(portal, title, text):
                return {
                    "url": url,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "blocked",

                    "source_status": {
                        "source": portal,
                        "capture_status": "captured",
                        "scrape_status": "blocked",
                        "login_status": "failed",
                        "jd_quality": "unusable"
                    },

                    "job_title": parsed_title.get("job_title"),
                    "company": parsed_title.get("company"),
                    "location": parsed_title.get("location"),
                    "needs_manual_review": parsed_title.get("needs_manual_review"),
                    "page_title": title,
                    "content": "",
                    "message": "Page requires login, blocks automated access, or returned a security challenge."
                }

            cleaned_content = clean_job_text(text)[:4000]
            has_metadata = bool(
                parsed_title.get("job_title")
                and parsed_title.get("company")
            )
            has_usable_content = len(cleaned_content.strip()) >= 200

            if not has_metadata or not has_usable_content:
                return {
                    "url": url,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "status": "partial",
                    "source_status": {
                        "source": portal,
                        "capture_status": "captured",
                        "scrape_status": "partial",
                        "login_status": (
                            "profile_used"
                            if portal_config.get("requires_login")
                            else "not_required"
                        ),
                        "jd_quality": "partial"
                    },
                    "job_title": parsed_title.get("job_title"),
                    "company": parsed_title.get("company"),
                    "location": parsed_title.get("location"),
                    "needs_manual_review": True,
                    "page_title": title,
                    "content": cleaned_content,
                    "message": "Page loaded, but required metadata or usable job content is missing."
                }

            return {
                "url": url,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "status": "success",

                "source_status": {
                    "source": portal,
                    "capture_status": "captured",
                    "scrape_status": "success",
                    "login_status": (
                        "profile_used"
                        if portal_config.get("requires_login")
                        else "not_required"
                    ),
                    "jd_quality": "full"
                },

                "job_title": parsed_title.get("job_title"),
                "company": parsed_title.get("company"),
                "location": parsed_title.get("location"),
                "needs_manual_review": parsed_title.get("needs_manual_review"),
                "page_title": title,
                "content": cleaned_content,
                "message": "Job content extracted successfully."
            }

        except Exception as e:
            browser.close()
            return {
                "url": url,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "status": "error",
                "job_title": "",
                "company": "",
                "location": "",
                "needs_manual_review": True,
                "page_title": "",
                "content": "",
                "source_status": {
                    "source": portal,
                    "capture_status": "captured",
                    "scrape_status": "failed",
                    "login_status": "failed",
                    "jd_quality": "unusable"
                },
                "message": str(e)
            }


def is_blocked_or_login_page(portal, title, text):
    combined = f"{title} {text}".lower()

    blocked_signals = [
        "captcha",
        "verify you are human",
        "access denied",
        "just a moment",
        "humans only",
        "security challenge",
        "cloudflare",
        "ray id:",
        "blocked - indeed.com",
    ]

    if any(signal in combined for signal in blocked_signals):
        return True

    if portal == "linkedin":
        normalized_title = (title or "").strip().lower()
        login_titles = {
            "linkedin login",
            "linkedin login, sign in",
            "sign in | linkedin",
        }
        if normalized_title in login_titles:
            return True

        login_wall_signals = [
            "sign in to view this job",
            "join linkedin to view this job",
            "authwall",
        ]
        return any(signal in combined for signal in login_wall_signals)

    return False


def parse_job_details(portal, url, page_title, body_text):
    if portal == "linkedin":
        return parse_linkedin_details(page_title, body_text)

    if portal == "iimjobs":
        return parse_iimjobs_details(page_title, body_text)

    if portal == "foundit":
        return parse_foundit_details(page_title, body_text)

    if portal == "ziprecruiter":
        return parse_ziprecruiter_details(page_title, body_text)

    return parse_generic_details(page_title, body_text)


def parse_ziprecruiter_details(page_title, body_text):
    result = empty_job_details()
    title = (page_title or "").strip()
    match = re.match(
        (
            r"^(?P<job_title>.+?)\s+Job\s+at\s+"
            r"(?P<company>.+?)\s+in\s+"
            r"(?P<location>.+?)\s+\|\s+ZipRecruiter(?:\s+.+)?$"
        ),
        title,
        flags=re.IGNORECASE,
    )

    if match:
        result["job_title"] = match.group("job_title").strip()
        result["company"] = match.group("company").strip()
        result["location"] = match.group("location").strip()
    else:
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if not line.lower().startswith("posted "):
                continue
            if index + 3 >= len(lines):
                break
            result["job_title"] = lines[index + 1]
            result["company"] = lines[index + 2]
            result["location"] = re.sub(
                r"\s+(?:Full|Part)\s+Time.*$",
                "",
                lines[index + 3],
                flags=re.IGNORECASE,
            ).strip()
            break

    result["needs_manual_review"] = not (
        result["job_title"] and result["company"]
    )
    return result


def parse_foundit_details(page_title, body_text):
    result = empty_job_details()
    title = (page_title or "").strip()
    match = re.match(
        (
            r"^(?P<job_title>.+?)\s+-\s+.+?\s+with\s+"
            r"\d+\s*-\s*\d+\s+Years?\s+of\s+Experience\s+at\s+"
            r"(?P<company>.+?)\s+in\s+(?P<location>.+)$"
        ),
        title,
        flags=re.IGNORECASE,
    )

    if match:
        result["job_title"] = match.group("job_title").strip()
        result["company"] = match.group("company").strip()
        result["location"] = match.group("location").strip()
    else:
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if index + 2 >= len(lines):
                break
            if line.lower().startswith(("login", "register", "jobs", "services")):
                continue
            if re.fullmatch(r"\d+\s*-\s*\d+\s+Years?", lines[index + 3] if index + 3 < len(lines) else "", re.IGNORECASE):
                result["job_title"] = line
                result["company"] = lines[index + 1]
                result["location"] = lines[index + 2]
                break

    result["needs_manual_review"] = not (
        result["job_title"] and result["company"]
    )
    return result


def parse_iimjobs_details(page_title, body_text):
    result = empty_job_details()
    clean_title = re.sub(
        r"\s*\|\s*iimjobs\.com\s*$",
        "",
        page_title or "",
        flags=re.IGNORECASE
    )

    screening_match = re.match(
        (
            r"^Job Application Screening\s*\|\s*"
            r"(?P<company>.+?)\s+-\s+"
            r"(?P<job_title>.+?)"
            r"(?:\s+-\s+(?:IIT|IIM|ISB|XLRI|MDI|SPJIMR|MBA|CA|CPA|CFA|"
            r"Engineer|Engineering|Premium).*)?"
            r"\s*\|\s*\d+\s*$"
        ),
        clean_title,
        flags=re.IGNORECASE,
    )
    if screening_match:
        result["job_title"] = screening_match.group("job_title").strip()
        result["company"] = screening_match.group("company").strip()
        result["needs_manual_review"] = not (
            result["job_title"] and result["company"]
        )
        return result

    parts = [part.strip() for part in clean_title.split(" - ") if part.strip()]

    if len(parts) >= 3:
        result["job_title"] = " - ".join(parts[1:-1])
        result["company"] = parts[-1]

    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    if not result["company"] and result["job_title"] in lines:
        index = lines.index(result["job_title"])
        if index + 1 < len(lines):
            result["company"] = lines[index + 1]

    result["needs_manual_review"] = not (
        result["job_title"] and result["company"]
    )
    return result


def parse_generic_details(page_title, body_text):
    result = empty_job_details()
    title = (page_title or "").strip()

    for suffix in (" | Glassdoor", " | GulfTalent", " | NaukriGulf.com"):
        if title.lower().endswith(suffix.lower()):
            title = title[:-len(suffix)].strip()

    parts = [part.strip() for part in re.split(r"\s+[|\-]\s+", title) if part.strip()]
    if len(parts) >= 2:
        result["job_title"] = parts[0]
        result["company"] = parts[1]

    result["needs_manual_review"] = not (
        result["job_title"] and result["company"]
    )
    return result


def empty_job_details():
    return {
        "job_title": "",
        "company": "",
        "location": "",
        "needs_manual_review": True
    }


LINKEDIN_DETAIL_SEPARATORS = ("·", "Â·", "•", "∙", "⋅")
TEXT_CONTROL_CHARS = dict.fromkeys(
    map(ord, "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\ufeff"),
    None,
)
LINKEDIN_NON_LOCATION_VALUES = {
    "",
    "apply",
    "easy apply",
    "save",
    "follow",
    "message",
    "full-time",
    "full time",
    "part-time",
    "part time",
    "contract",
    "temporary",
    "internship",
    "volunteer",
    "on-site",
    "onsite",
    "hybrid",
    "not available",
    "not mentioned",
}
ARABIC_LOCATION_EXACT_TRANSLATIONS = {
    "\u0627\u0644\u0631\u064a\u0627\u0636 \u0627\u0644\u0631\u064a\u0627\u0636 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Riyadh, Riyadh, Saudi Arabia",
    "\u0627\u0644\u0631\u064a\u0627\u0636 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Riyadh, Saudi Arabia",
    "\u0627\u0644\u0634\u0631\u0642\u064a\u0629 \u0627\u0644\u062c\u0628\u064a\u0644 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Jubail, Eastern Province, Saudi Arabia",
    "\u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Saudi Arabia",
    "\u0645\u0643\u0629 \u0645\u0643\u0629 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Makkah, Makkah, Saudi Arabia",
    "\u0645\u0643\u0629 \u062c\u062f\u0629 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Jeddah, Makkah, Saudi Arabia",
    "\u0627\u0644\u0645\u062f\u064a\u0646\u0629 \u062d\u064a \u0627\u0644\u0631\u0632\u064a\u0642\u064a\u0629 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Al Raziqiyah, Madinah, Saudi Arabia",
    "\u0627\u0644\u0642\u0635\u064a\u0645 \u0631\u064a\u0627\u0636 \u0627\u0644\u0631\u0645\u0627\u062d \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Riyadh Al Rimah, Qassim, Saudi Arabia",
}
ARABIC_LOCATION_WORD_TRANSLATIONS = {
    "\u0627\u0644\u0631\u064a\u0627\u0636": "Riyadh",
    "\u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "Saudi Arabia",
    "\u0627\u0644\u0634\u0631\u0642\u064a\u0629": "Eastern Province",
    "\u0627\u0644\u062c\u0628\u064a\u0644": "Jubail",
    "\u0645\u0643\u0629": "Makkah",
    "\u062c\u062f\u0629": "Jeddah",
    "\u0627\u0644\u0645\u062f\u064a\u0646\u0629": "Madinah",
    "\u062d\u064a": "",
    "\u0627\u0644\u0631\u0632\u064a\u0642\u064a\u0629": "Al Raziqiyah",
    "\u0627\u0644\u0642\u0635\u064a\u0645": "Qassim",
    "\u0631\u064a\u0627\u0636": "Riyadh",
    "\u0627\u0644\u0631\u0645\u0627\u062d": "Al Rimah",
}


def normalize_linkedin_text(value):
    value = str(value or "").translate(TEXT_CONTROL_CHARS)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip("`'\" ")


def contains_arabic(value):
    return bool(re.search(r"[\u0600-\u06ff]", str(value or "")))


def translate_arabic_location_to_english(value):
    location = normalize_linkedin_text(value)
    if not contains_arabic(location):
        return location

    if location in ARABIC_LOCATION_EXACT_TRANSLATIONS:
        return ARABIC_LOCATION_EXACT_TRANSLATIONS[location]

    translated_parts = []
    for part in re.split(r"[\s,]+", location):
        translated = ARABIC_LOCATION_WORD_TRANSLATIONS.get(part, part)
        if translated:
            translated_parts.append(translated)

    deduped_parts = []
    for part in translated_parts:
        if not deduped_parts or deduped_parts[-1] != part:
            deduped_parts.append(part)

    if deduped_parts and all(not contains_arabic(part) for part in deduped_parts):
        return ", ".join(deduped_parts)

    return location


def translate_location_to_english(value):
    return translate_arabic_location_to_english(value)


def normalize_for_match(value):
    return normalize_linkedin_text(value).casefold()


def split_linkedin_detail_line(line):
    pattern = "|".join(re.escape(separator) for separator in LINKEDIN_DETAIL_SEPARATORS)
    return [
        normalize_linkedin_text(part)
        for part in re.split(pattern, line or "")
        if normalize_linkedin_text(part)
    ]


def is_probable_linkedin_location(value, job_title="", company=""):
    value = normalize_linkedin_text(value)
    normalized = value.casefold()

    if normalized in LINKEDIN_NON_LOCATION_VALUES:
        return False

    if len(value) < 2 or len(value) > 90:
        return False

    if normalized in {
        normalize_for_match(job_title),
        normalize_for_match(company),
        "linkedin",
    }:
        return False

    if re.search(r"https?://|www\.|@", value, flags=re.IGNORECASE):
        return False

    if re.fullmatch(r"[\d\s,.\-+()]+", value):
        return False

    if re.search(r"\b(apply|applicant|reposted|promoted|premium|linkedin)\b", normalized):
        return False

    return True


def extract_location_from_linkedin_title(parts, job_title="", company=""):
    for part in parts[2:]:
        candidate = normalize_linkedin_text(part)
        if is_probable_linkedin_location(candidate, job_title, company):
            return candidate
    return ""


def extract_location_from_linkedin_detail_line(line, job_title="", company=""):
    parts = split_linkedin_detail_line(line)
    if len(parts) < 2:
        return ""

    candidate = parts[0]
    if is_probable_linkedin_location(candidate, job_title, company):
        return candidate

    return ""


def find_linkedin_header_indexes(lines, job_title="", company=""):
    targets = {
        normalize_for_match(job_title),
        normalize_for_match(company),
    }
    targets.discard("")

    return [
        index
        for index, line in enumerate(lines)
        if normalize_for_match(line) in targets
    ]


def extract_location_from_linkedin_header(lines, job_title="", company=""):
    indexes = find_linkedin_header_indexes(lines, job_title, company)

    for index in indexes:
        for line in lines[index + 1:index + 8]:
            location = extract_location_from_linkedin_detail_line(
                line,
                job_title,
                company,
            )
            if location:
                return location

    for line in lines:
        location = extract_location_from_linkedin_detail_line(
            line,
            job_title,
            company,
        )
        if location:
            return location

    return ""


def extract_labeled_location_from_body(lines):
    for line in lines:
        match = re.match(
            r"^(?:job\s+location|work\s+location|location)\s*:\s*(.+)$",
            normalize_linkedin_text(line),
            flags=re.IGNORECASE,
        )
        if match:
            location = normalize_linkedin_text(match.group(1))
            if is_probable_linkedin_location(location):
                return location
    return ""


def parse_linkedin_details(page_title, body_text):
    result = empty_job_details()
    title_location = ""

    # 1. Extract job title and company from page title first
    # Example: Senior Manager Business Operations | Takamol Holding | LinkedIn
    if page_title and " | " in page_title and "LinkedIn" in page_title:
        clean_title = page_title.replace(" | LinkedIn", "").strip()

        login_titles = [
            "linkedin login",
            "sign in",
            "linkedin login, sign in"
        ]

        if any(item in clean_title.lower() for item in login_titles):
            result["needs_manual_review"] = True
            return result

        parts = clean_title.split(" | ")

        if len(parts) >= 2:
            result["job_title"] = parts[0].strip()
            result["company"] = parts[1].strip()
            title_location = extract_location_from_linkedin_title(
                parts,
                result["job_title"],
                result["company"],
            )

    # 2. Extract location from body text
    lines = [
        line.strip()
        for line in body_text.splitlines()
        if line.strip()
    ]

    for line in lines:
        line_lower = line.lower()

        if "·" in line and (
            "applicant" in line_lower
            or "ago" in line_lower
            or "clicked apply" in line_lower
            or "reposted" in line_lower
        ):
            result["location"] = line.split("·")[0].strip()
            break

    if not result["location"]:
        normalized_lines = [
            normalize_linkedin_text(line)
            for line in body_text.splitlines()
            if normalize_linkedin_text(line)
        ]
        result["location"] = (
            extract_location_from_linkedin_header(
                normalized_lines,
                result["job_title"],
                result["company"],
            )
            or title_location
            or extract_labeled_location_from_body(normalized_lines)
        )

    # 3. Mark manual review only if title/company are missing
    if not result["job_title"] or not result["company"]:
        result["needs_manual_review"] = True

    return result

def save_job_result(result):
    existing_jobs = []

    if SCRAPED_JOBS_FILE.exists():
        try:
            with open(SCRAPED_JOBS_FILE, "r", encoding="utf-8") as file:
                content = file.read().strip()

                if content:
                    existing_jobs = json.loads(content)

        except Exception:
            existing_jobs = []

    existing_index = next(
        (
            index
            for index, job in enumerate(existing_jobs)
            if job.get("url") == result.get("url")
        ),
        None
    )

    if existing_index is None:
        existing_jobs.append(result)
    else:
        existing_result = existing_jobs[existing_index]
        existing_is_usable = (
            existing_result.get("status") == "success"
            and bool((existing_result.get("job_title") or "").strip())
            and bool((existing_result.get("company") or "").strip())
            and len((existing_result.get("content") or "").strip()) >= 200
        )
        new_is_usable = (
            result.get("status") == "success"
            and bool((result.get("job_title") or "").strip())
            and bool((result.get("company") or "").strip())
            and len((result.get("content") or "").strip()) >= 200
        )

        if existing_is_usable and not new_is_usable:
            print("\nExisting successful job result retained.")
        else:
            existing_jobs[existing_index] = result
            print("\nExisting job result updated.")

    SCRAPED_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCRAPED_JOBS_FILE, "w", encoding="utf-8") as file:
        json.dump(existing_jobs, file, indent=4, ensure_ascii=False)

    #print("\nJob saved to scraped_jobs.json")


if __name__ == "__main__":
    test_url = input("Paste one job link here: ")
    result = scrape_job_description(test_url)

    save_job_result(result)

    print("\n====================")
    # print("STATUS:")
    # print(result["status"])

    # print("\nJOB TITLE:")
    # print(result.get("job_title", ""))

    # print("\nCOMPANY:")
    # print(result.get("company", ""))

    # print("\nLOCATION:")
    # print(result.get("location", ""))

    # print("\nNEEDS MANUAL REVIEW:")
    # print(result.get("needs_manual_review", ""))

    print("\nMESSAGE:")
    print(result["message"])

    print("\nCONTENT PREVIEW:")
    print(result.get("content", "")[:2000])
