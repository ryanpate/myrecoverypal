# Court Compliance Outreach Kit — MyRecoveryPal

Mass-outreach email campaign promoting the **Court Compliance** feature of
myrecoverypal.com to four B2B audiences. This folder is a self-contained asset
pack: drop it into a Claude Code project and use it to send, edit, A/B test, or
wire up the emails into a sending platform / sequence tool.

## What this promotes
The **Court-Ordered Meeting Tracker / Court Compliance** feature: people with
DUI / drug-court / probation requirements log AA/NA/SMART/secular meetings and
generate a **tamper-evident, publicly verifiable, court-ready PDF** attendance
report. Free for facilities — the individual client pays (B2C-referral model).

## Audiences (4 versions)
| Key | Audience | HTML | Plain-text |
|-----|----------|------|-----------|
| recovery-houses | Recovery Houses & Sober Living | emails-html/recovery-houses.html | emails-plaintext/recovery-houses.txt |
| lawyers | Defense & DUI Lawyers | emails-html/lawyers.html | emails-plaintext/lawyers.txt |
| rehab-centers | Rehab & Treatment Centers | emails-html/rehab-centers.html | emails-plaintext/rehab-centers.txt |
| dui-services | DUI & Drug-Court Services | emails-html/dui-services.html | emails-plaintext/dui-services.txt |

## Folder contents
```
court_compliance_outreach_kit/
├── CLAUDE.md              <- you are here (context for the coding agent)
├── README.md             <- human-readable quick start
├── dns-setup.md          <- SPF / DKIM / DMARC steps (do this before sending)
├── emails-html/          <- 4 designed, send-ready HTML emails (warm/opt-in)
└── emails-plaintext/     <- 4 plain-text cold versions (cold prospecting)
```

## Which format to send when
- **Plain-text (`emails-plaintext/`)** — use for COLD prospecting (lists you
  have no relationship with). Higher inbox placement + reply rates for B2B.
  Send from a real person via a cold-email tool (Instantly / Smartlead / Apollo).
- **HTML (`emails-html/`)** — use for WARM / opted-in contacts and newsletters.
  Do NOT blast HTML to a cold list — it trips spam filters.

## HTML email technical notes (when editing)
- Table-based layout, 600px max width, ALL styles inline. Do not refactor to
  external CSS or fl/grid — email clients (Outlook especially) won't render it.
- Brand: blue header `#1e4d8b` (gradient `#1e4d8b -> #0f2d56` as progressive
  enhancement; solid `#1e4d8b` is the Outlook fallback — keep both). Green CTA
  `#52b788`. Gold accent `#f5a623`. Body text `#2c3e50`. Footer text `#9ca3af`.
- Icons are unicode glyphs (gavel ⚖ U+2696, checkmark ✓ U+2713), NOT image or
  font-icon dependencies — keeps rendering bulletproof. Don't swap in <img> icons.
- Logo is a styled TEXT wordmark ("MyRecoveryPal"), not an image — avoids the
  blocked-image / hosted-asset problem. If you want the real logo mark instead,
  host a PNG publicly and swap the wordmark cell for an <img> (SVG won't render
  in Gmail/Outlook).
- CTA is a bulletproof table button (`<a>` inside a bgcolor `<td>` with
  border-radius). Safe to edit the href/label, keep the structure.

## Merge fields (replace before sending)
- `{{first_name}}` — recipient first name
- `{{company}}` — recipient org name (used in cold subject lines)
- `{{unsubscribe_link}}` — your platform's unsubscribe URL (HTML footer)
- `[Your mailing address, City, ST ZIP]` — REQUIRED by CAN-SPAM. Replace the
  literal placeholder in every HTML file's footer before sending.

## Voice & compliance (MyRecoveryPal brand)
- Warm, plain-spoken, peer-to-peer, founder voice ("I'm Ryan... I'll keep this
  short."). Never clinical, hype, or preachy.
- Program-neutral: always list AA, NA, SMART, LifeRing/Refuge & secular.
- No outcome promises / no medical claims. Always include physical address +
  working opt-out (CAN-SPAM). Cold B2B is permitted under CAN-SPAM with those.
- Primary CTA across all versions: get the recipient to FORWARD to a client who
  needs it (HTML) or reply for a sample PDF (cold plain-text).

## Before first send — checklist
1. Set up SPF + DKIM + DMARC (see `dns-setup.md`). Mandatory in 2026.
2. Use a separate sending domain for cold volume; warm it ~2 weeks.
3. Fill every merge field + the physical-address placeholder.
4. Cold = plain-text via cold-email tool; warm = HTML via ESP.
5. Send a test, "Show original" in Gmail, confirm SPF/DKIM/DMARC = PASS.

## Source design
The original branded mockup (all 4 emails side-by-side) lives one level up in the
project as `Court Compliance Outreach Emails.dc.html`.
