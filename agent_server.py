import json
import os
import re
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from openai import OpenAI
from dotenv import load_dotenv

# ================== CONFIG ==================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a browser automation planner for Playwright (Python).

Convert the given TASK + SUBTASKS into a JSON array of steps.

Each step MUST follow this schema:
{
  "type": "open" | "click" | "wait_for" | "type",
  "url": "string (only for open)",
  "selector": "string (for click/wait_for/type)",
  "text": "string (only for type)"
}

Rules:
- Return ONLY raw JSON array. No markdown. No explanation.
- Use Playwright locators only (no jQuery selectors)
- Examples:
  { "type": "open", "url": "http://localhost:8080/" }
  { "type": "click", "selector": "role=link[name=\\"Create Account\\"]" }
  { "type": "wait_for", "selector": "input[placeholder=\\"Enter your full name\\"]" }
  { "type": "type", "selector": "input[type=\\"email\\"]", "text": "piyush@gmail" }

- After clicking Create Account link, wait for:
  input[placeholder="Enter your full name"]

- After clicking Create Account button, wait for:
  role=button[name="Login"]

- After clicking Login button, wait for:
  #dashboard

  
"""

TASK_INPUT = {
    "task": "Open http://localhost:8080/ and create a new account, then login and wait for dashboard.",
    "subtasks": [
        "Click on the Create Account link on the home page",
        "Wait for the Create Account page to load",
        "Fill the form with Name Piyush, Email piyush@gmail, Password Abcd1234, Confirm Password Abcd1234",
        "Click Create Account",
        "Wait for Login page",
        "Enter Email piyush@gmail",
        "Enter Password Abcd1234",
        "Click Login",
        "Wait for Dashboard"
        "Select the medicine Amoxicillin 500mg in the select medicine dropdown",
        "Select 6 Months in the Forecast duration dropdown",
        "Click on the Generate Prediction button"
    ]
}

# ================== LLM PLANNER ==================
def generate_plan():
    prompt = f"""
TASK:
{TASK_INPUT["task"]}

SUBTASKS:
{json.dumps(TASK_INPUT["subtasks"], indent=2)}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()
    print("\n🧠 LLM RAW PLAN:\n", raw)

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise ValueError("❌ LLM did not return valid JSON")

    return json.loads(match.group(0))

# ================== SELECTOR HELPERS ==================
def parse_role(selector: str):
    role = selector.split("[")[0].replace("role=", "")
    match = re.search(r'name="(.*?)"', selector)
    name = match.group(1) if match else None
    return role, name

def wait_visible(page, selector):
    if selector.startswith("role="):
        role, name = parse_role(selector)
        page.get_by_role(role, name=name).first.wait_for(state="visible", timeout=30000)
    else:
        page.locator(selector).first.wait_for(state="visible", timeout=30000)

def click_locator(page, selector):
    wait_visible(page, selector)
    if selector.startswith("role="):
        role, name = parse_role(selector)
        page.get_by_role(role, name=name).first.click()
    else:
        page.locator(selector).first.click()

def fill_locator(page, selector, value):
    selectors_to_try = [selector]

    # Fallbacks for common fields
    if "password" in selector.lower():
        selectors_to_try.extend([
            'input[type="password"]',
            'input[name="password"]',
            '#password'
        ])
    if "email" in selector.lower():
        selectors_to_try.extend([
            'input[type="email"]',
            'input[name="email"]',
            '#email'
        ])

    last_error = None

    for sel in selectors_to_try:
        try:
            if sel.startswith("role="):
                role, name = parse_role(sel)
                loc = page.get_by_role(role, name=name).first
            else:
                loc = page.locator(sel).first

            loc.wait_for(state="visible", timeout=5000)
            loc.fill("")
            loc.type(value, delay=50)
            print(f"✅ Filled using selector: {sel}")
            return

        except Exception as e:
            last_error = e
            continue

    raise last_error

# ================== EXECUTOR ==================
def run_agent():
    plan = generate_plan()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        page.set_viewport_size({"width": 1400, "height": 900})

        for i, step in enumerate(plan):
            print(f"\n➡️ Step {i+1}: {step}")

            try:
                if step["type"] == "open":
                    page.goto(step["url"], wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(1500)
                    print("✅ Opened:", page.url)

                elif step["type"] == "click":
                    click_locator(page, step["selector"])

                elif step["type"] == "type":
                    fill_locator(page, step["selector"], step["text"])

                elif step["type"] == "wait_for":
                    wait_visible(page, step["selector"])

                time.sleep(0.6)

            except PlaywrightTimeoutError:
                print("⏰ Timeout on step:", step)
                page.screenshot(path=f"timeout_step_{i+1}.png")
                break

            except Exception as e:
                print("❌ Step failed:", step)
                print("🔥 Error:", e)
                page.screenshot(path=f"error_step_{i+1}.png")
                break

        print("\n✅ Flow finished. Browser will stay open.")
        input("Press ENTER to close browser...")
        browser.close()

if __name__ == "__main__":
    run_agent()
