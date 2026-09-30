import os
import shutil
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .extract import (analyze_401k, analyze_estate, demo_estate_docs,
                      demo_mode, extract_text)
from .rules import check_401k, check_estate

load_dotenv()

BASE = Path(__file__).parent
UPLOAD_DIR = Path("/tmp/second-look-uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ADVISOR_NAME = os.getenv("ADVISOR_NAME", "Mark Anderson")
ADVISOR_PHONE = os.getenv("ADVISOR_PHONE", "")
BOOKING_URL = os.getenv("BOOKING_URL", "")

app = FastAPI(title="Second Look", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


def ctx(**kw):
    d = {"advisor_name": ADVISOR_NAME,
         "advisor_phone": ADVISOR_PHONE, "booking_url": BOOKING_URL,
         "demo": demo_mode()}
    d.update(kw)
    return d


def render(request: Request, name: str, **kw):
    return templates.TemplateResponse(request, name, {"request": request, **ctx(**kw)})


def _save(upload: UploadFile) -> Path:
    safe = "".join(c for c in (upload.filename or "upload.pdf")
                   if c.isalnum() or c in "._-") or "upload.pdf"
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe}"
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return render(request, "index.html")


@app.get("/checkup/retirement", response_class=HTMLResponse)
def retirement_form(request: Request):
    return render(request, "upload_401k.html")


@app.post("/checkup/retirement", response_class=HTMLResponse)
async def retirement_report(request: Request,
                            statement: UploadFile = File(...)):
    path = _save(statement)
    text = extract_text(str(path))
    path.unlink(missing_ok=True)
    data, demo = analyze_401k(text)
    flags = check_401k(data)
    holdings = data.get("holdings", [])
    total = sum(h.get("value") or 0 for h in holdings) or data.get("total_value") or 0
    w_er = (sum((h.get("expense_ratio") or 0) * (h.get("value") or 0)
                for h in holdings) / total) if total else 0
    return render(request, "report_401k.html", data=data, flags=flags,
                holdings=holdings, total=total, w_er=w_er,
                yearly=w_er / 100 * total, demo=demo)


@app.get("/checkup/estate", response_class=HTMLResponse)
def estate_form(request: Request):
    return render(request, "upload_estate.html")


@app.post("/checkup/estate", response_class=HTMLResponse)
async def estate_report(request: Request,
                        documents: list[UploadFile] = File(...)):
    docs = []
    any_demo = demo_mode()
    if any_demo:
        # Demo mode: show a finished sample report; uploaded files are ignored.
        docs = demo_estate_docs()
    else:
        for upload in documents:
            if not (upload.filename or "").strip():
                continue
            path = _save(upload)
            text = extract_text(str(path))
            path.unlink(missing_ok=True)
            info, doc_demo = analyze_estate(text, upload.filename)
            any_demo = any_demo or doc_demo
            docs.append(info)
    checklist = check_estate(docs)
    return render(request, "report_estate.html", docs=docs,
                checklist=checklist, demo=any_demo)


@app.get("/talk", response_class=HTMLResponse)
def talk(request: Request):
    return render(request, "book.html")
