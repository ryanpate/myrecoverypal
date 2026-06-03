# Cold-outreach emails — Court Compliance feature

Three branded HTML email variants for promoting the Court Compliance tier to
recovery-support facilities, plus a working opt-out flow.

## The three variants

| File | Audience | Angle |
|------|----------|-------|
| `sober-living.html` | Sober living / recovery homes | Less staff paperwork verifying residents' attendance cards |
| `rehab-treatment.html` | Rehab / treatment centers | Smoother discharge handoff; fewer attendance-letter requests on clinical staff |
| `court-liaison.html` | Court / drug-court / probation officers | Tamper-evident, publicly verifiable reports — no more forged cards |

Each variant also has a **plain-text version** (`.txt`) with the subject line at
the top. Send both: the HTML as the rich version and the `.txt` as the
`text/plain` alternative part. Most email tools (and Gmail's "plain text mode")
let you paste both; including a text alternative improves deliverability and
covers recipients whose clients strip HTML. Fill the same `{{FIRST_NAME}}` and
`{{RECIPIENT_EMAIL}}` tokens in both.

All use the **B2C-referral model**: the facility pays nothing; their
clients/residents subscribe individually ($19.99/mo). The facility's incentive
is less paperwork — an easy "yes."

## Before sending — fill in these placeholders

Each file contains two merge tokens. Replace them per recipient:

- `{{FIRST_NAME}}` — the recipient's first name (e.g. "Maria"). If unknown, use
  "there".
- `{{RECIPIENT_EMAIL}}` — the recipient's email address. This pre-fills the
  unsubscribe form so they can opt out in one click. If you can't merge it,
  delete `?email={{RECIPIENT_EMAIL}}` from the unsubscribe link — the opt-out
  page also works with a manually typed address.

## How the opt-out works

The "Unsubscribe here" link points to:

```
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=<their address>
```

Clicking it opens a branded page with their email pre-filled. When they submit,
the address is added to the **Cold-outreach opt-out** suppression list. You can
view and export that list in Django admin under
**Accounts → Cold-outreach opt-outs**.

**Always check that list before sending a new batch** so you don't email anyone
who has opted out.

## Sending best practices (important)

1. **Send from `ryan@myrecoverypal.com`** (a real personal inbox), not a
   `noreply@` address or bulk tool. Replies should reach you.
2. **Small batches** — 20–30/day. Large blasts can flag your sending domain and
   break your transactional/retention email (which runs through Resend).
3. **CAN-SPAM** — every email already includes the required physical mailing
   address and a working opt-out. Don't remove them. Keep subject lines honest.
4. **Personalize one line** per recipient if you can — naming the facility's
   specific paperwork pain beats a polished generic email.

## Suggested subject lines (A/B test)

**Sober living**
- Less paperwork verifying your residents' meeting attendance
- A free tool that documents your residents' court-ordered meetings

**Rehab / treatment**
- Court-ready meeting tracking for clients after discharge
- Fewer attendance-letter requests on your clinical team

**Court / probation liaison**
- Verifiable meeting-attendance reports for court-ordered clients
- A faster way to confirm attendance cards are real
