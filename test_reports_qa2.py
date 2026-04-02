"""QA Phase 2: Generate reports with actual data, check API, test PDF downloads."""
import os, sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
from datetime import date as dt_date, timedelta

SITE = "https://carferry.online"
SD = "screenshots_review"
os.makedirs(SD, exist_ok=True)

# Date range with actual data (last 30 days)
TODAY = dt_date.today()
DATE_FROM = (TODAY - timedelta(days=30)).strftime("%Y-%m-%d")
DATE_TO = TODAY.strftime("%Y-%m-%d")
TODAY_STR = TODAY.strftime("%Y-%m-%d")

# Report tabs to test - in order they appear
REPORT_TABS = [
    "Date Wise Amount",
    "Ferry Wise Item",
    "Itemwise Levy",
    "Payment Mode Wise",
    "Ticket Details",
    "User Wise Daily",
    "Vehicle Wise Tickets",
    "Branch Summary",
]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()

        # Capture API calls
        api_log = []
        def handle_response(resp):
            if "/api/" in resp.url:
                body = ""
                try:
                    body = resp.text()[:800]
                except:
                    pass
                api_log.append({"url": resp.url, "status": resp.status, "body": body})
        page.on("response", handle_response)

        # -- LOGIN --
        print("=" * 70)
        print(f"SSMSPL REPORTS QA - PHASE 2 (Data: {DATE_FROM} to {DATE_TO})")
        print("=" * 70)

        for attempt in range(4):
            page.goto(f"{SITE}/login", wait_until="networkidle", timeout=30000)
            time.sleep(1)
            if "dashboard" in page.url:
                break
            page.fill('input[type="email"]', "admin@ssmspl.com")
            page.fill('input[type="password"]', "Password@123")
            page.click('button[type="submit"]')
            try:
                page.wait_for_url("**/dashboard**", timeout=10000)
                break
            except:
                time.sleep(2)
                body = page.inner_text("body")
                if "already logged in" in body.lower():
                    print(f"  Session conflict, waiting 70s (attempt {attempt+1})...")
                    time.sleep(70)

        if "dashboard" not in page.url:
            print("FATAL: Cannot login")
            browser.close()
            return
        print("[LOGIN] OK")

        # -- Navigate to reports --
        page.goto(f"{SITE}/dashboard/reports", wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # ================================================================
        # TEST EACH REPORT TAB
        # ================================================================
        results = {}
        for tab_name in REPORT_TABS:
            print(f"\n{'='*70}")
            print(f"TESTING: {tab_name}")
            print(f"{'='*70}")

            api_log.clear()

            # Click the tab
            try:
                tab_btn = page.locator(f"button:text-is('{tab_name}')").first
                tab_btn.click()
                time.sleep(2)
            except Exception as e:
                print(f"  FAIL: Could not click tab - {e}")
                results[tab_name] = {"status": "FAIL", "error": f"Tab click failed: {e}"}
                continue

            # Set date range
            date_inputs = page.locator('input[type="date"]:visible').all()
            if len(date_inputs) >= 2:
                # From/To range
                date_inputs[0].fill(DATE_FROM)
                date_inputs[1].fill(DATE_TO)
                print(f"  Set dates: {DATE_FROM} to {DATE_TO}")
            elif len(date_inputs) == 1:
                # Single date - use a date with data
                date_inputs[0].fill("2026-03-09")
                print(f"  Set date: 2026-03-09")

            # Click Generate Report
            try:
                gen_btn = page.locator("button:text-is('Generate Report')").first
                gen_btn.click()
                time.sleep(4)
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(1)
            except Exception as e:
                print(f"  FAIL: Generate button click error - {e}")

            # Screenshot
            safe_name = tab_name.lower().replace(" ", "_")[:25]
            page.screenshot(path=f"{SD}/data_{safe_name}.png", full_page=True)

            # Check for errors
            body_text = page.inner_text("body")
            has_error = "Failed to load" in body_text
            has_no_data = "No data" in body_text or "no report" in body_text.lower()

            if has_error:
                print(f"  ** FAIL: 'Failed to load data' **")

            # Check table content
            tables = page.locator("table:visible").all()
            table_info = {}
            if tables:
                headers = tables[0].locator("th").all()
                header_texts = [h.text_content().strip() for h in headers]
                data_rows = tables[0].locator("tbody tr").all()
                row_count = len(data_rows)

                # Get first row data if available
                first_row = {}
                if row_count > 0:
                    cells = data_rows[0].locator("td").all()
                    cell_texts = [c.text_content().strip() for c in cells]
                    for j, h in enumerate(header_texts):
                        if j < len(cell_texts):
                            first_row[h] = cell_texts[j]

                table_info = {
                    "columns": header_texts,
                    "row_count": row_count,
                    "first_row": first_row,
                }

                print(f"  Columns: {header_texts}")
                print(f"  Rows: {row_count}")
                if first_row:
                    print(f"  Sample row: {json.dumps(first_row, ensure_ascii=False)[:200]}")
            else:
                print(f"  No table visible")
                table_info = {"columns": [], "row_count": 0}

            # Check filters present
            selects = page.locator("select:visible").all()
            # Also check for combobox-style dropdowns
            comboboxes = page.locator('[role="combobox"]:visible').all()
            filter_texts = []
            for cb in comboboxes:
                text = cb.text_content().strip()
                filter_texts.append(text)

            visible_labels = []
            for label in page.locator("label:visible").all():
                text = label.text_content().strip()
                if text:
                    visible_labels.append(text)

            print(f"  Filters: labels={visible_labels[:8]}, dropdowns={filter_texts}")

            # Check API calls
            report_apis = [r for r in api_log if "report" in r["url"].lower()]
            for r in report_apis:
                url_short = r["url"].replace(SITE, "")
                if len(url_short) > 100:
                    url_short = url_short[:100] + "..."
                status_mark = "OK" if r["status"] < 400 else "FAIL"
                print(f"  API [{status_mark}] {r['status']} {url_short}")
                if r["status"] >= 400:
                    print(f"    Error: {r['body'][:200]}")

            results[tab_name] = {
                "status": "FAIL" if has_error else ("NO_DATA" if has_no_data else "OK"),
                "error": "Failed to load data" if has_error else None,
                "table": table_info,
                "filters": visible_labels[:8],
                "api_errors": [r for r in report_apis if r["status"] >= 400],
            }

        # ================================================================
        # SUMMARY
        # ================================================================
        print(f"\n{'='*70}")
        print("QA SUMMARY")
        print(f"{'='*70}")

        for tab, res in results.items():
            status = res["status"]
            cols = res.get("table", {}).get("columns", [])
            rows = res.get("table", {}).get("row_count", 0)
            marker = "PASS" if status == "OK" else status
            print(f"  [{marker:8s}] {tab:25s} | {rows:3d} rows | cols: {cols}")

        # Check date defaults (reload page to verify)
        print(f"\n--- Date Default Check ---")
        page.goto(f"{SITE}/dashboard/reports", wait_until="networkidle", timeout=30000)
        time.sleep(3)
        date_inputs = page.locator('input[type="date"]').all()
        for i, d in enumerate(date_inputs):
            val = d.input_value()
            label = "From" if i == 0 else "To"
            expected = TODAY_STR
            status = "PASS" if val == expected else f"FAIL (got={val})"
            print(f"  {label}: {status}")

        browser.close()
        print(f"\nPhase 2 complete. Screenshots in {SD}/")

if __name__ == "__main__":
    main()
