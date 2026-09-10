# Cold-outreach wave 6 — Indiana — drafted 2026-09-10

Ten B2B emails to **verified, published Indiana inboxes**. No overlap with waves
1–4 (Illinois) or wave 5 (Missouri).

## The find that makes this wave different

Indiana publishes a **live, machine-readable directory of every certified court
alcohol and drug program in the state — with each program director's name, title,
county, phone and email**:

```
https://courtapps.in.gov/reports/api/courtaddirectory
```

It's served as a PDF generated on request; the copy pulled this session is
stamped **"Indiana Court Alcohol and Drug Program Directory - September 2026"**
and lists ~40 counties. Under IC 12-23-14, the Indiana Office of Court Services
certifies these programs; they do the screening, assessment, referral and case
management for court-involved people with alcohol and drug issues — which means
**the people in that directory are the exact people who receive AA/NA attendance
documentation**, and the state hands you their email addresses.

No Illinois or Missouri equivalent turned up in earlier waves. Re-pull the URL
before a future wave rather than trusting this snapshot.

**Terminology:** Indiana says **OWI**, not DUI or DWI. Using the wrong acronym
marks you as an out-of-state vendor in the first sentence.

**Before sending:** check Django admin → Accounts → Cold-outreach opt-outs.
Send individually from `ryan@trymyrecoverypal.com`, 20–30/day across all waves,
no attachments on first touch. One follow-up at ~7 days, then stop.

| # | Prospect | Contact | Inbox | Why | Verified on |
|---|----------|---------|-------|-----|-------------|
| 1 | Indiana Office of Court Services | Jamie Bergacs, Program Certification | `jamie.bergacs@courts.in.gov` | Certifies both the ~40 A&D programs *and* the problem-solving courts. Highest leverage in the state | in.gov/courts/iocs/cadp/ |
| 2 | Indiana Council of Community Mental Health Centers | Lee Ann Jordan, Dir. Communications & Membership | `ljordan@indianacouncil.org` | Association of the CMHCs that treat these clients; membership director is the right door for a member mention | indianacouncil.org/about-us/our-leadership/ |
| 3 | Marion Superior Court A&D Services (Indianapolis) | Sharyl F. Ramsey | `sharyl.ramsey@indy.gov` | Largest county program in Indiana | IOCS directory, Sep 2026 |
| 4 | LADOS Division 1, Lake Superior Court (Crown Point) | Yasmin Whittemore | `whittyx@lakecountyin.org` | Second-largest county; Chicago-metro volume | IOCS directory, Sep 2026 |
| 5 | Allen Superior Court Criminal Div. Services (Fort Wayne) | Jeffrey R. Yoder | `jeff.yoder@allensuperiorcourt.us` | Third-largest; also runs Allen County Drug Court | IOCS directory, Sep 2026 |
| 6 | Hamilton County CARE (Noblesville) | Emily Boles | `emily.boles@hamiltoncounty.in.gov` | Fast-growing suburban county, well-resourced program | IOCS directory, Sep 2026 |
| 7 | St. Joseph County Court Substance Abuse Program (South Bend) | Kristin Fee | `KFee@sjcindiana.gov` | Northern Indiana hub | IOCS directory, Sep 2026 |
| 8 | Vanderburgh County DADS (Evansville) | Megan Collins | `macollins@vanderburghgov.org` | Deferral-services model — clients are pre-conviction and highly motivated to document compliance | IOCS directory, Sep 2026 |
| 9 | PACT / Porter County A&D Offender Services (Valparaiso) | Tammy O'Neill | `tammy.oneill@pactchangeslives.com` | Nonprofit contractor running a county program — private-sector decision speed | IOCS directory, Sep 2026 |
| 10 | Our Place Services / Washington County A&D Program | MeriBeth Adams-Wolf | `meribeth@ourplaceservices.org` | Nonprofit operator (New Albany) running the county program; Louisville-metro caseload | IOCS directory, Sep 2026 |

