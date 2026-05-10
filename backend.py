import os
import re
import time
import random
import threading
import urllib.parse
import csv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from plyer import notification

# ── Paths ────────────────────────────────────────────────────────────────────

CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")
CHROMIUM_PATH     = r"C:\Users\hp\AppData\Local\Chromium\Application\chrome.exe"
PROFILE_PATH      = os.path.join(os.path.expanduser("~"), "Desktop", "whatsapp_profile")
CONTACTS_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "formatted_contacts.csv")

MIN_DELAY = 8
MAX_DELAY = 14

COUNTRY_CODES = [
    ("🇮🇳 India          +91", "91"),
    ("🇺🇸 USA            +1",  "1"),
    ("🇬🇧 UK             +44", "44"),
    ("🇦🇺 Australia      +61", "61"),
    ("🇨🇦 Canada         +1",  "1"),
    ("🇦🇪 UAE            +971","971"),
    ("🇸🇦 Saudi Arabia   +966","966"),
    ("🇵🇰 Pakistan       +92", "92"),
    ("🇧🇩 Bangladesh     +880","880"),
    ("🇳🇵 Nepal          +977","977"),
    ("🇱🇰 Sri Lanka      +94", "94"),
    ("🇲🇾 Malaysia       +60", "60"),
    ("🇸🇬 Singapore      +65", "65"),
    ("🇿🇦 South Africa   +27", "27"),
    ("🇳🇬 Nigeria        +234","234"),
    ("🇰🇪 Kenya          +254","254"),
    ("🇩🇪 Germany        +49", "49"),
    ("🇫🇷 France         +33", "33"),
    ("🇮🇹 Italy          +39", "39"),
    ("🇧🇷 Brazil         +55", "55"),
    ("🇲🇽 Mexico         +52", "52"),
    ("🇮🇩 Indonesia      +62", "62"),
    ("🇵🇭 Philippines    +63", "63"),
]

# Keywords that confirm WhatsApp Web has fully loaded the chat sidebar
LOADED_KEYWORDS = [
    "Search or start a new chat",
    "chatlist",
    "Unread",
    "New chat",
    'data-testid="chat-list"',
    "Start new chat",
]

# ── Updated selectors – ordered from most reliable to fallback ────────────────
# WhatsApp Web 2024/2025 uses aria-label and data-tab="10" for the footer box.
MSG_BOX_SELECTORS = [
    # Most reliable for current WhatsApp Web
    (By.CSS_SELECTOR, 'div[aria-label="Type a message"]'),
    (By.CSS_SELECTOR, 'div[aria-label="Message"]'),
    (By.CSS_SELECTOR, 'div[aria-label="type a message"]'),
    (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]'),
    (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="1"]'),
    # Generic fallbacks
    (By.XPATH,        '//div[@title="Type a message"]'),
    (By.XPATH,        '//div[@aria-label="Type a message"]'),
    (By.XPATH,        '//div[@aria-label="Message"]'),
    (By.XPATH,        '//div[@role="textbox" and @contenteditable="true"]'),
    (By.CSS_SELECTOR, 'footer div[contenteditable="true"]'),
    (By.XPATH,        '(//div[@contenteditable="true"])[last()]'),
]

# Selectors that confirm a phone number is INVALID (no WhatsApp account)
INVALID_PHONE_SELECTORS = [
    (By.XPATH,       '//*[contains(text(),"Phone number shared via url is invalid")]'),
    (By.XPATH,       '//*[contains(text(),"phone number is invalid")]'),
    (By.CSS_SELECTOR,'div[data-animate-modal-popup="true"]'),
    (By.XPATH,       '//*[contains(@class,"popup-contents")]'),
]

# ── Utility: screenshot helper ─────────────────────────────────────────────────

def _screenshot(driver, tag):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"debug_{tag}.png")
    try:
        driver.save_screenshot(path)
    except Exception:
        pass
    return path


# ── Window hiding ─────────────────────────────────────────────────────────────

