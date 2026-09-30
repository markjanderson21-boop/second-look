# Second Look

A free retirement & estate checkup for prospects — in plain English.
Built super boomer-friendly: big text, high contrast, one clear action per screen,
no account needed, no jargon.

**How it works:** a visitor uploads a retirement statement → gets a plain-English
checkup (fees, concentration, cash drag, diversification) → ends on a
"Talk with Mark" booking page. Or they upload estate documents → get an organizer
showing what's found, what's missing, and what's out of date → same booking CTA.

## Run it

```bash
cd second-look
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in your values
.venv/bin/python -m uvicorn app.main:app --port 8123
```

Open http://localhost:8123.

## Demo mode vs. live mode

- **Without `ANTHROPIC_API_KEY`**: the app runs in clearly-labeled **demo mode**.
  Uploads are ignored and every report shows sample data with a "Sample report"
  banner, so the whole flow can be clicked through immediately.
- **With `ANTHROPIC_API_KEY` set**: uploaded PDFs are parsed and sent to the
  Claude API for structured extraction, then the rules engine builds the report.
  Set `ANTHROPIC_MODEL` if you want a different model.

## Configure the booking page

In `.env`:

```
ADVISOR_NAME=Mark Anderson
ADVISOR_PHONE=+15551234567
BOOKING_URL=https://calendly.com/your-link
```

The `/talk` page shows a call button and/or an online booking button from these.

## Project layout

```
app/
  main.py        # FastAPI app + routes
  extract.py     # PDF text extraction + AI structured extraction (or demo data)
  rules.py       # plain-English findings engine (fees, concentration, estate gaps)
  templates/     # Jinja2 pages — home, uploads, reports, booking
  static/style.css  # big-type, high-contrast styling
```

## Before this goes live — read this

1. **Compliance.** Talk to a compliance attorney before collecting real
   prospect documents. SEC marketing rule, state RIA requirements, and
   "educational information only — not advice" positioning all matter.
   The disclaimer footer is a starting point, not legal cover.
2. **Data security.** You're handling people's full financial lives. Encrypt
   uploads at rest, set a retention/deletion policy (the prototype deletes
   files right after parsing), and never email reports with PII.
3. **Human review.** Keep a human-in-the-loop step before any report reaches
   a prospect — quality control and a compliance safety net.

## Roadmap ideas

- Email capture before the report (with consent) so no lead is lost
- Save reports + CRM handoff (e.g., push to your existing system)
- More custodians' statement formats, tested against real PDFs
- Spanish-language version of the report pages
- Analytics: which findings drive the most bookings
