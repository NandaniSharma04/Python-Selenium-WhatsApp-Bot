import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog

from backend import (
    CHROMEDRIVER_PATH,
    CHROMIUM_PATH,
    PROFILE_PATH,
    CONTACTS_CSV_PATH,
    COUNTRY_CODES,
    clean_phone,
    run_sending,
    load_contacts,
)