def clean_job_text(raw_text):
    if not raw_text:
        return ""

    text = raw_text

    if "About the job" in text:
        text = text.split("About the job", 1)[1]

    stop_sections = [
        "Set alert for similar jobs",
        "About the company",
        "More jobs",
        "Job search smarter with Premium",
        "Looking for talent?",
        "Select language",
        "LinkedIn Corporation",
    ]

    for section in stop_sections:
        if section in text:
            text = text.split(section, 1)[0]

    unwanted_lines = [
        "Show more",
        "Show all",
        "Easy Apply",
        "Apply",
        "Save",
        "Use AI to assess how you fit",
        "Tailor my resume",
        "Help me stand out",
        "People you can reach out to",
        "Retry Premium",
    ]

    cleaned_lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if any(bad.lower() in line.lower() for bad in unwanted_lines):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)