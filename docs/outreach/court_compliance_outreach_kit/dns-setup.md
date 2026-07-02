# Email Authentication Setup — SPF, DKIM, DMARC

All three are DNS TXT records added at your domain host (GoDaddy, Namecheap,
Cloudflare, Squarespace). As of 2026, Gmail/Yahoo **reject** bulk mail that
is missing these. Set all three up and verify before your first real send.

> **Strongly recommended:** do cold prospecting from a **separate domain**
> (we use `trymyrecoverypal.com`), set up all three records there, and warm it for
> ~2 weeks before sending volume. A spam complaint then can't burn your primary
> inbox at `myrecoverypal.com`.

> **Our actual setup (do this once):** `trymyrecoverypal.com` was bought through
> the Google Workspace signup, so the registrar/DNS host is **Squarespace
> Domains** (Google's partner — manage DNS at `account.squarespace.com` ->
> Domains -> the domain -> DNS Settings). **Because the domain was purchased
> through Google, Workspace auto-populates SPF, DKIM, and MX for you.** When you
> open DNS Settings you'll already see, under *Custom records*:
> `TXT @ v=spf1 include:_spf.google.com ~all` and
> `TXT google._domainkey v=DKIM1; k=rsa; p=...`, plus `MX @ smtp.google.com`
> under *Google records*. So in practice the only record you add by hand is
> **DMARC**. Do NOT add a second SPF or DKIM — duplicates break authentication.

Exact record values depend on your sending platform. Steps below cover Google
Workspace and generic cold-email tools (Instantly, Smartlead, SendGrid). If your
domain was bought through Google, treat Steps 1-2 as "verify already present"
rather than "add."

## Step 1 — SPF (authorizes sending servers)
One TXT record per domain. Merge ALL senders into a single record.

- Host/Name: `@` (root domain)
- Type: `TXT`
- Google Workspace: `v=spf1 include:_spf.google.com ~all`
- Google + another tool: `v=spf1 include:_spf.google.com include:sendgrid.net ~all`

Rules: only ONE SPF record total; keep `include:` count under ~10.

> Google-purchased domains: this is **already present** — just confirm the value
> matches. Don't add a duplicate.

## Step 2 — DKIM (cryptographically signs mail)
Generate the key inside your sending platform, then publish what it gives you.

- Google Workspace: Admin console -> Apps -> Google Workspace -> Gmail ->
  *Authenticate email* -> Generate new record (2048-bit). It outputs:
  - Host/Name: `google._domainkey`
  - Type: `TXT`
  - Value: the long `v=DKIM1; k=rsa; p=...` string
  After publishing, wait ~1 hr then click **Start authentication**.
- Cold tools generate their own selector host (e.g. `s1._domainkey`). Publish
  exactly the host + value they provide.

> Google-purchased domains: the `google._domainkey` TXT record is **already
> published**. You still must flip it on: Admin -> Apps -> Google Workspace ->
> Gmail -> *Authenticate email* -> select the domain -> **Start authentication**.
> A published record alone doesn't mean Gmail is signing yet.

## Step 3 — DMARC (failure policy + reports)
The one record you almost always add by hand. Add AFTER SPF and DKIM verify as PASS.

- Host/Name: `_dmarc`
- Type: `TXT`
- Start (monitor only): `v=DMARC1; p=none; rua=mailto:ryan@trymyrecoverypal.com; fo=1`
- After 2-4 weeks of clean reports: tighten to `p=quarantine`, then `p=reject`.

> Point `rua=` at a mailbox on the **same domain** (e.g.
> `ryan@trymyrecoverypal.com`). Cross-domain reporting (e.g. an address at
> `myrecoverypal.com`) needs an extra authorization record at the receiving
> domain — not worth the hassle.

## Step 4 — Verify
Send a test to a Gmail address -> open it -> three-dot menu -> **Show original**.
You want **PASS** on SPF, DKIM, and DMARC. Or use MXToolbox / dmarcian / Google
Check MX. DNS changes propagate in 1-48 hrs (usually under an hour).
