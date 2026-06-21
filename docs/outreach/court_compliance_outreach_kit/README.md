# Court Compliance Outreach Kit

Mass-email campaign promoting MyRecoveryPal's **Court Compliance** feature to
Recovery Houses, Lawyers, Rehab Centers, and DUI/Drug-Court services.

## Quick start
1. **Read `dns-setup.md` first** and set up SPF / DKIM / DMARC. Required in 2026
   or Gmail/Yahoo will reject your mail.
2. Pick your audience folder version (4 of each):
   - **Cold outreach** -> use `emails-plaintext/*.txt` in a cold-email tool
     (Instantly, Smartlead, Apollo).
   - **Warm / opted-in** -> use `emails-html/*.html` in your ESP (paste into the
     HTML/code editor).
3. Replace merge fields: `{{first_name}}`, `{{company}}`, `{{unsubscribe_link}}`,
   and the `[Your mailing address...]` placeholder (legally required).
4. Send a test to Gmail, "Show original", confirm SPF/DKIM/DMARC = PASS, then send.

## Contents
- `emails-html/` — 4 designed, send-ready HTML emails (table-based, inline CSS).
- `emails-plaintext/` — 4 plain-text cold versions with subject lines.
- `dns-setup.md` — SPF / DKIM / DMARC step-by-step.
- `CLAUDE.md` — full context for an AI coding agent (editing rules, brand, tech notes).

## Cold vs. warm — important
Send **plain-text** to cold lists (better deliverability + reply rates for B2B).
Reserve the **HTML** versions for warm/opted-in contacts. Blasting HTML to a cold
list trips spam filters.
