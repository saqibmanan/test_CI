import os
import subprocess
import sys
import pytest
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# GLOBAL dict: nodeid → relative PNG path
FAILED_SCREENSHOTS = {}

@pytest.fixture(scope="session")
def driver():
    """
    Launch Chrome WebDriver (headless by default).
    """
    opts = Options()
    opts.headless = True
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    # install via webdriver_manager
    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    drv = webdriver.Chrome(service=service, options=opts)
    drv.implicitly_wait(3)
    yield drv
    drv.quit()

@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    After each test’s “call” phase, if it failed and there is a WebDriver fixture,
    save a PNG under ./screenshots/<sanitized nodeid>.png and record
    FAILED_SCREENSHOTS[nodeid] = <rel_path>.

    We do NOT rely on rep.user_properties here, because pytest‐json‐report runs
    its own hook *before* our post‐yield. Instead, we stash into FAILED_SCREENSHOTS
    and let pytest_json_modifyreport pick it up later.
    """
    outcome = yield
    rep = outcome.get_result()

    if rep.when == "call" and rep.failed:
        # 1) Find *any* WebDriver fixture injected into this test
        driver_obj = None
        for _, fixture_val in item.funcargs.items():
            if isinstance(fixture_val, WebDriver):
                driver_obj = fixture_val
                break

        if not driver_obj:
            # No WebDriver in test, nothing to screenshot
            return

        # 2) Create screenshots dir if needed
        screenshots_dir = Path(os.getcwd()) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        # 3) Sanitize nodeid to a valid filename
        sanitized = rep.nodeid.replace("::", "__").replace("/", "_").replace("\\", "_")
        png_path = screenshots_dir / f"{sanitized}.png"

        try:
            driver_obj.save_screenshot(str(png_path))
            rel = os.path.relpath(str(png_path), os.getcwd())

            # Record into global dict so we can inject into JSON later
            FAILED_SCREENSHOTS[rep.nodeid] = rel

            print(f"\n📸 [HOOK] Saved screenshot for {rep.nodeid}: {rel}\n")

        except Exception as e:
            print(f"\n⚠️ [HOOK] Could not save screenshot for {rep.nodeid}: {e}\n")


# ──────────────────────────────────────────────────────────────────────────────────
# 3) pytest_json_modifyreport: after pytest-json-report builds the JSON for each test,
#    inject our screenshot path into that test’s "user_properties"
# ──────────────────────────────────────────────────────────────────────────────────

@pytest.hookimpl
def pytest_json_modifyreport(json_report):
    """
    Called by pytest-json-report after it has created its internal JSON structure but
    before writing to report.json. Here we look up FAILED_SCREENSHOTS and, if a nodeid
    is present, append [ "screenshot", <path> ] under that test’s "user_properties".
    """
    for test_dict in json_report.get("tests", []):
        nodeid = test_dict.get("nodeid")
        if nodeid in FAILED_SCREENSHOTS:
            rel_path = FAILED_SCREENSHOTS[nodeid]
            # Ensure "user_properties" exists as a list
            if "user_properties" not in test_dict or test_dict["user_properties"] is None:
                test_dict["user_properties"] = []
            # Append our screenshot entry
            test_dict["user_properties"].append(["screenshot", rel_path])
            # (Optional) print to console for debugging
            print(f"🔗 [HOOK] Injected screenshot into JSON for {nodeid}: {rel_path}")


# ──────────────────────────────────────────────────────────────────────────────────
# 4) pytest_sessionfinish: after the JSON file is written, run report_generator.py
# ──────────────────────────────────────────────────────────────────────────────────

@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """
    At the very end of pytest, if `report.json` exists, automatically invoke report_generator.py
    to produce TEST_REPORT.md and TEST_REPORT.pdf.
    """
    rpt = Path(os.getcwd()) / "report.json"
    if rpt.exists():
        print("\n\n📄 Generating TEST_REPORT.md + TEST_REPORT.pdf …")
        subprocess.run([sys.executable, "report_generator.py"], check=False)
    else:
        print("\n\n⚠️  report.json not found; skipping report generation.")
