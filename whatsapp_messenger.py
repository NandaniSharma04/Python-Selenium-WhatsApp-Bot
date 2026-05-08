import os
import re
import time
import random
import threading
import urllib.parse
import csv
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from plyer import notification


CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")
CHROMIUM_PATH = r"C:\Users\hp\AppData\Local\Chromium\Application\chrome.exe"
PROFILE_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "whatsapp_profile")
CONTACTS_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "formatted_contacts.csv")

MIN_DELAY = 5
MAX_DELAY = 9

COUNTRY_CODES = [
    ("🇮🇳 India          +91", "91"),
    ("🇺🇸 USA            +1", "1"),
    ("🇬🇧 UK             +44", "44"),
    ("🇦🇺 Australia      +61", "61"),
    ("🇨🇦 Canada         +1", "1"),
    ("🇦🇪 UAE            +971", "971"),
    ("🇸🇦 Saudi Arabia   +966", "966"),
    ("🇵🇰 Pakistan       +92", "92"),
    ("🇧🇩 Bangladesh     +880", "880"),
    ("🇳🇵 Nepal          +977", "977"),
    ("🇱🇰 Sri Lanka      +94", "94"),
    ("🇲🇾 Malaysia       +60", "60"),
    ("🇸🇬 Singapore      +65", "65"),
    ("🇿🇦 South Africa   +27", "27"),
    ("🇳🇬 Nigeria        +234", "234"),
    ("🇰🇪 Kenya          +254", "254"),
    ("🇩🇪 Germany        +49", "49"),
    ("🇫🇷 France         +33", "33"),
    ("🇮🇹 Italy          +39", "39"),
    ("🇧🇷 Brazil         +55", "55"),
    ("🇲🇽 Mexico         +52", "52"),
    ("🇮🇩 Indonesia      +62", "62"),
    ("🇵🇭 Philippines    +63", "63"),
]

LOADED_KEYWORDS = [
    'Search or start a new chat',
    'chatlist', 'Unread', 'New chat',
    'data-testid="chat-list"',
]

MSG_BOX_SELECTORS = [
    (By.XPATH, '//div[@title="Type a message"]'),
    (By.XPATH, '//div[@contenteditable="true" and @data-tab="10"]'),
    (By.XPATH, '//div[@contenteditable="true" and @data-tab="1"]'),
    (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab]'),
    (By.CSS_SELECTOR, 'footer div[contenteditable="true"]'),
    (By.XPATH, '//div[@role="textbox"]'),
    (By.XPATH, '(//div[@contenteditable="true"])[last()]'),
]


def hide_our_window(pid, retries=6):
    import ctypes
    SW_HIDE = 0
    user32 = ctypes.windll.user32
    found = [False]

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


def create_driver():
    options = Options()
    options.binary_location = CHROMIUM_PATH
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,800")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(executable_path=CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)


def wait_for_whatsapp_load(driver, log_func, timeout=90):
    log_func("[INFO] Waiting for WhatsApp to load...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if any(kw in driver.page_source for kw in LOADED_KEYWORDS):
                log_func("[INFO] WhatsApp loaded!")
                time.sleep(2)
                return True
        except Exception:
            pass
        time.sleep(2)
    shot = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_timeout.png")
    driver.save_screenshot(shot)
    log_func(f"[ERROR] Timed out. Screenshot → {shot}")
    return False


def find_message_box(driver, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for by, sel in MSG_BOX_SELECTORS:
            try:
                for el in driver.find_elements(by, sel):
                    if el.is_displayed() and el.is_enabled():
                        return el
            except Exception:
                pass
        time.sleep(1)
    return None


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


def send_message(driver, phone, message, log_func):
    phone = normalize_phone(phone)
    encoded = urllib.parse.quote(message)
    url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}"
    log_func(f"[→] {phone} opening chat...")

    try:
        driver.get(url)
        time.sleep(6)
        msg_box = find_message_box(driver, timeout=45)
        if msg_box is None:
            shot = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"debug_{phone.replace('+','')}.png")
            driver.save_screenshot(shot)
            log_func(f"[✗] {phone} message box not found → {shot}")
            return False
        time.sleep(1)
        msg_box.click()
        time.sleep(0.5)
        msg_box.send_keys(Keys.ENTER)
        time.sleep(2)
        log_func(f"[✓] {phone} sent!")
        notification.notify(title="WhatsApp Messenger", message=f"Sent to {phone}", app_name="WhatsApp Messenger", timeout=3)
        return True
    except Exception as e:
        log_func(f"[✗] {phone} error: {str(e)[:80]}")
        return False


