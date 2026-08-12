from playwright.sync_api import sync_playwright

from paths import BROWSER_PROFILES_DIR


def login_to_ziprecruiter():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILES_DIR / "ziprecruiter"),
            headless=False
        )

        page = browser.new_page()
        page.goto("https://www.ziprecruiter.com/login", timeout=60000)

        print("Login to ZipRecruiter manually in the opened browser.")
        print("Complete any captcha, OTP, or verification if shown.")
        print("After login is complete, close the browser window or wait.")

        page.wait_for_timeout(180000)

        browser.close()


if __name__ == "__main__":
    login_to_ziprecruiter()
