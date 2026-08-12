VALID_CAPTURE_STATUS = ["captured", "skipped", "duplicate"]
VALID_SCRAPE_STATUS = ["success", "failed", "partial", "login_required", "blocked"]
VALID_LOGIN_STATUS = ["not_required", "required", "profile_used", "failed"]
VALID_JD_QUALITY = ["full", "partial", "email_snippet_only", "unusable"]


def build_job_status(
    source="unknown",
    capture_status="captured",
    scrape_status="success",
    login_status="not_required",
    jd_quality="full",
    notes=""
):
    return {
        "source": source,
        "capture_status": capture_status,
        "scrape_status": scrape_status,
        "login_status": login_status,
        "jd_quality": jd_quality,
        "notes": notes
    }