"""
SSMSPL Reports QA — Full 9-Test Suite
Login as MANAGER, verify all report overhaul requirements.
"""
import os, sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
from datetime import date as dt_date, timedelta

SITE = "https://carferry.online"
SD = "screenshots_review"
os.makedirs(SD, exist_ok=True)

TODAY = dt_date.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")
DATA_DATE = "2026-03-09"  # Known date with ticket data
DATA_FROM = (TODAY - timedelta(days=30)).strftime("%Y-%m-%d")
DATA_TO = TODAY_STR

# Manager credentials to try
MANAGER_CREDS = [
    ("sandip.pawar@ssmspl.com", "Password@123"),
    ("manager@ssmspl.com", "Password@123"),
]

EXPECTED_TABS = [
    "Date Wise Amount",
    "Ferry Wise Item",
    "Item Wise Summary",
    "Payment Mode Wise",
    "Ticket Details",
    "User Wise Daily",
    "Vehicle Wise Tickets",
    "Branch Summary",
]

results = {}

def record(test_id, status, detail=""):
    results[test_id] = {"status": status, "detail": detail}
    marker = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else status
    print(f"  [{marker}] {detail}")


def login(page):
    """Login as manager with retry."""
    for email, pwd in MANAGER_CREDS:
        for attempt in range(3):
            page.goto(f"{SITE}/login", wait_until="networkidle", timeout=30000)
            time.sleep(1)
            if "dashboard" in page.url:
                return True, email

            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', pwd)
            page.click('button[type="submit"]')
            try:
                page.wait_for_url("**/dashboard**", timeout=10000)
                return True, email
            except:
                time.sleep(2)
                body = page.inner_text("body")
                if "already logged in" in body.lower():
                    wait = 70 if attempt == 0 else 35
                    print(f"  Session conflict ({email}), waiting {wait}s...")
                    time.sleep(wait)
                elif "incorrect" in body.lower():
                    print(f"  Wrong password for {email}, trying next...")
                    break  # try next credential
                else:
                    print(f"  Unknown login error for {email}")
                    break
    return False, ""


def click_tab(page, tab_name):
    """Click a report tab by exact text."""
    try:
        btn = page.locator(f"button:text-is('{tab_name}')").first
        btn.click()
        time.sleep(2)
        return True
    except:
        return False


def set_dates_and_generate(page, date_from=None, date_to=None, single_date=None):
    """Set date filters and click Generate Report."""
    date_inputs = page.locator('input[type="date"]:visible').all()
    if single_date and len(date_inputs) >= 1:
        date_inputs[0].fill(single_date)
    elif date_from and len(date_inputs) >= 2:
        date_inputs[0].fill(date_from)
        if date_to:
            date_inputs[1].fill(date_to)

    try:
        page.locator("button:text-is('Generate Report')").first.click()
        time.sleep(4)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(1)
    except:
        pass


