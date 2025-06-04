# conftest.py

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope="session")
def driver():
    """
    Launch a headless Chrome on GitHub Actions (Ubuntu). We do NOT set
    --user-data-dir, because on a fresh runner Chrome will automatically
    create a throwaway profile under /tmp. Omitting it avoids “already in use” errors.
    """
    opts = Options()
    opts.headless = True
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")  # required on some CI containers
    opts.add_argument("--disable-extensions")

    # Install the matching chromedriver, then launch Chrome
    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    drv = webdriver.Chrome(service=service, options=opts)
    yield drv
    try:
        drv.quit()
    except:
        pass
