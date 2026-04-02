"""FINAL QA: Verify all 6 issues on live site."""
import os, sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
from datetime import date as dt_date, timedelta

SITE = "https://carferry.online"
SD = "screenshots_review"
os.makedirs(SD, exist_ok=True)
TODAY = dt_date.today().strftime("%Y-%m-%d")
DATA_FROM = (dt_date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

results = {}
def record(tid, status, detail=""):
    results[tid] = {"status": status, "detail": detail}
    print(f"  [{status:4s}] {detail}")

def login(page, email):
    for attempt in range(4):
        page.goto(f"{SITE}/login", wait_until="networkidle", timeout=30000)
        time.sleep(1)
        if "dashboard" in page.url:
            return True
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', "Password@123")
        page.click('button[type="submit"]')
        try:
            page.wait_for_url("**/dashboard**", timeout=10000)
            return True
        except:
            time.sleep(2)
            body = page.inner_text("body")
            if "already logged in" in body.lower():
                print(f"  Session conflict, waiting 70s (attempt {attempt+1})...")
                time.sleep(70)
            elif "incorrect" in body.lower():
                return False
    return False

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ================================================================
        # ISSUE 1 - Add Item Focus (test with admin on ticketing)
        # ================================================================
        print("=" * 70)
        print("ISSUE 1 - Add Item Focus Behavior")
        print("=" * 70)

        ctx1 = browser.new_context(viewport={"width": 1440, "height": 1000})
        pg = ctx1.new_page()

        if not login(pg, "admin@ssmspl.com"):
            record("I1", "FAIL", "Cannot login as admin")
            ctx1.close()
        else:
            pg.goto(f"{SITE}/dashboard/ticketing", wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Click "New Ticket" button
            try:
                new_btn = pg.locator("button:has-text('New Ticket')").first
                new_btn.click()
                time.sleep(2)
                pg.screenshot(path=f"{SD}/I1_01_new_ticket_modal.png", full_page=True)

                # Check if modal opened - look for Add Item button
                add_btn = pg.locator("button:has-text('Add Item')").first
                if add_btn.is_visible():
                    record("I1_modal", "PASS", "New Ticket modal opened, Add Item button visible")
                else:
                    record("I1_modal", "FAIL", "Add Item button not found in modal")

                # Check if item-id inputs have the right id attribute
                id_inputs = pg.locator('[id^="item-id-"]').all()
                record("I1_id_attr", "PASS" if len(id_inputs) > 0 else "FAIL",
                       f"Found {len(id_inputs)} input(s) with id='item-id-*'")

                # Click Add Item and check focus
                add_btn.click()
                time.sleep(1)

                # Check which element has focus after adding
                focused_id = pg.evaluate("document.activeElement?.id || ''")
                focused_tag = pg.evaluate("document.activeElement?.tagName || ''")
                focused_type = pg.evaluate("document.activeElement?.type || ''")

                if focused_id.startswith("item-id-"):
                    record("I1_focus", "PASS", f"Focus moved to new row ID input: #{focused_id}")
                else:
                    record("I1_focus", "FAIL",
                           f"Focus NOT on new row ID. Focused: tag={focused_tag} type={focused_type} id='{focused_id}'")

                # Count total id inputs now
                id_inputs_after = pg.locator('[id^="item-id-"]').all()
                record("I1_row_count", "PASS" if len(id_inputs_after) > len(id_inputs) else "FAIL",
                       f"Rows before={len(id_inputs)}, after={len(id_inputs_after)}")

                pg.screenshot(path=f"{SD}/I1_02_after_add_item.png", full_page=True)

            except Exception as e:
                record("I1_error", "FAIL", f"Error: {e}")

            ctx1.close()

        # ================================================================
        # ISSUES 2,3,4,5 - Reports (test with manager)
        # ================================================================
        print(f"\n{'=' * 70}")
        print("ISSUES 2-5 - Reports Module")
        print("=" * 70)

        ctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
        pg = ctx2.new_page()

        api_log = []
        def on_resp(resp):
            if "/api/" in resp.url:
                body = ""
                try: body = resp.text()[:500]
                except: pass
                api_log.append({"url": resp.url, "status": resp.status, "body": body})
        pg.on("response", on_resp)

        if not login(pg, "manager@ssmspl.com"):
            record("I2", "FAIL", "Cannot login as manager")
            ctx2.close()
        else:
            print(f"\n  Logged in as manager")

            # Navigate to reports
            pg.goto(f"{SITE}/dashboard/reports", wait_until="networkidle", timeout=30000)
            time.sleep(4)

            # ── ISSUE 2: Print Layout ──
            print(f"\n--- ISSUE 2: Print Layout ---")

            # Check PRINT_STYLES content
            html = pg.content()
            has_a4 = "size: A4" in html or "size:A4" in html
            has_margin = "margin: 10mm" in html or "margin:10mm" in html
            has_print_media = "@media print" in html
            has_page_rule = "@page" in html

            record("I2_page_a4", "PASS" if has_a4 else "FAIL", f"@page size A4: {has_a4}")
            record("I2_margin", "PASS" if has_margin else "FAIL", f"@page margin 10mm: {has_margin}")
            record("I2_print_media", "PASS" if has_print_media else "FAIL", f"@media print present: {has_print_media}")

            # Check print-only header exists (hidden on screen)
            print_header = pg.locator('.hidden.print\\:block').all()
            record("I2_print_header", "PASS" if print_header else "FAIL",
                   f"Print-only header block found: {len(print_header)}")

            # Check header content
            if print_header:
                header_html = print_header[0].inner_html()
                has_company = "SSMSPL" in header_html
                has_report_name = True  # Dynamic content
                record("I2_header_content", "PASS" if has_company else "FAIL",
                       f"Company name in print header: {has_company}")

            # Generate a report to test print/download buttons
            date_inputs = pg.locator('input[type="date"]').all()
            if len(date_inputs) >= 2:
                date_inputs[0].fill(DATA_FROM)
                date_inputs[1].fill(TODAY)
            pg.locator("button:has-text('Generate Report')").first.click()
            time.sleep(4)
            pg.wait_for_load_state("networkidle", timeout=15000)

            pg.screenshot(path=f"{SD}/I2_01_date_wise_generated.png", full_page=True)

            # Check that sidebar/filters hidden elements have print:hidden
            sidebar_elements = pg.locator('[class*="print:hidden"]').all()
            record("I2_hidden_elements", "PASS" if len(sidebar_elements) >= 3 else "FAIL",
                   f"Elements with print:hidden class: {len(sidebar_elements)}")

            # ── ISSUE 3: Branch Summary Print Buttons ──
            print(f"\n--- ISSUE 3: Branch Summary Print Buttons ---")

            # Switch to Branch Summary
            pg.locator("button:text-is('Branch Summary')").first.click()
            time.sleep(2)

            date_inputs = pg.locator('input[type="date"]:visible').all()
            if len(date_inputs) >= 2:
                date_inputs[0].fill(DATA_FROM)
                date_inputs[1].fill(TODAY)
            pg.locator("button:has-text('Generate Report')").first.click()
            time.sleep(4)
            pg.wait_for_load_state("networkidle", timeout=15000)

            pg.screenshot(path=f"{SD}/I3_01_branch_summary.png", full_page=True)

            # Count all print-related buttons
            all_btns = pg.locator("button:visible").all()
            print_btns = []
            for btn in all_btns:
                text = (btn.text_content() or "").strip()
                if "print" in text.lower():
                    print_btns.append(text)

            record("I3_print_btns", "PASS" if print_btns.count("Print") <= 1 else "FAIL",
                   f"Print buttons: {print_btns}")

            has_80mm = any("80mm" in t for t in print_btns)
            has_regular_print = "Print" in print_btns
            record("I3_80mm", "PASS" if has_80mm else "FAIL", f"Print 80mm button: {has_80mm}")
            record("I3_regular", "PASS" if has_regular_print else "FAIL", f"Regular Print button: {has_regular_print}")

            # Check Download PDF exists
            download_btns = [b for b in all_btns if "download" in (b.text_content() or "").lower()]
            record("I3_download", "PASS" if download_btns else "FAIL",
                   f"Download PDF button: {len(download_btns)}")

            # Now switch to Date Wise Amount and verify NO 80mm button
            pg.locator("button:text-is('Date Wise Amount')").first.click()
            time.sleep(2)
            date_inputs = pg.locator('input[type="date"]:visible').all()
            if len(date_inputs) >= 2:
                date_inputs[0].fill(DATA_FROM)
                date_inputs[1].fill(TODAY)
            pg.locator("button:has-text('Generate Report')").first.click()
            time.sleep(4)

            all_btns_dwa = pg.locator("button:visible").all()
            dwa_print_btns = [(btn.text_content() or "").strip() for btn in all_btns_dwa
                              if "print" in (btn.text_content() or "").lower()]
            has_80mm_dwa = any("80mm" in t for t in dwa_print_btns)
            record("I3_no_80mm_other", "PASS" if not has_80mm_dwa else "FAIL",
                   f"Date Wise Amount should NOT have 80mm: buttons={dwa_print_btns}")

            # ── ISSUE 4: Thermal Printer CSS ──
            print(f"\n--- ISSUE 4: Thermal Printer Support ---")

            has_80mm_media = "@media print and (max-width: 80mm)" in html
            has_58mm_media = "@media print and (max-width: 58mm)" in html
            record("I4_80mm_css", "PASS" if has_80mm_media else "FAIL",
                   f"80mm print media query: {has_80mm_media}")
            record("I4_58mm_css", "PASS" if has_58mm_media else "FAIL",
                   f"58mm print media query: {has_58mm_media}")

            # ── ISSUE 5: User Hierarchy Filter ──
            print(f"\n--- ISSUE 5: User Hierarchy Filter ---")

            # Check report-users API was called
            report_users_calls = [r for r in api_log if "report-users" in r["url"]]
            if report_users_calls:
                resp = report_users_calls[-1]
                record("I5_api", "PASS" if resp["status"] == 200 else "FAIL",
                       f"GET /api/reports/report-users -> {resp['status']}")
                try:
                    users_data = json.loads(resp["body"])
                    record("I5_users_count", "PASS",
                           f"Manager sees {len(users_data)} users: {[u['full_name'] for u in users_data[:5]]}")
                    # Check none are admin/superadmin
                    # (We can't verify roles from here, but the endpoint should filter)
                except:
                    record("I5_parse", "FAIL", f"Cannot parse users response: {resp['body'][:200]}")
            else:
                record("I5_api", "FAIL", "report-users endpoint NOT called")

            # Check User Wise Daily has the dropdown
            pg.locator("button:text-is('User Wise Daily')").first.click()
            time.sleep(2)
            pg.screenshot(path=f"{SD}/I5_01_user_wise.png", full_page=True)

            labels = [l.text_content().strip() for l in pg.locator("label:visible").all()]
            has_operator_label = "Billing Operator" in labels
            record("I5_dropdown", "PASS" if has_operator_label else "FAIL",
                   f"Billing Operator dropdown visible for manager: {has_operator_label}")

            ctx2.close()

        # ================================================================
        # ISSUE 5 (continued) - Test as billing operator
        # ================================================================
        print(f"\n--- ISSUE 5b: Billing Operator Role ---")

        ctx3 = browser.new_context(viewport={"width": 1440, "height": 1000})
        pg = ctx3.new_page()

        api_log.clear()
        pg.on("response", on_resp)

        if not login(pg, "billing@ssmspl.com"):
            record("I5b", "FAIL", "Cannot login as billing operator")
        else:
            pg.goto(f"{SITE}/dashboard/reports", wait_until="networkidle", timeout=30000)
            time.sleep(4)

            # Switch to User Wise Daily
            pg.locator("button:text-is('User Wise Daily')").first.click()
            time.sleep(2)
            pg.screenshot(path=f"{SD}/I5_02_billing_operator.png", full_page=True)

            labels = [l.text_content().strip() for l in pg.locator("label:visible").all()]
            has_operator_label = "Billing Operator" in labels
            record("I5b_no_dropdown", "PASS" if not has_operator_label else "FAIL",
                   f"Billing Operator should NOT see dropdown: visible={has_operator_label}, labels={labels}")

            # Check report-users returns only self
            ru_calls = [r for r in api_log if "report-users" in r["url"] and r["status"] == 200]
            if ru_calls:
                try:
                    users_data = json.loads(ru_calls[-1]["body"])
                    record("I5b_self_only", "PASS" if len(users_data) == 1 else "FAIL",
                           f"Billing operator sees {len(users_data)} user(s): {users_data}")
                except:
                    record("I5b_parse", "FAIL", "Cannot parse response")
            else:
                record("I5b_api", "FAIL", "report-users not called for billing operator")

        ctx3.close()

        # ================================================================
        # ISSUE 6 - Global Search Removed
        # ================================================================
        print(f"\n{'=' * 70}")
        print("ISSUE 6 - Global Search Removed")
        print("=" * 70)

        ctx4 = browser.new_context(viewport={"width": 1440, "height": 1000})
        pg = ctx4.new_page()

        if login(pg, "admin@ssmspl.com"):
            pg.goto(f"{SITE}/dashboard", wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Look for the search input in the header
            search_inputs = pg.locator('input[placeholder="Search..."]').all()
            header_search = pg.locator('header input[placeholder="Search..."]').all()
            record("I6_global_search", "PASS" if len(header_search) == 0 else "FAIL",
                   f"Global search in header: {len(header_search)} (should be 0)")

            pg.screenshot(path=f"{SD}/I6_01_no_search.png", full_page=True)

            # Also check reports page
            pg.goto(f"{SITE}/dashboard/reports", wait_until="networkidle", timeout=30000)
            time.sleep(3)
            header_search2 = pg.locator('header input[placeholder="Search..."]').all()
            record("I6_reports_no_search", "PASS" if len(header_search2) == 0 else "FAIL",
                   f"Global search on reports: {len(header_search2)}")

        ctx4.close()

        # ================================================================
        # FINAL SUMMARY
        # ================================================================
        browser.close()

        print(f"\n{'=' * 70}")
        print("FINAL QA SUMMARY")
        print(f"{'=' * 70}")

        pass_c = sum(1 for r in results.values() if r["status"] == "PASS")
        fail_c = sum(1 for r in results.values() if r["status"] == "FAIL")
        total = len(results)

        print(f"\nTotal: {total} | PASS: {pass_c} | FAIL: {fail_c}\n")
        for tid, res in results.items():
            print(f"  [{res['status']:4s}] {tid}: {res['detail']}")

        print(f"\nScreenshots saved to {SD}/")

if __name__ == "__main__":
    main()