def run_sending(phones, message, country_code, log_func, progress_func, done_func):
    log_func("[INFO] Starting browser...")
    driver = None
    try:
        driver = create_driver()
        browser_pid = driver.service.process.pid
        log_func("[INFO] Browser started. Hiding window...")
        driver.get("https://web.whatsapp.com")
        threading.Thread(target=hide_our_window, args=(browser_pid,), daemon=True).start()
        loaded = wait_for_whatsapp_load(driver, log_func, timeout=90)
        if not loaded:
            log_func("[ACTION] Run login_once.py again.")
            done_func()
            return
        log_func(f"[INFO] Session OK — sending to {len(phones)} contact(s)...\n")
        total = len(phones)
        success = 0
        failed = 0
        for i, raw in enumerate(phones):
            phone = raw.strip()
            if not phone:
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
                log_func(f"[~] Waiting {delay}s...")
                time.sleep(delay)
        log_func(f"\n{'='*45}")
        log_func(f"  DONE!  ✓ Sent: {success}   ✗ Failed: {failed}")
        log_func(f"{'='*45}")
        notification.notify(title="WhatsApp Messenger — Done!", message=f"Sent: {success}  |  Failed: {failed}", app_name="WhatsApp Messenger", timeout=6)
    except Exception as e:
        log_func(f"\n[FATAL ERROR] {e}")
    finally:
        if driver:
            driver.quit()
        done_func()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp Bulk Messenger")
        self.root.geometry("740x820")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")
        self.contacts = {}
        self.contact_names = []
        self._build_ui()

    def _build_ui(self):
        tk.Label(self.root, text="WhatsApp Bulk Messenger", font=("Helvetica", 16, "bold"), bg="#075E54", fg="white", pady=12).pack(fill="x")
        tk.Label(self.root, text="  ℹ  Browser opens briefly then hides — messages send silently in background.", font=("Helvetica", 9), bg="#fff3cd", fg="#856404", pady=4, anchor="w").pack(fill="x")

        cc_frame = tk.Frame(self.root, bg="#f0f0f0")
        cc_frame.pack(fill="x", padx=15, pady=(12, 0))
        tk.Label(cc_frame, text="Country Code:", font=("Helvetica", 10, "bold"), bg="#f0f0f0").pack(side="left")
        self.cc_var = tk.StringVar()
        self.cc_map = {label: code for label, code in COUNTRY_CODES}
        labels = [label for label, _ in COUNTRY_CODES]
        self.cc_dropdown = ttk.Combobox(cc_frame, textvariable=self.cc_var, values=labels, state="readonly", font=("Helvetica", 10), width=28)
        self.cc_dropdown.current(0)
        self.cc_dropdown.pack(side="left", padx=(10, 0))

        tk.Label(self.root, text="Contacts File:", font=("Helvetica", 10, "bold"), bg="#f0f0f0", anchor="w").pack(fill="x", padx=15, pady=(10, 2))
        file_frame = tk.Frame(self.root, bg="#f0f0f0")
        file_frame.pack(fill="x", padx=15)
        tk.Button(file_frame, text="Load Contacts File", command=self.load_contacts_file, bg="#0078d7", fg="white", relief="flat", cursor="hand2").pack(side="left")
        self.csv_path_var = tk.StringVar(value=f"Default: {os.path.basename(CONTACTS_CSV_PATH)}")
        tk.Label(file_frame, textvariable=self.csv_path_var, font=("Helvetica", 9), bg="#f0f0f0", anchor="w").pack(side="left", padx=10)

        tk.Label(self.root, text="Select Contacts (Ctrl/Shift for multiple):", font=("Helvetica", 10), bg="#f0f0f0", anchor="w").pack(fill="x", padx=15, pady=(10, 2))
        list_frame = tk.Frame(self.root, bg="#f0f0f0")
        list_frame.pack(fill="both", padx=15, pady=(0, 5), expand=False)

        self.contact_listbox = tk.Listbox(list_frame, selectmode="extended", height=12, width=60, exportselection=False)
        self.contact_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.contact_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.contact_listbox.yview)

        self.selected_phone_var = tk.StringVar(value="Selected contacts: 0")
        tk.Label(self.root, textvariable=self.selected_phone_var, font=("Helvetica", 10), bg="#f0f0f0", anchor="w").pack(fill="x", padx=15, pady=(5, 0))

        tk.Button(self.root, text="Update Selected Count", command=self.on_contact_select, bg="#6c757d", fg="white", relief="flat").pack(padx=15, pady=(4, 0), anchor="w")

        tk.Label(self.root, text="Message:", font=("Helvetica", 10), bg="#f0f0f0", anchor="w").pack(fill="x", padx=15, pady=(10, 2))
        self.message_box = scrolledtext.ScrolledText(self.root, height=5, font=("Courier", 11), relief="solid", bd=1)
        self.message_box.pack(fill="x", padx=15)

        self.send_btn = tk.Button(self.root, text="▶  Send Messages", font=("Helvetica", 12, "bold"), bg="#25D366", fg="white", activebackground="#128C7E", relief="flat", pady=8, cursor="hand2", command=self.start_sending)
        self.send_btn.pack(fill="x", padx=15, pady=10)

        prog_frame = tk.Frame(self.root, bg="#f0f0f0")
        prog_frame.pack(fill="x", padx=15)
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var, maximum=100, length=400, mode="determinate")
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_label = tk.Label(prog_frame, text="0%", font=("Helvetica", 10, "bold"), bg="#f0f0f0", fg="#075E54", width=6)
        self.progress_label.pack(side="left", padx=(8, 0))
        self.stats_label = tk.Label(self.root, text="", font=("Helvetica", 9), bg="#f0f0f0", fg="#555")
        self.stats_label.pack(fill="x", padx=15, pady=(2, 0))

        tk.Label(self.root, text="Log:", font=("Helvetica", 10), bg="#f0f0f0", anchor="w").pack(fill="x", padx=15, pady=(8, 2))
        self.log_box = scrolledtext.ScrolledText(self.root, height=10, font=("Courier", 10), bg="#1e1e1e", fg="#00ff88", relief="solid", bd=1, state="disabled")
        self.log_box.pack(fill="both", padx=15, pady=(0, 15), expand=True)

        if os.path.exists(CONTACTS_CSV_PATH):
            self.load_contacts_from_path(CONTACTS_CSV_PATH, silent=True)

    def log(self, message):
        def _u():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, _u)

    def update_progress(self, pct, done, total, success, failed):
        def _u():
            self.progress_var.set(pct)
            self.progress_label.config(text=f"{pct}%")
            self.stats_label.config(text=f"Processed: {done}/{total}   ✓ Sent: {success}   ✗ Failed: {failed}")
        self.root.after(0, _u)

    def on_done(self):
        def _u():
            self.send_btn.configure(state="normal", text="▶  Send Messages")
        self.root.after(0, _u)

    def _detect_columns(self, fieldnames):
        lowered = {h.lower().strip(): h for h in fieldnames or []}
        name_candidates = ["name", "first name", "given name", "full name"]
        phone_candidates = ["phone", "phone 1 - value", "phone number", "mobile"]
        name_col = next((lowered[c] for c in name_candidates if c in lowered), None)
        phone_col = next((lowered[c] for c in phone_candidates if c in lowered), None)
        return name_col, phone_col

    def load_contacts_from_path(self, path, silent=False):
        if not os.path.exists(path):
            messagebox.showerror("File not found", f"Cannot find:\n{path}")
            return False

        contacts = {}
        names = []

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                messagebox.showerror("CSV format error", "CSV file has no header row.")
                return False

            name_col, phone_col = self._detect_columns(reader.fieldnames)
            if not name_col or not phone_col:
                messagebox.showerror("CSV format error", f"Could not find name/phone columns.\nHeaders found:\n{reader.fieldnames}")
                return False

            for row in reader:
                name = (row.get(name_col) or "").strip()
                phone = (row.get(phone_col) or "").strip()
                phone = normalize_phone(phone)
                if name and phone:
                    if name not in contacts:
                        names.append(name)
                    contacts[name] = phone

        self.contacts = contacts
        self.contact_names = names
        self.contact_listbox.delete(0, "end")
        for name in self.contact_names:
            self.contact_listbox.insert("end", name)
        self.on_contact_select()

        self.csv_path_var.set(os.path.basename(path))
        if not silent:
            messagebox.showinfo("Loaded", f"Loaded {len(self.contact_names)} contacts from CSV.")
        self.log(f"[INFO] Loaded {len(self.contact_names)} contacts from {os.path.basename(path)}")
        return True

    def load_contacts_file(self):
        path = filedialog.askopenfilename(
            initialdir=os.path.dirname(os.path.abspath(__file__)),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        self.load_contacts_from_path(path)

    def on_contact_select(self, event=None):
        selected_indexes = self.contact_listbox.curselection()
        self.selected_phone_var.set(f"Selected contacts: {len(selected_indexes)}")

    def start_sending(self):
        message = self.message_box.get("1.0", "end").strip()
        cc_label = self.cc_var.get()
        country_code = self.cc_map.get(cc_label, "91")
        selected_indexes = self.contact_listbox.curselection()

        if not selected_indexes:
            messagebox.showwarning("Missing Input", "Please select at least one contact.")
            return

        if not message:
            messagebox.showwarning("Missing Input", "Please enter a message.")
            return

        selected_names = [self.contact_listbox.get(i) for i in selected_indexes]
        selected_phones = []

        for name in selected_names:
            phone = self.contacts.get(name)
            if phone:
                if not phone.startswith("+"):
                    phone = clean_phone(phone, country_code)
                selected_phones.append(phone)

        if not selected_phones:
            messagebox.showerror("Error", "No valid phone numbers found for selected contacts.")
            return

        confirm = messagebox.askyesno(
            "Confirm",
            f"Send to {len(selected_phones)} selected contact(s)?\n\n"
            f"\"{message[:80]}{'...' if len(message) > 80 else ''}\""
        )
        if not confirm:
            return

        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        self.stats_label.config(text="")
        self.send_btn.configure(state="disabled", text="Sending...")
        self.log(f"[START] Sending to {len(selected_phones)} contact(s) | Country: +{country_code}")

        threading.Thread(
            target=run_sending,
            args=(selected_phones, message, country_code, self.log, self.update_progress, self.on_done),
            daemon=True
        ).start()


if __name__ == "__main__":
    errors = []
    if not os.path.exists(CHROMEDRIVER_PATH):
        errors.append(f"chromedriver.exe not found:\n{CHROMEDRIVER_PATH}")
    if not os.path.exists(CHROMIUM_PATH):
        errors.append(f"Chromium not found:\n{CHROMIUM_PATH}")
    if not os.path.exists(PROFILE_PATH):
        errors.append(f"WhatsApp profile not found:\n{PROFILE_PATH}\nRun login_once.py first!")
    if not os.path.exists(CONTACTS_CSV_PATH):
        errors.append(f"Contacts CSV not found:\n{CONTACTS_CSV_PATH}")

    if errors:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Setup Error", "\n\n".join(errors))
        root.destroy()
    else:
        root = tk.Tk()
        app = App(root)
        root.mainloop()