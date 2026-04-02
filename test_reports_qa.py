"""QA: Full report module testing - all tabs, filters, errors, PDFs."""
import os, sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
from datetime import date as dt_date

SITE = "https://carferry.online"
SD = "screenshots_review"
os.makedirs(SD, exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Capture API responses
        api_log = []
        def handle_response(resp):
            if "/api/" in resp.url:
                body = ""
                try:
                    body = resp.text()[:500]
                except:
                    pass
                api_log.append({"url": resp.url, "status": resp.status, "body": body})
        page.on("response", handle_response)

        # -- LOGIN --
        print("=" * 70)
        print("SSMSPL REPORTS QA TEST SUITE")
        print("=" * 70)
        print("\n[LOGIN] Attempting admin@ssmspl.com...")

        for attempt in range(4):
            page.goto(f"{SITE}/login", wait_until="networkidle", timeout=30000)
            time.sleep(1)

            # Check if already redirected to dashboard (existing session)
            if "dashboard" in page.url:
                print(f"  Already logged in - on {page.url}")
                break

            page.fill('input[type="email"]', "admin@ssmspl.com")
            page.fill('input[type="password"]', "Password@123")
            page.click('button[type="submit"]')

            # Wait for navigation
            try:
                page.wait_for_url("**/dashboard**", timeout=10000)
                print(f"  OK - Redirected to {page.url}")
                break
            except:
                pass

            time.sleep(2)
            current = page.url
            print(f"  Attempt {attempt+1}: URL={current}")

            if "dashboard" in current:
                break

            body = page.inner_text("body")
            if "already logged in" in body.lower():
                wait = 70
                print(f"  Session conflict. Waiting {wait}s...")
                time.sleep(wait)
            else:
                page.screenshot(path=f"{SD}/login_attempt_{attempt}.png")
                print(f"  Unknown error. Saved screenshot.")
                if attempt == 3:
                    print("[LOGIN] FATAL")
                    browser.close()
                    return

        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)
        page.screenshot(path=f"{SD}/01_dashboard.png")
        print(f"[LOGIN] Logged in. URL: {page.url}")

        # ================================================================
        # NAVIGATE TO REPORTS
        # ================================================================
        print("\n[NAV] Going to /dashboard/reports...")
        api_log.clear()
        page.goto(f"{SITE}/dashboard/reports", wait_until="networkidle", timeout=30000)
        time.sleep(4)
        page.screenshot(path=f"{SD}/10_reports_landing.png", full_page=True)
        print(f"  URL: {page.url}")

        # ================================================================
        # PHASE 1: Discover tabs
        # ================================================================
        print("\n" + "=" * 70)
        print("PHASE 1: REPORT TABS")
        print("=" * 70)

        all_buttons = page.locator("button:visible").all()
        print(f"Total visible buttons: {len(all_buttons)}")
        for i, btn in enumerate(all_buttons):
            text = (btn.text_content() or "").strip()
            if text and len(text) < 50:
                role = btn.get_attribute("role") or ""
                ds = btn.get_attribute("data-state") or ""
                cls = (btn.get_attribute("class") or "")[:60]
                active_mark = " <<< ACTIVE" if ds == "active" or "bg-blue" in cls or "active" in cls.lower() else ""
                print(f"  [{i:2d}] '{text}' role={role} data-state={ds}{active_mark}")

        # ================================================================
        # PHASE 2: Date filter defaults
        # ================================================================
        print("\n" + "=" * 70)
        print("PHASE 2: DATE FILTER DEFAULTS")
        print("=" * 70)

        today_str = dt_date.today().strftime("%Y-%m-%d")
        date_inputs = page.locator('input[type="date"]').all()
        for i, d in enumerate(date_inputs):
            val = d.input_value()
            label = ["From Date", "To Date"][i] if i < 2 else f"Date_{i}"
            status = "PASS" if val == today_str else f"FAIL (got='{val}' expected='{today_str}')"
            print(f"  {label}: {status}")

        # ================================================================
        # PHASE 3: Dropdown filters
        # ================================================================
        print("\n" + "=" * 70)
        print("PHASE 3: FILTER DROPDOWNS")
        print("=" * 70)

        selects = page.locator("select:visible").all()
        print(f"Visible dropdowns: {len(selects)}")
        for i, sel in enumerate(selects):
            try:
                options = sel.locator("option").all()
                opt_texts = [o.text_content().strip() for o in options[:10]]
                print(f"  [{i}] {opt_texts}")
            except:
                pass

        # ================================================================
        # PHASE 4: Initial API calls
        # ================================================================
        print("\n" + "=" * 70)
        print("PHASE 4: API RESPONSES ON LOAD")
        print("=" * 70)

        for r in api_log:
            url_short = r["url"].replace(SITE, "").split("?")[0]
            params = r["url"].split("?")[1][:100] if "?" in r["url"] else ""
            if r["status"] >= 400:
                print(f"  FAIL {r['status']} {url_short}")
                if params: print(f"    Params: {params}")
                print(f"    Body: {r['body'][:200]}")
            elif "report" in url_short.lower():
                print(f"  OK   {r['status']} {url_short}")
                if params: print(f"    Params: {params}")

        # ================================================================
        # PHASE 5: Error check
        # ================================================================
        print("\n" + "=" * 70)
        print("PHASE 5: PAGE ERROR CHECK")
        print("=" * 70)

        body_text = page.inner_text("body")
        if "Failed to load" in body_text:
            print("  FAIL: 'Failed to load data' found!")
        else:
            print("  PASS: No 'Failed to load' errors")

        if "No data" in body_text or "no report" in body_text.lower():
            print("  INFO: 'No data' displayed (expected if no tickets today)")

        # Check table
        tables = page.locator("table:visible").all()
        if tables:
            headers = tables[0].locator("th").all()
            header_texts = [h.text_content().strip() for h in headers]
            rows = tables[0].locator("tbody tr").all()
            print(f"  Table: {len(rows)} data rows")
            print(f"  Columns: {header_texts}")
        else:
            print("  No visible table (check screenshot)")

        # ================================================================
        # PHASE 6: Click through all tabs and screenshot each
        # ================================================================
        print("\n" + "=" * 70)
        print("PHASE 6: CLICK EACH REPORT TAB")
        print("=" * 70)

        # Re-discover tab-like buttons (filter out action buttons like Print, Download)
        action_words = {"print", "download", "pdf", "sign", "generate", "search", "reset", "clear", "apply", "logout"}
        tab_btns = []
        for btn in page.locator("button:visible").all():
            text = (btn.text_content() or "").strip()
            if not text or len(text) > 40:
                continue
            if text.lower() in action_words or any(w in text.lower() for w in action_words):
                continue
            # Check if it's in a tab-like container
            tab_btns.append((text, btn))

        # Deduplicate by text
        seen = set()
        unique_tabs = []
        for text, btn in tab_btns:
            if text not in seen:
                seen.add(text)
                unique_tabs.append((text, btn))

        print(f"Candidate tabs: {len(unique_tabs)}")
        for text, _ in unique_tabs:
            print(f"  - {text}")

        # Click each tab
        for idx, (text, btn) in enumerate(unique_tabs):
            try:
                api_log.clear()
                print(f"\n  --- Clicking tab: '{text}' ---")
                btn.click()
                time.sleep(3)
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(1)

                # Screenshot
                safe_name = text.lower().replace(" ", "_").replace("/", "_")[:30]
                page.screenshot(path=f"{SD}/tab_{idx:02d}_{safe_name}.png", full_page=True)

                # Check for errors
                body_now = page.inner_text("body")
                if "Failed to load" in body_now:
                    print(f"    FAIL: 'Failed to load' on '{text}'!")
                else:
                    print(f"    PASS: No errors")

                # Check table
                tables_now = page.locator("table:visible").all()
                if tables_now:
                    headers_now = tables_now[0].locator("th").all()
                    h_texts = [h.text_content().strip() for h in headers_now]
                    rows_now = tables_now[0].locator("tbody tr").all()
                    print(f"    Table: {len(rows_now)} rows, columns: {h_texts}")
                else:
                    print(f"    No table visible")

                # Check API
                for r in api_log:
                    if "report" in r["url"].lower() and r["status"] >= 400:
                        url_short = r["url"].replace(SITE, "").split("?")[0]
                        print(f"    API FAIL: {r['status']} {url_short}: {r['body'][:150]}")

            except Exception as e:
                print(f"    ERROR clicking tab '{text}': {e}")

        browser.close()
        print(f"\n{'=' * 70}")
        print(f"QA Phase 1 complete. Screenshots saved to {SD}/")
        print(f"{'=' * 70}")

if __name__ == "__main__":
    main()
