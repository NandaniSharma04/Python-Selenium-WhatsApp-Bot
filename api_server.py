from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from backend import (
    load_contacts,
    run_sending,
    COUNTRY_CODES,
)

app = FastAPI()

# Allow React (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SendRequest(BaseModel):
    phones: List[str]
    message: str
    countryCode: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/contacts")
def get_contacts():
    contacts = load_contacts()
    return {"contacts": contacts, "countryCodes": COUNTRY_CODES}

@app.post("/send")
def send_messages(body: SendRequest):
    # simple log and progress callbacks for now
    def log_func(msg: str):
        print(msg)

    def progress_func(pct, done, total, success, failed):
        print(f"{pct}% {done}/{total} ✓{success} ✗{failed}")

    def done_func():
        print("Done sending")

    # run_sending is blocking; later we can run it in a thread
    run_sending(body.phones, body.message, body.countryCode, log_func, progress_func, done_func)
    return {"status": "completed"}