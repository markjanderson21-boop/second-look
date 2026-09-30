"""Document intake: PDF text extraction + AI structured extraction.

Runs in clearly-labeled DEMO MODE until ANTHROPIC_API_KEY is set.
In demo mode the uploaded file is ignored and sample data is returned,
so the full flow can be clicked through without a key.
"""
import json
import os

import pdfplumber

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def demo_mode() -> bool:
    return not os.getenv("ANTHROPIC_API_KEY")


def extract_text(pdf_path: str) -> str:
    """Pull raw text out of a PDF. Returns "" if it can't be read."""
    parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
    except Exception:
        return ""
    return "\n".join(parts)


def _claude_json(system: str, prompt: str, text: str) -> dict:
    from anthropic import Anthropic

    client = Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system,
        messages=[{
            "role": "user",
            "content": prompt + "\n\nDOCUMENT TEXT:\n" + text[:60000],
        }],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


# ---------------------------------------------------------------- 401(k)

DEMO_401K = {
    "account_type": "401(k)",
    "custodian": "Sample statement",
    "as_of_date": None,
    "total_value": 412350.00,
    "holdings": [
        {"name": "Company Stock Fund", "value": 148446.00,
         "expense_ratio": 0.02, "category": "Company stock"},
        {"name": "Growth Fund of America", "value": 115458.00,
         "expense_ratio": 0.62, "category": "US large-cap growth"},
        {"name": "S&P 500 Index Fund", "value": 82470.00,
         "expense_ratio": 0.015, "category": "US large-cap blend"},
        {"name": "Stable Value Fund", "value": 65976.00,
         "expense_ratio": 0.35, "category": "Cash / stable value"},
    ],
}

_401K_SYSTEM = (
    "You extract structured data from retirement account statements. "
    "Return ONLY valid JSON, no other text."
)
_401K_PROMPT = """Extract the holdings from this retirement account statement.
Return JSON exactly like this:
{
  "account_type": "401(k) | 403(b) | IRA | ...",
  "custodian": "name or null",
  "as_of_date": "statement date or null",
  "total_value": number or null,
  "holdings": [
    {"name": "fund name", "value": number,
     "expense_ratio": number as a percent (e.g. 0.62 means 0.62%) or null,
     "category": "short category like 'US large-cap', 'Bonds', 'Cash / stable value', 'Company stock'"}
  ]
}
Use null for anything not visible. Numbers only, no dollar signs or commas."""


def analyze_401k(text: str):
    """Returns (data_dict, demo_bool)."""
    if demo_mode() or not text.strip():
        return DEMO_401K, True
    try:
        return _claude_json(_401K_SYSTEM, _401K_PROMPT, text), False
    except Exception:
        return DEMO_401K, True


# ---------------------------------------------------------------- Estate

DEMO_ESTATE = [
    {"filename": "will.pdf",
     "doc_type": "will",
     "label": "Last Will and Testament",
     "signed_date": "2016-03-14",
     "key_people": ["Mark Anderson (person making the will)",
                    "Amber Anderson (executor)"],
     "notes": ""},
    {"filename": "trust.pdf",
     "doc_type": "trust",
     "label": "Revocable Living Trust",
     "signed_date": "2016-03-14",
     "key_people": ["Mark Anderson (grantor)", "Amber Anderson (successor trustee)"],
     "notes": ""},
    {"filename": "healthcare-proxy.pdf",
     "doc_type": "healthcare_proxy",
     "label": "Healthcare Proxy",
     "signed_date": "2016-03-14",
     "key_people": ["Amber Anderson (healthcare agent)"],
     "notes": ""},
]

_ESTATE_SYSTEM = (
    "You read estate planning documents and summarize them in plain terms. "
    "Return ONLY valid JSON, no other text."
)
_ESTATE_PROMPT = """Read this estate planning document and return JSON exactly like this:
{
  "doc_type": "one of: will, trust, financial_power_of_attorney, healthcare_proxy, beneficiary_designation, other",
  "label": "plain-English title, e.g. 'Last Will and Testament'",
  "signed_date": "YYYY-MM-DD or null",
  "key_people": ["Name (role)", ...],
  "notes": "one short sentence on anything important, or empty string"
}"""


def analyze_estate(text: str, filename: str):
    """Returns (info_dict, demo_bool) for one document."""
    if demo_mode() or not text.strip():
        return {"filename": filename, "doc_type": "other",
                "label": "Unreadable document", "signed_date": None,
                "key_people": [], "notes": "We could not read this file."}, True
    try:
        info = _claude_json(_ESTATE_SYSTEM, _ESTATE_PROMPT, text)
        info["filename"] = filename
        return info, False
    except Exception:
        return {"filename": filename, "doc_type": "other",
                "label": "Unreadable document", "signed_date": None,
                "key_people": [], "notes": "We could not read this file."}, True


def demo_estate_docs():
    return [dict(d) for d in DEMO_ESTATE]