def hide_our_window(pid, retries=8):
    import ctypes
    SW_HIDE = 0
    user32  = ctypes.windll.user32
    found   = [False]

    def callback(hwnd, _):
        try:
            pid_found = ctypes.c_ulong(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_found))
            if pid_found.value == pid and user32.IsWindowVisible(hwnd):
                user32.ShowWindow(hwnd, SW_HIDE)
                found[0] = True
        except Exception:
            pass
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
    )
    for _ in range(retries):
        user32.EnumWindows(WNDENUMPROC(callback), 0)
        if found[0]:
            break
        time.sleep(1)


# ── Driver ────────────────────────────────────────────────────────────────────

def create_driver():
    options = Options()
    options.binary_location = CHROMIUM_PATH
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    # Disable automation banner
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver  = webdriver.Chrome(service=service, options=options)
    # Remove navigator.webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


# ── WhatsApp load check ───────────────────────────────────────────────────────

def wait_for_whatsapp_load(driver, log_func, timeout=120):
    log_func("[INFO] Waiting for WhatsApp Web to load…")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            src = driver.page_source
            if any(kw in src for kw in LOADED_KEYWORDS):
                log_func("[INFO] WhatsApp Web loaded successfully!")
                time.sleep(3)
                return True
        except Exception:
            pass
        time.sleep(2)
    shot = _screenshot(driver, "loading_timeout")
    log_func(f"[ERROR] Timed out waiting for WhatsApp. Screenshot → {shot}")
    return False


# ── Invalid phone popup check ─────────────────────────────────────────────────

def _is_invalid_phone(driver):
    """Returns True if WhatsApp shows an 'invalid number' popup."""
    for by, sel in INVALID_PHONE_SELECTORS:
        try:
            els = driver.find_elements(by, sel)
            for el in els:
                txt = el.text.lower()
                if "invalid" in txt or "not registered" in txt or "phone number" in txt:
                    return True
        except Exception:
            pass
    # Also check page source quickly
    try:
        src = driver.page_source.lower()
        if "phone number shared via url is invalid" in src:
            return True
    except Exception:
        pass
    return False


# ── Message box finder ────────────────────────────────────────────────────────

