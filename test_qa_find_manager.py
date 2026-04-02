"""Find manager user credentials from the API."""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

SITE = "https://carferry.online"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture API responses
        users_data = []
        def handle_response(resp):
            if "/api/users" in resp.url and resp.status == 200:
                try:
                    users_data.append(resp.json())
                except:
                    pass
        page.on("response", handle_response)

        # Login as admin
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
                    print(f"Session conflict, waiting 70s...")
                    time.sleep(70)

        if "dashboard" not in page.url:
            print("Cannot login as admin")
            browser.close()
            return

        # Fetch users
        page.goto(f"{SITE}/dashboard/users", wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # Get the users from the table
        tables = page.locator("table").all()
        if tables:
            rows = tables[0].locator("tbody tr").all()
            print(f"Found {len(rows)} users in table:")
            for row in rows:
                cells = row.locator("td").all()
                cell_texts = [c.text_content().strip() for c in cells[:6]]
                print(f"  {cell_texts}")

        # Also try API directly
        for data in users_data:
            if isinstance(data, list):
                for u in data:
                    role = u.get("role", "")
                    email = u.get("email", "")
                    username = u.get("username", "")
                    name = u.get("full_name", "")
                    active = u.get("is_active", "")
                    print(f"  API: {role:20s} {email:35s} {username:20s} {name} active={active}")

        browser.close()

if __name__ == "__main__":
    main()