**Spares from the same directory (use if one bounces):** Monroe/Bloomington —
Dorthy Perrotte `dperrotte@co.monroe.in.us` · Tippecanoe/Lafayette — David
Hullinger `dhullinger@tippecanoe.in.gov` · Johnson — Shannon Barrick
`sbarrick@johnsoncounty.in.gov` · Hendricks — Chad Boruff
`cboruff@co.hendricks.in.us` · Delaware/Muncie — Catherine Greenwalt
`cgreenwalt@co.delaware.in.us` · Howard/Kokomo — Laura Rood
`laura.rood@howardcountyin.gov` · LaPorte — Kelly Johnson
`kjohnson@laporteco.in.gov` · Morgan — Brian Foley `bfoley@morgancounty.in.gov` ·
Wabash — Danelle Aspinwall `daspinwall@wabashcounty.in.gov` · Warrick — Laura
Campbell `lcampbell@warrickcounty.gov` · Knox/Vincennes — Joseph Williams
`jwilliams@knoxcounty.in.gov` · Dearborn — Amber Hohman
`ahohman@dearborncounty.in.gov`.

⚠️ **Three directory entries use personal addresses** — Cass
(`snyder4314@comcast.net`), Henry (`adec.inc.1001@gmail.com`), LaGrange
(`kharcenters@gmail.com`). They're officially published, but a cold pitch to a
personal inbox reads worse. Save them for last, if at all.

⚠️ **Found but do NOT use:** `diane.mains@courts.in.gov` — appears in search
results and older IOCS pages as the CADP contact, but the **current** cadp page
lists Jamie Bergacs and Lora Moeller instead. Assume Mains is stale.

**Checked this session, no published inbox:** INARR / Indiana Recovery Network
(both programs of Mental Health America of Indiana — 317-638-3501, phone only on
their contact pages), Allen County Drug Court page, Whitley County A&D,
Monroe County program page (the directory has the email; the county page
doesn't).

---

## 1. Indiana Office of Court Services — Jamie Bergacs

**To:** jamie.bergacs@courts.in.gov
**Subject:** Verifying meeting-attendance documentation — worth showing certified programs?

Hi Jamie,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing to IOCS rather than to individual counties because the
problem I want to describe is one the certified programs seem to share.

When someone hands a court alcohol and drug program a handwritten AA or NA
attendance card, there's usually no fast way to tell whether the signature is
real.

We built something for that. The person logs each meeting they attend and
generates a PDF attendance report carrying a cryptographic fingerprint. Whoever
holds that printout can paste the fingerprint at a public page on our site and
confirm in about 30 seconds — no account, no cost, no case details exposed — that
the document hasn't been altered since it was generated. Entries that are only
self-reported are labeled as self-reported right on the report, so it never
claims more certainty than it has. It's program-neutral by design (AA, NA, CA,
SMART Recovery, Refuge, LifeRing and secular options), since courts can't
constitutionally require a 12-step program.

How verification works, on one page:
https://www.myrecoverypal.com/for-probation-officers/

Two questions:

1. Is this the kind of thing IOCS would consider mentioning to certified programs
   or problem-solving courts — a training session, a newsletter, a resource list,
   whatever format you'd think appropriate?
2. What would an Indiana program need to see before treating a report like this
   as acceptable documentation?

Participants subscribe individually ($29.99/mo). There's no cost, contract, or
procurement on the court side, and nothing for your office to administer. I'd
rather build to what Indiana programs actually need than guess.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=jamie.bergacs@courts.in.gov

---

## 2. Indiana Council of Community Mental Health Centers — Lee Ann Jordan

**To:** ljordan@indianacouncil.org
**Subject:** Free aftercare tool for your member centers (and a court-report piece)

Hi Lee Ann,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing to the Council because what we built addresses a problem
your member centers all describe the same way: once someone completes a program,
nobody hears anything until they're in trouble again.

We made a free tool for that gap. Clients who opt in use the app day to day —
check-ins, mood and craving tracking, a recovery community — and staff get a
dashboard showing who's disengaging: no check-in in five days, cravings climbing,
mood bottoming out. A digest lands Monday morning with the names worth a phone
call that week.

