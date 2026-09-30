"""Plain-English rules engine.

Takes the structured data from extract.py and produces findings written
for a non-financial audience. Every finding has:
  level: "good" | "watch" | "review"
  title: short headline
  detail: what we saw, with numbers
  meaning: what it means in plain English

These are educational observations, not advice. Thresholds are simple
and conservative on purpose.
"""
from datetime import date

CASH_CATEGORIES = {"cash", "cash / stable value", "stable value",
                   "money market", "money-market"}


def _money(n):
    return f"${n:,.0f}"


# ---------------------------------------------------------------- 401(k)

def check_401k(data):
    flags = []
    holdings = [h for h in data.get("holdings", []) if h.get("value")]
    total = sum(h["value"] for h in holdings) or data.get("total_value") or 0

    def pct(v):
        return (v / total * 100) if total else 0

    # ---- Fees: asset-weighted expense ratio (stored as e.g. 0.62 = 0.62%)
    if total and holdings:
        w_er = sum((h.get("expense_ratio") or 0) * h["value"]
                   for h in holdings) / total
        yearly = w_er / 100 * total
        if w_er <= 0.30:
            flags.append({
                "level": "good",
                "title": "Your fees look reasonable",
                "detail": f"About {w_er:.2f}% per year ({_money(yearly)} on {_money(total)}).",
                "meaning": "Fees quietly eat into growth over time, so low fees are "
                           "a genuine advantage. Nothing to fix here.",
            })
        elif w_er <= 0.60:
            flags.append({
                "level": "watch",
                "title": "Fees are a little high",
                "detail": f"About {w_er:.2f}% per year ({_money(yearly)} on {_money(total)}).",
                "meaning": "This isn't an emergency, but cheaper options may exist "
                           "in your plan. Worth a look when you have a moment.",
            })
        else:
            flags.append({
                "level": "review",
                "title": "Fees are worth a closer look",
                "detail": f"About {w_er:.2f}% per year ({_money(yearly)} on {_money(total)}).",
                "meaning": "Over 20 or 30 years, high fees can cost far more than "
                           "most people expect. This deserves a conversation.",
            })

        pricey = [h for h in holdings if (h.get("expense_ratio") or 0) >= 0.75]
        if pricey:
            names = ", ".join(h["name"] for h in pricey[:3])
            flags.append({
                "level": "watch",
                "title": "One fund costs much more than the rest",
                "detail": f"{names}: {pricey[0]['expense_ratio']:.2f}% per year.",
                "meaning": "Sometimes an expensive fund earns its keep, and sometimes "
                           "a cheaper fund does the same job. Worth asking about.",
            })

    # ---- Concentration: a lot riding on one investment
    for h in holdings:
        if pct(h["value"]) >= 25:
            is_company = "company" in h["name"].lower() or "employer" in h["name"].lower()
            flags.append({
                "level": "review",
                "title": "A lot is riding on one investment",
                "detail": f"{h['name']}: {_money(h['value'])} ({pct(h['value']):.0f}% of the account).",
                "meaning": ("When it's your employer's stock, your paycheck and your "
                            "retirement move together — that's double exposure. "
                            if is_company else
                            "If that one investment stumbles, the whole account feels it. "
                            ) + "Spreading things out lowers that risk.",
            })
            break

    # ---- Cash drag: money sitting still
    cash = sum(h["value"] for h in holdings
               if (h.get("category") or "").lower() in CASH_CATEGORIES)
    if total and pct(cash) >= 15:
        flags.append({
            "level": "watch",
            "title": "A sizable chunk is sitting still",
            "detail": f"{_money(cash)} ({pct(cash):.0f}%) is in cash-like options.",
            "meaning": "Cash feels safe, but over long periods it usually grows far "
                       "slower than invested money. Some cash is fine — this much "
                       "may be working against you.",
        })

    # ---- Diversification: how many baskets
    cats = {(h.get("category") or "Other").lower() for h in holdings
            if (h.get("category") or "").lower() not in CASH_CATEGORIES}
    if holdings and len(cats) < 3:
        flags.append({
            "level": "watch",
            "title": "Your eggs are in few baskets",
            "detail": f"We see about {len(cats)} type(s) of investments besides cash.",
            "meaning": "Different types of investments take turns doing well. "
                       "Owning a few kinds smooths out the ride.",
        })

    if not flags:
        flags.append({
            "level": "good",
            "title": "Nothing jumped out",
            "detail": "Based on what we could read, this account looks sensible.",
            "meaning": "That doesn't mean it's perfect — just that the common "
                       "trouble spots weren't visible here.",
        })
    return flags


# ---------------------------------------------------------------- Estate

REQUIRED_DOCS = [
    ("will", "A will",
     "Names who gets what, and who wraps things up. Without one, the state decides."),
    ("financial_power_of_attorney", "Financial power of attorney",
     "Lets someone you trust pay bills and handle money if you can't."),
    ("healthcare_proxy", "Healthcare proxy",
     "Lets someone you trust make medical decisions if you can't."),
    ("beneficiary_designation", "Beneficiary designations",
     "The forms that say who gets your retirement accounts and life insurance. "
     "These override your will, so stale ones cause real problems."),
]

STALE_YEARS = 5


def _years_old(signed_date):
    try:
        y, m, d = map(int, str(signed_date).split("-"))
        delta = date.today() - date(y, m, d)
        return delta.days / 365.25
    except Exception:
        return None


def check_estate(docs):
    """docs: list of {doc_type, label, signed_date, key_people, notes}."""
    by_type = {}
    for d in docs:
        by_type.setdefault(d.get("doc_type"), []).append(d)

    checklist = []
    for doc_type, name, why in REQUIRED_DOCS:
        found = by_type.get(doc_type, [])
        if not found:
            checklist.append({
                "status": "missing",
                "title": f"Missing: {name}",
                "detail": why,
                "action": "Ask about getting this in place.",
            })
            continue
        doc = found[0]
        age = _years_old(doc.get("signed_date"))
        if age is not None and age >= STALE_YEARS:
            checklist.append({
                "status": "stale",
                "title": f"Out of date: {doc.get('label') or name}",
                "detail": f"Signed {doc.get('signed_date')} — about {age:.0f} years ago. {why}",
                "action": "Laws change and life changes. Have it reviewed.",
            })
        else:
            when = f" (signed {doc.get('signed_date')})" if doc.get("signed_date") else ""
            checklist.append({
                "status": "ok",
                "title": f"Found: {doc.get('label') or name}{when}",
                "detail": why,
                "action": "",
            })

    # Trust funding reminder — the most common trust mistake
    if "trust" in by_type:
        checklist.append({
            "status": "watch",
            "title": "Check: is your trust funded?",
            "detail": "A trust only works for accounts and property actually moved "
                      "into it. Many trusts sit empty for years.",
            "action": "Confirm your accounts were retitled into the trust.",
        })

    return checklist
