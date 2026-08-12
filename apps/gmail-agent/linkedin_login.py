from playwright.sync_api import sync_playwright

from paths import LINKEDIN_BROWSER_PROFILE_DIR


def login_to_linkedin():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(LINKEDIN_BROWSER_PROFILE_DIR),
            headless=False
        )

        page = browser.new_page()
        page.goto("https://www.linkedin.com/login")

        print("Login to LinkedIn manually in the opened browser.")
        print("After login is complete, close the browser window.")

        page.wait_for_timeout(120000)

        browser.close()


if __name__ == "__main__":
    login_to_linkedin()