Two things I'd want to know in your members' position, so I'll say them up front:

- Staff see engagement and risk trends only — never journal entries, never raw
  check-in notes. Personal writing stays private, permanently.
- Only clients who accept an invite appear at all. Nobody is enrolled without
  agreeing to it.

It's genuinely free, and a center can set it up itself at
https://www.myrecoverypal.com/accounts/facility/signup/ — a work email verifies
the account.

Separately, for members serving OWI and court-referred clients: those clients can
generate a court-ready PDF of their meeting attendance carrying a fingerprint the
court verifies at a public link. That piece is a subscription the client buys
directly ($29.99/mo) — nothing the center pays for or administers.
https://www.myrecoverypal.com/court-ordered-meeting-tracker/

Is either worth a mention to members — newsletter, member resource list, or
however you'd normally handle it? Happy to answer questions first, and equally
happy to hear why it wouldn't fit.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=ljordan@indianacouncil.org

---

## 3. Marion Superior Court A&D Services — Sharyl F. Ramsey

**To:** sharyl.ramsey@indy.gov
**Subject:** Question about how your program verifies AA/NA attendance cards

Hi Sharyl,

Quick question from someone building tools in this space: when someone in the
Marion County program hands your staff a paper AA or NA sign-in card, how do you
know it's real?

I built MyRecoveryPal, a recovery app, and one feature was designed for exactly
that. The person logs each meeting they attend and generates a PDF attendance
report carrying a cryptographic fingerprint. Your staff can paste that
fingerprint at a public page on our site and confirm in about 30 seconds — no
account, no cost to the court, no case details exposed — that the document hasn't
been altered since it was generated. Entries that are only self-reported are
labeled as self-reported right on the report, so it never claims to prove more
than it does. It's program-neutral (AA, NA, CA, SMART Recovery, Refuge, LifeRing,
secular).

One page on how verification works:
https://www.myrecoverypal.com/for-probation-officers/

Yours is the biggest program in the state, so if it wouldn't work at Marion's
volume, it probably doesn't work anywhere. Would a report like this be acceptable
documentation for your program? And if not, what would it need first?

Participants subscribe individually ($29.99/mo) — no cost, contract, or install
on the court's side. A "no, because…" is genuinely useful to me.

Thanks for the work you do,

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=sharyl.ramsey@indy.gov

---

## 4. LADOS Division 1, Lake Superior Court — Yasmin Whittemore

**To:** whittyx@lakecountyin.org
**Subject:** A faster way to confirm meeting-attendance cards are real

Hi Yasmin,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing because of one piece of paperwork LADOS deals with
constantly: the handwritten AA or NA attendance card, which nobody can verify
after the fact.

We built a better version of that record. The person logs each meeting they
attend and generates a PDF attendance report for any date range. Every report
carries a cryptographic fingerprint your staff can paste at a public page on our
site to confirm, in about 30 seconds, that the document hasn't been altered since
it was generated — no account, no cost, no case details exposed. Entries that are
only self-reported are labeled that way on the report itself; it doesn't pretend
to prove someone sat in the room, only that the record is intact.

How verification works, on one page:
https://www.myrecoverypal.com/for-probation-officers/

Participants subscribe individually ($29.99/mo). Nothing for Lake County to buy,
install, or administer.

Would documentation like this be acceptable in Division 1 — and if not, what
would have to change? I'd rather build to what Indiana programs need than guess
from out of state.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=whittyx@lakecountyin.org

---

## 5. Allen Superior Court Criminal Division Services — Jeff Yoder

**To:** jeff.yoder@allensuperiorcourt.us
**Subject:** Verifying meeting attendance for A&D and drug court participants

Hi Jeff,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing because Allen County runs both a certified alcohol and drug
program and a drug court — so your staff are on the receiving end of a lot of
handwritten meeting cards, from people at very different stages of supervision.

