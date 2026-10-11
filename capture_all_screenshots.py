import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path(r"c:\Hackathons\APEX 2026\screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def capture():
    print(">>> Starting Playwright screenshot capture in 1920x1080...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page = context.new_page()

        # Step 1: Open app
        page.goto("http://127.0.0.1:8000")
        page.wait_for_timeout(3000)

        # Screen 1: Mapping
        print("Capturing Screen 1: Upload & Mapping...")
        page.locator("button:has-text('LOAD DEMO FILE')").click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(SCREENSHOT_DIR / "01_mapping.png"))

        # Screen 2: Rule Panel
        print("Capturing Screen 2: Rule Panel...")
        page.locator("button:has-text('2. Rule Panel')").click()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOT_DIR / "02_rules.png"))

        # Screen 3: Allocation Grid
        print("Capturing Screen 3: Allocation Dashboard...")
        page.locator("button:has-text('3. Allocation Grid')").click()
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SCREENSHOT_DIR / "03_allocation.png"))

        # Screen 4: Checker Report (Clean)
        print("Capturing Screen 4: Checker Report...")
        page.locator("button:has-text('4. Checker Report')").click()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOT_DIR / "04_checker.png"))

        # Screen 5: Technical Queries (TQs)
        print("Capturing Screen 5: TQ List...")
        page.locator("button:has-text('5. Technical Queries (TQs)')").click()
        page.wait_for_timeout(1500)
        page.locator("button:has-text('LOAD ADVERSARIAL CONFLICT FILE')").click()
        page.wait_for_timeout(3500)
        # Click first expandable row
        tq_rows = page.locator("div.cursor-pointer")
        if tq_rows.count() > 0:
            tq_rows.first.click()
            page.wait_for_timeout(1000)
        page.screenshot(path=str(SCREENSHOT_DIR / "05_tqs.png"))

        # Reset back to clean demo data
        page.locator("button:has-text('DEMO MODE (1,000 SIGNALS)')").click()
        page.wait_for_timeout(4000)

        # Screen 6: Revision Diff (Rev B)
        print("Capturing Screen 6: Revision Diff...")
        page.locator("button:has-text('6. Revision Diff (Rev B)')").click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(SCREENSHOT_DIR / "06_revision.png"))

        # Screen 7: Benchmark Suite
        print("Capturing Screen 7: Benchmarks...")
        page.locator("button:has-text('7. Benchmarks')").click()
        page.wait_for_timeout(2000)
        page.locator("button:has-text('RUN BENCHMARK')").click()
        page.wait_for_timeout(4000)
        page.screenshot(path=str(SCREENSHOT_DIR / "07_benchmark.png"))

        # Screen 8: Export
        print("Capturing Screen 8: Export Workbook...")
        page.locator("button:has-text('8. Export Workbook')").click()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOT_DIR / "08_export.png"))

        browser.close()
        print(">>> ALL 8 SCREENSHOTS CAPTURED PERFECTLY IN 1920x1080!")

if __name__ == "__main__":
    capture()
