# conftest.py

import os
import tempfile
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope="session")
def driver():
    """
    Launch a headless Chrome on GitHub Actions (Ubuntu). We force Chrome to use
    a brand-new, empty user-data directory (in /tmp) on each session so that
    “user data directory already in use” errors never occur.
    """
    # 1) Build ChromeOptions
    opts = Options()

    # Use the new headless mode; on GH runners this avoids some legacy issues.
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")

    # 2) Create a fresh, empty directory for Chrome's user-data
    tmp_dir = tempfile.mkdtemp(prefix="chrome-user-data-")
    opts.add_argument(f"--user-data-dir={tmp_dir}")

    # 3) Install the matching chromedriver, then start Chrome
    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    drv = webdriver.Chrome(service=service, options=opts)

    yield drv

    # 4) Teardown: quit Chrome and remove the temp folder
    try:
        drv.quit()
    except Exception:
        pass

    # Clean up the temp profile directory
    try:
        # shutil.rmtree would remove it recursively
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass
