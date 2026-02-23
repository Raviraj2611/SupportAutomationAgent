from playwright.sync_api import sync_playwright

def use_browser(action: dict):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        if action["type"] == "open":
            page.goto(action["url"])
            content = page.content()

        elif action["type"] == "click":
            page.click(action["selector"])
            content = page.content()

        elif action["type"] == "type":
            page.fill(action["selector"], action["text"])
            content = page.content()

        browser.close()
        return content