def find_message_box(driver, timeout=60):
    """
    Wait up to `timeout` seconds for any known message-box selector to appear
    and be interactable. Returns the element or None.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        # First check if the phone is invalid — bail early
        if _is_invalid_phone(driver):
            return None

        for by, sel in MSG_BOX_SELECTORS:
            try:
                elements = driver.find_elements(by, sel)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        # Extra check: make sure it's actually in the chat footer area
                        # and not some search box
                        tag  = el.get_attribute("data-tab") or ""
                        role = el.get_attribute("role") or ""
                        aria = (el.get_attribute("aria-label") or "").lower()
                        # Accept known good attributes
                        if tag in ("10", "1") or "message" in aria or "type" in aria or role == "textbox":
                            return el
                        # If none of those matched, still accept last resort
                        if by == By.XPATH and "last()" in sel:
                            return el
            except Exception:
                pass
        time.sleep(1.5)
    return None


# ── Phone normalisation ───────────────────────────────────────────────────────

def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("00"):
        digits = digits[2:]
    return "+" + digits if digits else ""


def clean_phone(number, country_code):
    digits = re.sub(r"\D", "", number)
    if digits.startswith(country_code):
        digits = digits[len(country_code):]
    digits = digits.lstrip("0")
    return f"+{country_code}{digits}"


# ── Core send ─────────────────────────────────────────────────────────────────

def send_message(driver, phone, message, log_func):
    phone   = normalize_phone(phone)
    encoded = urllib.parse.quote(message)
    url     = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}"
    log_func(f"[→] {phone} — opening chat…")

    try:
        driver.get(url)

        # Give the page a moment to start loading
        time.sleep(4)

        # Wait for the message box (up to 60 s)
        msg_box = find_message_box(driver, timeout=60)

        if msg_box is None:
            # Check if it's an invalid number popup
            if _is_invalid_phone(driver):
                log_func(f"[✗] {phone} — number not on WhatsApp / invalid.")
            else:
                shot = _screenshot(driver, phone.replace("+", ""))
                log_func(f"[✗] {phone} — message box not found. Screenshot → {shot}")
            return False

        # Scroll element into view and click it
        driver.execute_script("arguments[0].scrollIntoView(true);", msg_box)
        time.sleep(0.5)

        # Click to focus
        try:
            msg_box.click()
        except Exception:
            driver.execute_script("arguments[0].click();", msg_box)
        time.sleep(0.8)

        # The text was already pre-filled by the URL — just press Enter
        msg_box.send_keys(Keys.ENTER)
        time.sleep(2.5)

        # Verify message was sent by checking the box is now empty
        remaining = msg_box.get_attribute("innerHTML") or ""
        if len(remaining.strip()) < 10:
            log_func(f"[✓] {phone} — sent!")
            notification.notify(
                title="WhatsApp Messenger",
                message=f"Sent to {phone}",
                app_name="WhatsApp Messenger",
                timeout=3,
            )
            return True
        else:
            # Text still in box — try once more
            log_func(f"[~] {phone} — retrying send…")
            msg_box.send_keys(Keys.ENTER)
            time.sleep(2)
            log_func(f"[✓] {phone} — sent (retry)!")
            return True

    except Exception as e:
        log_func(f"[✗] {phone} — error: {str(e)[:120]}")
        shot = _screenshot(driver, phone.replace("+", "") + "_err")
        log_func(f"       Screenshot → {shot}")
        return False


# ── Bulk send orchestrator ────────────────────────────────────────────────────

def run_sending(phones, message, country_code, log_func, progress_func, done_func):
    log_func("[INFO] Starting browser…")
    driver = None
    try:
        driver = create_driver()
        browser_pid = driver.service.process.pid

        log_func("[INFO] Browser started. Hiding window…")
        driver.get("https://web.whatsapp.com")

        threading.Thread(target=hide_our_window, args=(browser_pid,), daemon=True).start()

        loaded = wait_for_whatsapp_load(driver, log_func, timeout=120)
        if not loaded:
            log_func("[ACTION REQUIRED] WhatsApp session expired — run login_once.py to re-scan QR.")
            done_func()
            return

        log_func(f"[INFO] Session OK — sending to {len(phones)} contact(s)…\n")

        total   = len(phones)
        success = 0
        failed  = 0

        for i, raw in enumerate(phones):
            phone = raw.strip()
            if not phone:
                total -= 1
                continue

            if not phone.startswith("+"):
                phone = clean_phone(phone, country_code)

            ok = send_message(driver, phone, message, log_func)
            if ok:
                success += 1
            else:
                failed += 1

            pct = int(((i + 1) / total) * 100)
            progress_func(pct, i + 1, total, success, failed)

            if i < total - 1:
                delay = random.randint(MIN_DELAY, MAX_DELAY)
                log_func(f"[~] Waiting {delay}s before next message…")
                time.sleep(delay)

        log_func("\n" + "=" * 48)
        log_func(f"  DONE!   ✓ Sent: {success}   ✗ Failed: {failed}")
        log_func("=" * 48)
        notification.notify(
            title="WhatsApp Messenger — Done!",
            message=f"Sent: {success}  |  Failed: {failed}",
            app_name="WhatsApp Messenger",
            timeout=6,
        )

    except Exception as e:
        log_func(f"\n[FATAL ERROR] {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        done_func()


# ── CSV helpers ───────────────────────────────────────────────────────────────

def detect_columns(fieldnames):
    lowered = {h.lower().strip(): h for h in (fieldnames or [])}
    name_candidates  = ["name", "first name", "given name", "full name", "contact name"]
    phone_candidates = ["phone", "phone 1 - value", "phone number", "mobile", "number"]
    name_col  = next((lowered[c] for c in name_candidates  if c in lowered), None)
    phone_col = next((lowered[c] for c in phone_candidates if c in lowered), None)
    return name_col, phone_col


def load_contacts(path=CONTACTS_CSV_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot find: {path}")

    contacts = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")

        name_col, phone_col = detect_columns(reader.fieldnames)
        if not name_col or not phone_col:
            raise ValueError(
                f"Could not detect name/phone columns. Found headers: {list(reader.fieldnames)}"
            )

        for row in reader:
            name  = (row.get(name_col)  or "").strip()
            phone = (row.get(phone_col) or "").strip()
            phone = normalize_phone(phone)
            if name and phone:
                contacts.append({"name": name, "phone": phone})

    return contacts