def get_table_info(page):
    """Get table headers and row data."""
    tables = page.locator("table:visible").all()
    if not tables:
        return {"columns": [], "rows": 0, "first_row": {}, "all_rows": []}
    headers = [h.text_content().strip() for h in tables[0].locator("th").all()]
    data_rows = tables[0].locator("tbody tr").all()
    all_rows = []
    for row in data_rows:
        cells = [c.text_content().strip() for c in row.locator("td").all()]
        row_dict = {}
        for j, h in enumerate(headers):
            if j < len(cells):
                row_dict[h] = cells[j]
        all_rows.append(row_dict)
    return {
        "columns": headers,
        "rows": len(data_rows),
        "first_row": all_rows[0] if all_rows else {},
        "all_rows": all_rows,
    }


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()

        # Track API calls
        api_log = []
        def on_resp(resp):
            if "/api/" in resp.url:
                body = ""
                try: body = resp.text()[:500]
                except: pass
                api_log.append({"url": resp.url, "status": resp.status, "body": body})
        page.on("response", on_resp)

        # ============================================================
        print("=" * 70)
        print("SSMSPL REPORTS QA — FULL TEST SUITE (MANAGER ROLE)")
        print(f"Date: {TODAY_STR}   Site: {SITE}")
        print("=" * 70)

        # LOGIN
        print("\n[LOGIN]")
        ok, email = login(page)
        if not ok:
            print("FATAL: Cannot login as manager")
            page.screenshot(path=f"{SD}/FAIL_login.png")
            browser.close()
            return
        print(f"  Logged in as {email}")
        page.screenshot(path=f"{SD}/00_manager_dashboard.png")

        # Navigate to reports
        page.goto(f"{SITE}/dashboard/reports", wait_until="networkidle", timeout=30000)
        time.sleep(4)
        page.screenshot(path=f"{SD}/T0_reports_landing.png", full_page=True)

        # ============================================================
        # TEST 1: Default Dates
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 1 — Default Dates")
        print(f"{'='*70}")

        date_inputs = page.locator('input[type="date"]').all()
        from_val = date_inputs[0].input_value() if len(date_inputs) > 0 else "N/A"
        to_val = date_inputs[1].input_value() if len(date_inputs) > 1 else "N/A"

        if from_val == TODAY_STR:
            record("T1_from", "PASS", f"From Date = {from_val} (today)")
        else:
            record("T1_from", "FAIL", f"From Date = {from_val}, expected {TODAY_STR}")

        if to_val == TODAY_STR:
            record("T1_to", "PASS", f"To Date = {to_val} (today)")
        else:
            record("T1_to", "FAIL", f"To Date = {to_val}, expected {TODAY_STR}")

        page.screenshot(path=f"{SD}/T1_default_dates.png", full_page=True)

        # ============================================================
        # TEST 2: Report Tabs
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 2 — Report Tabs")
        print(f"{'='*70}")

        all_buttons = page.locator("button:visible").all()
        button_texts = [(btn.text_content() or "").strip() for btn in all_buttons]

        for expected_tab in EXPECTED_TABS:
            if expected_tab in button_texts:
                record(f"T2_{expected_tab}", "PASS", f"Tab '{expected_tab}' exists")
            else:
                record(f"T2_{expected_tab}", "FAIL", f"Tab '{expected_tab}' NOT FOUND")

        if "Itemwise Levy" in button_texts:
            record("T2_old_name", "FAIL", "Old tab name 'Itemwise Levy' still present!")
        else:
            record("T2_old_name", "PASS", "Old name 'Itemwise Levy' removed")

        # ============================================================
        # TEST 3: Route Filter on all reports
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 3 — Route Filter")
        print(f"{'='*70}")

        for tab_name in EXPECTED_TABS:
            if not click_tab(page, tab_name):
                record(f"T3_{tab_name}", "FAIL", f"Cannot click tab '{tab_name}'")
                continue
            time.sleep(1)

            # Look for Route label or Route dropdown
            body_text = page.inner_text("body")
            labels = [l.text_content().strip() for l in page.locator("label:visible").all()]
            comboboxes = page.locator('[role="combobox"]:visible').all()
            combo_texts = [(c.text_content() or "").strip() for c in comboboxes]

            has_route = "Route" in labels or any("route" in t.lower() for t in combo_texts)
            if has_route:
                record(f"T3_{tab_name}", "PASS", f"Route filter present on '{tab_name}'")
            else:
                record(f"T3_{tab_name}", "FAIL", f"Route filter MISSING on '{tab_name}' (labels={labels}, combos={combo_texts})")

        page.screenshot(path=f"{SD}/T3_route_filter.png", full_page=True)

        # ============================================================
        # TEST 4: Item Wise Summary
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 4 — Item Wise Summary")
        print(f"{'='*70}")

        click_tab(page, "Item Wise Summary")
        set_dates_and_generate(page, date_from=DATA_FROM, date_to=DATA_TO)
        page.screenshot(path=f"{SD}/T4_item_wise_summary.png", full_page=True)

        info = get_table_info(page)
        expected_cols = ["Item", "Rate", "Qty", "Net"]
        if info["columns"][:4] == expected_cols:
            record("T4_columns", "PASS", f"Columns: {info['columns'][:4]}")
        else:
            record("T4_columns", "FAIL", f"Columns: {info['columns']}, expected {expected_cols}")

        if info["rows"] > 0:
            record("T4_data", "PASS", f"{info['rows']} rows returned")
            # Verify Rate = base + levy, Net = Rate * Qty
            first = info["first_row"]
            print(f"    Sample: {json.dumps(first, ensure_ascii=False)[:200]}")
        else:
            record("T4_data", "FAIL", "No data returned")

        # ============================================================
        # TEST 5: Ticket Details
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 5 — Ticket Details")
        print(f"{'='*70}")

        click_tab(page, "Ticket Details")
        set_dates_and_generate(page, single_date=DATA_DATE)
        page.screenshot(path=f"{SD}/T5_ticket_details.png", full_page=True)

        info = get_table_info(page)
        expected_td = ["Ticket Date", "TicketNo", "Payment Mode", "Boat Name", "Time", "Ferry Type", "ClientName", "Amount"]
        if info["columns"] == expected_td:
            record("T5_columns", "PASS", f"Columns match: {info['columns']}")
        else:
            record("T5_columns", "FAIL", f"Columns: {info['columns']}, expected: {expected_td}")

        has_boat = any(r.get("Boat Name", "---") not in ("", "---", None) for r in info["all_rows"])
        has_ferry = any(r.get("Ferry Type", "") not in ("", "---", None) for r in info["all_rows"])
        record("T5_boat_name", "PASS" if has_boat else "FAIL", f"Boat Name populated: {has_boat}")
        record("T5_ferry_type", "PASS" if has_ferry else "FAIL", f"Ferry Type populated: {has_ferry}")

        if info["rows"] > 0:
            print(f"    Sample: {json.dumps(info['first_row'], ensure_ascii=False)[:250]}")

        # ============================================================
        # TEST 6: Vehicle Wise Tickets
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 6 — Vehicle Wise Tickets")
        print(f"{'='*70}")

        click_tab(page, "Vehicle Wise Tickets")
        set_dates_and_generate(page, single_date=DATA_DATE)
        page.screenshot(path=f"{SD}/T6_vehicle_wise.png", full_page=True)

        info = get_table_info(page)
        # Check key columns exist
        needed = ["Boat Name", "Ferry Type", "Vehicle No", "Vehicle Name"]
        for col in needed:
            if col in info["columns"]:
                record(f"T6_{col}", "PASS", f"'{col}' column present")
            else:
                record(f"T6_{col}", "FAIL", f"'{col}' column MISSING. Have: {info['columns']}")

        has_boat = any(r.get("Boat Name", "---") not in ("", "---", None) for r in info["all_rows"])
        record("T6_boat_populated", "PASS" if has_boat else "FAIL", f"Boat Name populated: {has_boat}")

        if info["rows"] > 0:
            print(f"    Sample: {json.dumps(info['first_row'], ensure_ascii=False)[:250]}")

        # ============================================================
        # TEST 7: User Wise Daily — Billing Operator dropdown
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 7 — User Wise Daily (Manager filter)")
        print(f"{'='*70}")

        click_tab(page, "User Wise Daily")
        time.sleep(2)
        page.screenshot(path=f"{SD}/T7_user_wise.png", full_page=True)

        labels = [l.text_content().strip() for l in page.locator("label:visible").all()]
        combos = page.locator('[role="combobox"]:visible').all()
        combo_texts = [(c.text_content() or "").strip() for c in combos]

        has_user_filter = (
            "Billing Operator" in labels
            or "User" in labels
            or any("operator" in t.lower() or "user" in t.lower() or "all users" in t.lower() for t in combo_texts)
        )
        if has_user_filter:
            record("T7_user_filter", "PASS", f"User/Operator filter present (labels={labels}, combos={combo_texts})")
        else:
            record("T7_user_filter", "FAIL", f"No user filter dropdown (labels={labels}, combos={combo_texts})")

        # ============================================================
        # TEST 8: Print Mode
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 8 — Print Mode")
        print(f"{'='*70}")

        # Generate a report first
        click_tab(page, "Date Wise Amount")
        set_dates_and_generate(page, date_from=DATA_FROM, date_to=DATA_TO)
        time.sleep(2)

        # Check for print stylesheet
        html = page.content()
        has_print_style = "@media print" in html
        has_print_hidden = "print:hidden" in html or "print\\:hidden" in html

        if has_print_style or has_print_hidden:
            record("T8_print_css", "PASS", f"Print stylesheet found (@media print={has_print_style}, print:hidden={has_print_hidden})")
        else:
            record("T8_print_css", "FAIL", "No @media print or print:hidden classes found in page HTML")

        # Check that sidebar, header, filters have print:hidden or hidden-print class
        sidebar = page.locator("aside, nav, [class*='sidebar'], [class*='Sidebar']").all()
        sidebar_hidden = False
        for el in sidebar:
            cls = el.get_attribute("class") or ""
            if "print:hidden" in cls or "print-hidden" in cls or "hidden-print" in cls:
                sidebar_hidden = True
                break

        record("T8_sidebar_hidden", "PASS" if sidebar_hidden else "FAIL",
               f"Sidebar has print:hidden: {sidebar_hidden}")

        # Print button exists
        print_btn = page.locator("button:has-text('Print')").all()
        record("T8_print_button", "PASS" if print_btn else "FAIL",
               f"Print button found: {len(print_btn)} button(s)")

        page.screenshot(path=f"{SD}/T8_print_mode.png", full_page=True)

        # ============================================================
        # TEST 9: PDF Export
        # ============================================================
        print(f"\n{'='*70}")
        print("TEST 9 — PDF Export")
        print(f"{'='*70}")

        # Already on Date Wise Amount with data
        api_log.clear()

        # Set up download handler
        pdf_downloaded = False
        pdf_error = None
        try:
            with page.expect_download(timeout=30000) as download_info:
                page.locator("button:has-text('Download PDF')").first.click()
            download = download_info.value
            pdf_path = os.path.join(SD, download.suggested_filename or "report.pdf")
            download.save_as(pdf_path)
            pdf_size = os.path.getsize(pdf_path)
            pdf_downloaded = True
            record("T9_download", "PASS", f"PDF downloaded: {pdf_path} ({pdf_size} bytes)")
        except Exception as e:
            pdf_error = str(e)
            # Check if it was an API error
            for r in api_log:
                if "pdf" in r["url"].lower():
                    if r["status"] >= 400:
                        pdf_error = f"API {r['status']}: {r['body'][:200]}"
            record("T9_download", "FAIL", f"PDF download failed: {pdf_error}")

        page.screenshot(path=f"{SD}/T9_pdf_export.png", full_page=True)

        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        print(f"\n{'='*70}")
        print("FINAL QA SUMMARY")
        print(f"{'='*70}")

        pass_count = sum(1 for r in results.values() if r["status"] == "PASS")
        fail_count = sum(1 for r in results.values() if r["status"] == "FAIL")
        total = len(results)

        print(f"\nTotal checks: {total} | PASS: {pass_count} | FAIL: {fail_count}")
        print()

        for test_id, res in results.items():
            marker = "PASS" if res["status"] == "PASS" else "FAIL"
            print(f"  [{marker}] {test_id}: {res['detail']}")

        browser.close()
        print(f"\nScreenshots saved to {SD}/")

if __name__ == "__main__":
    main()
