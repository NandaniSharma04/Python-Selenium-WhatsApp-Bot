"""
STEP 2 — One-Time WhatsApp Web Login (Fixed for Chromium v135)
===============================================================
Run this script ONCE to scan the QR code and save your session.
After this, you will never need to scan again.

Instructions:
1. Make sure chromedriver.exe is in E:\Messenger\ (same folder as this file)
2. Run: python login_once.py
3. A Chrome/Chromium window will open WhatsApp Web
4. Scan the QR code with your phone
5. Wait until your chats load fully
6. Press ENTER in this terminal to save and close
"""

import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# ── Paths ────────────────────────────────────────────────────────────────────

# ChromeDriver must be in the same folder as this script
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")

# Your Chromium browser path (detected from your error message)
CHROMIUM_PATH = r"C:\Users\hp\AppData\Local\Chromium\Application\chrome.exe"

# Session profile saved to Desktop
PROFILE_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "whatsapp_profile")
os.makedirs(PROFILE_PATH, exist_ok=True)

# ── Sanity checks ─────────────────────────────────────────────────────────────
if not os.path.exists(CHROMEDRIVER_PATH):
    print("ERROR: chromedriver.exe not found!")
    print(f"   Expected location: {CHROMEDRIVER_PATH}")
    print("\n   Please download it from:")
    print("   https://googlechromelabs.github.io/chrome-for-testing/#stable")
    print("   Choose: chromedriver > win64 > extract > put chromedriver.exe in E:\\Messenger\\")
    input("\nPress ENTER to exit...")
    exit(1)

if not os.path.exists(CHROMIUM_PATH):
    print("ERROR: Chromium browser not found at expected path.")
    print(f"   Expected: {CHROMIUM_PATH}")
    input("\nPress ENTER to exit...")
    exit(1)

print(f"[OK] ChromeDriver found:  {CHROMEDRIVER_PATH}")
print(f"[OK] Chromium found:      {CHROMIUM_PATH}")
print(f"[OK] Profile path:        {PROFILE_PATH}\n")

# ── Chrome options (VISIBLE window for QR scan) ───────────────────────────────
options = Options()
options.binary_location = CHROMIUM_PATH
options.add_argument(f"--user-data-dir={PROFILE_PATH}")
options.add_argument("--profile-directory=Default")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# No headless here — we need to SEE the QR code this one time

# ── Launch browser ────────────────────────────────────────────────────────────
print("[INFO] Opening Chromium... please wait.")
service = Service(executable_path=CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://web.whatsapp.com")

print("\n" + "="*55)
print("  ACTION REQUIRED")
print("="*55)
print("  1. Scan the QR code shown in the Chromium window.")
print("  2. Wait until ALL your chats have loaded.")
print("  3. Come back here and press ENTER to save & close.")
print("="*55 + "\n")

input("  >>> Press ENTER after your chats have loaded: ")

print("\n[SUCCESS] Session saved!")
print(f"   Profile stored at: {PROFILE_PATH}")
print("   You can now run the main app. No QR scan needed again!")

driver.quit()