We built a cleaner record for that. The participant logs each meeting they attend
and generates a PDF attendance report for any date range — say, exactly the
period a phase requires. Each report carries a cryptographic fingerprint your
staff can paste at a public page on our site and confirm in about 30 seconds — no
account, no cost, no case details exposed — that the document hasn't been altered
since it was generated. Self-reported entries are flagged as self-reported on the
face of the report, so it never overclaims. It's program-neutral (AA, NA, CA,
SMART Recovery, Refuge, LifeRing, secular), which matters when a participant
objects to 12-step attendance.

One page on how verification works:
https://www.myrecoverypal.com/for-probation-officers/

Participants subscribe individually ($29.99/mo); nothing for the court to buy or
administer.

Would your team accept a report like this? And if there's a reason it wouldn't
survive a review hearing in Allen County, that's exactly what I'd like to hear.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=jeff.yoder@allensuperiorcourt.us

---

## 6. Hamilton County CARE — Emily Boles

**To:** emily.boles@hamiltoncounty.in.gov
**Subject:** Meeting-attendance reports your team can verify in 30 seconds

Hi Emily,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. Quick question about one specific piece of paperwork: when a CARE
participant turns in a signed AA or NA card, is there any practical way for your
staff to confirm it's genuine?

That's the gap we built for. The participant logs each meeting they attend and
generates a PDF attendance report carrying a cryptographic fingerprint. Your
staff paste that fingerprint at a public page on our site and get a confirmation
in about 30 seconds — no account, no cost, no case details exposed — that the
document hasn't been altered since it was generated. Entries that are only
self-reported are labeled as such on the report, so it never claims more than it
can back up. Program-neutral across AA, NA, CA, SMART Recovery, Refuge, LifeRing
and secular meetings.

How verification works: https://www.myrecoverypal.com/for-probation-officers/

Participants subscribe individually ($29.99/mo). No cost or contract on the
county's side, and nothing to install.

Would a report like this be acceptable documentation for CARE? If it's close but
not quite, I'd rather hear what's missing than keep guessing.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=emily.boles@hamiltoncounty.in.gov

---

## 7. St. Joseph County Court Substance Abuse Program — Kristin Fee

**To:** KFee@sjcindiana.gov
**Subject:** Spotting altered meeting-attendance cards

Hi Kristin,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing about the paper AA/NA attendance card — the piece of
documentation that everyone in your position receives constantly and nobody can
actually verify.

The participant logs each meeting they attend in our app and generates a PDF
attendance report for any date range. Each report carries a cryptographic
fingerprint your staff can paste at a public page on our site and confirm in
about 30 seconds — no account, no cost, no case details exposed — that the
document hasn't been altered since it was generated. Entries that are only
self-reported are labeled as self-reported right on the report, so it never
claims more certainty than it has. It's program-neutral (AA, NA, CA, SMART
Recovery, Refuge, LifeRing, secular), since a court can't constitutionally
require a 12-step program.

A one-page explanation of how the verification works:
https://www.myrecoverypal.com/for-probation-officers/

Participants subscribe individually ($29.99/mo) — nothing for St. Joseph County
to buy or administer.

Would your program accept documentation like this? And if not — what would it
need first? An honest "no, because…" shapes what we build next.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=KFee@sjcindiana.gov

---

## 8. Vanderburgh County DADS — Megan Collins

**To:** macollins@vanderburghgov.org
**Subject:** Documentation for deferral clients that your office can verify

Hi Megan,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing because deferral is the setting where documentation matters
most — the client has a real incentive to prove compliance, and your office
carries the burden of deciding whether what they hand over is trustworthy.

We built for exactly that. The client logs each meeting they attend and generates
a PDF attendance report for whatever date range their agreement specifies. Each
report carries a cryptographic fingerprint your staff can paste at a public page
on our site and confirm in about 30 seconds — no account, no cost, no case
details exposed — that the document hasn't been altered since it was generated.
Entries that are only self-reported are labeled that way on the report itself, so
it never claims to prove attendance it can't. Program-neutral across AA, NA, CA,
SMART Recovery, Refuge, LifeRing and secular meetings.

How verification works: https://www.myrecoverypal.com/for-probation-officers/

Clients subscribe individually ($29.99/mo); nothing for DADS to buy or
administer.

