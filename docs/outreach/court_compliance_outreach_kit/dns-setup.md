# Email Authentication Setup — SPF, DKIM, DMARC

All three are DNS TXT records added at your domain host (GoDaddy, Namecheap,
Cloudflare, Google Domains). As of 2026, Gmail/Yahoo **reject** bulk mail that
is missing these. Set all three up and verify before your first real send.

> **Strongly recommended:** do cold prospecting from a **separate domain**
> (e.g. `getmyrecoverypal.com`), set up all three records there, and warm it for
> ~2 weeks before sending volume. A spam complaint then can't burn your primary
> inbox at `myrecoverypal.com`.

Exact record values depend on your sending platform. Examples below cover Google
Workspace and generic cold-email tools (Instantly, Smartlead, SendGrid).

## Step 1 — SPF (authorizes sending servers)
One TXT record per domain. Merge ALL senders into a single record.

- Host/Name: `@` (root domain)
- Type: `TXT`
- Google Workspace: `v=spf1 include:_spf.google.com ~all`
- Google + another tool: `v=spf1 include:_spf.google.com include:sendgrid.net ~all`

Rules: only ONE SPF record total; keep `include:` count under ~10.

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

## Step 3 — DMARC (failure policy + reports)
Add AFTER SPF and DKIM verify as PASS.

- Host/Name: `_dmarc`
- Type: `TXT`
- Start (monitor only): `v=DMARC1; p=none; rua=mailto:dmarc@myrecoverypal.com; fo=1`
- After 2-4 weeks of clean reports: tighten to `p=quarantine`, then `p=reject`.

## Step 4 — Verify
Send a test to a Gmail address -> open it -> three-dot menu -> **Show original**.
You want **PASS** on SPF, DKIM, and DMARC. Or use MXToolbox / dmarcian / Google
Check MX. DNS changes propagate in 1-48 hrs (usually under an hour).