Would a report like this be acceptable for a deferral file? And if there's a
reason it wouldn't be, I'd genuinely like to hear it.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=macollins@vanderburghgov.org

---

## 9. PACT — Porter County A&D Offender Services — Tammy O'Neill

**To:** tammy.oneill@pactchangeslives.com
**Subject:** Meeting-attendance reports your staff can verify independently

Hi Tammy,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing because PACT sits in an interesting spot — you run the
county's alcohol and drug program, so you both set the documentation requirement
and have to judge whether what comes back is real.

The handwritten meeting card is the weak link there. We built the alternative:
the person logs each meeting they attend and generates a PDF attendance report
for any date range. Each report carries a cryptographic fingerprint your staff
can paste at a public page on our site and confirm in about 30 seconds — no
account, no cost — that the document hasn't been altered since it was generated.
Entries that are only self-reported are flagged as self-reported on the report,
so it never overclaims. It's program-neutral (AA, NA, CA, SMART Recovery, Refuge,
LifeRing, secular).

One page on how verification works:
https://www.myrecoverypal.com/for-probation-officers/

Clients subscribe individually ($29.99/mo) — nothing for PACT to buy, bill, or
administer.

Two questions: would your staff accept a report like this, and what would it need
before you'd hand it to a client as an option? You move faster than a county
office, so your read on it is worth a lot to me.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=tammy.oneill@pactchangeslives.com

---

## 10. Our Place Services — Washington County A&D Program — MeriBeth Adams-Wolf

**To:** meribeth@ourplaceservices.org
**Subject:** Court-ready meeting documentation for your A&D program clients

Hi MeriBeth,

I'm Ryan Pate, founder of MyRecoveryPal, a recovery app built in central
Illinois. I'm writing because Our Place runs both recovery services and a
certified court alcohol and drug program — which means you see the meeting-card
problem from both ends: clients who genuinely go and can't prove it, and cards
that come back looking a little too convenient.

We built the record that fixes that. The client logs each meeting they attend and
generates a PDF attendance report for any date range. Each report carries a
cryptographic fingerprint that your staff — or a court, or a PO — can paste at a
public page on our site and confirm in about 30 seconds, with no account and no
cost, that the document hasn't been altered since it was generated. Entries that
are only self-reported are labeled as such right on the report. It covers AA, NA,
CA, SMART Recovery, Refuge, LifeRing and secular meetings, so it holds up for
clients who object to 12-step attendance.

How verification works: https://www.myrecoverypal.com/for-probation-officers/

Clients subscribe individually ($29.99/mo); nothing for Our Place to buy or
administer.

Would this be worth offering to clients who leave with a meeting requirement? And
if it wouldn't work for the courts you serve, telling me why would genuinely
help.

Ryan Pate
Founder, MyRecoveryPal
ryan@trymyrecoverypal.com

--
You received this email as part of outreach to court and recovery-support
professionals. MyRecoveryPal, 1350 Wyndmoor Dr, Rochester, IL 62563.
Prefer not to hear from us? Unsubscribe here:
https://www.myrecoverypal.com/email/cold-outreach-unsubscribe/?email=meribeth@ourplaceservices.org

---

## Suggested send order

1. **#9 PACT** and **#10 Our Place** — nonprofit operators, fastest decisions,
   lowest institutional friction. Good pressure test before the big counties.
2. **#3, #5, #6, #7, #8** — the county programs. Highest-intent audience in the
   whole outreach effort: they receive these cards every week.
3. **#4 Lake County** — largest after Marion, but a big bureaucracy; expect slow.
4. **#1 IOCS** — the leverage play. Worth sending early, but the answer will be
   shaped by whether any county program has said yes yet, so a reply from #3–#8
   first strengthens it. If one county responds well, mention it (by role, not
   name) when writing IOCS.
5. **#2 Indiana Council** — different pitch entirely (aftercare dashboard);
   send independently of the court thread.

Log every send: date, name, org, variant, response (none / no / interested /
objection). Objections are product input — chair signatures and QR check-in are
the most likely asks, and both are already on the Phase 2 deferred list.
