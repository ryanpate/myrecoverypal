# Resources Library Brainstorm: More Value, More Premium Conversions

**Date:** 2026-10-03
**Goal:** Make `/resources/` worth coming back to, and give the current ~423 members concrete reasons to upgrade to Premium ($4.99/mo, $29.99/yr).
**Status:** Brainstorm. Nothing is built yet. Open questions are at the bottom.

---

## 1. What's there today

Live at https://www.myrecoverypal.com/resources/: **12 resources in 5 categories, plus a professional-help search page.**

| Category | Resources |
|---|---|
| Educational | Post-Acute Withdrawal Syndrome (PAWS); Stages of Change |
| Support | Find a Recovery Support Group; How to Find a Sponsor |
| Tools | Coping Skills for Cravings (interactive + PDF); Daily Recovery Checklist (interactive + PDF); Relapse Prevention Plan |
| Wellness | Mindfulness & Meditation in Early Recovery; Sleep, Nutrition & Exercise |
| Family | Healthy Boundaries in Active Addiction; Support a Loved One Without Enabling |

**What already works:**
- Bookmarks, ratings, view/download counts, and per-user `InteractiveResourceProgress`.
- The strong free tools sit outside `/resources/`: Sobriety Calculator, Clean Time Calculator, Medallion Maker, Craving SOS, Relapse Prevention Plan builder, and Online AA Meetings.

**What's missing or broken:**
- **No resource is premium today.** The page's only call to action is "Create a free account". Nothing on it points to Premium.
- **Premium gating is broken.** In `resources/views.py:181` and `resources/views.py:229`, the check `not hasattr(request.user, 'has_premium')` is always true, and it redirects to `store:premium`, a URL that doesn't exist. If any resource were set to `access_level='premium'`, everyone would hit a 500 error, paying members included. `ResourceDetailView` also does no gating at all. This has to be fixed before anything can be premium.
- **Too little content.** Two items per category reads as an empty shelf, not a library.
- **Every substance gets the same content.** There is nothing specific to opioids, stimulants, cannabis or gambling, even though landing pages for those audiences already exist.
- **Resources are disconnected from the rest of the product.** They don't link to check-ins, the journal, Anchor, groups or the progress home.

## 2. What competitors do (summary)

| Competitor | What they sell |
|---|---|
| **Reframe** ($14–25/mo) | A 160-day daily neuroscience course, daily Zoom meetings, meditations, craving games, mocktail recipes |
| **Tempest / Monument** ($15–59/mo) | Live workshops, a moderated community, daily affirmations; a $399 4-week intensive |
| **I Am Sober Plus** ($9.99/mo) | Private accountability groups, multiple addictions, cloud backup; $0.99 "motivation packs" |
| **Sunnyside** ($99/yr) | Moderation goals, an AI coach, optional naltrexone |
| **SMART Recovery** | 14 free static PDF worksheets (ABC, Cost-Benefit, Change Plan, Urge Log, DENTS, Values, Lifestyle Balance); $11.95 handbooks |
| **Hazelden** | *Twenty-Four Hours a Day* daily reading app, $7.99 one-time |
| **Al-Anon** | A paid daily-reflection subscription |
| **CMC Foundation for Change** | The free "20-Minute Guide" for families, based on CRAFT and Invitation to Change |
| **Recovery Dharma, In The Rooms, Nomo** | Free, donation-funded: speaker tapes, meditations, daily readings |

**Gaps nobody fills well, and where MyRecoveryPal has an edge:**
1. **SMART/CBT worksheets you fill in and save, linked to your journal and reviewed by AI.** Everyone else offers static PDFs. We have the journal, check-ins and Anchor.
2. **Family/CRAFT content inside a recovery app.** We already have the Supporter seat and a "Support a Loved One" page.
3. **Daily readings that aren't tied to one program** (secular or multi-path). Hazelden and Al-Anon are 12-step; Recovery Dharma is Buddhist.
4. **Content for substances other than alcohol.** The paid programs are almost all about alcohol.
5. **Affordable live groups.** Elsewhere they cost $15–59/mo. We charge $4.99.
6. **Certificates and printable milestone documents.** No app offers them, and we already have the Medallion Maker and court PDFs.

## 3. Strategy: give away the teaser, charge for the "do it with me" layer

Rule of thumb: **reading and printing a blank copy is free. Saving it, personalizing it, getting guidance on it, and exporting it is Premium.**

- **Free content** does SEO and acquisition work. It should be indexable and long-form.
- **Premium content** builds on the person's own data and the social graph: their check-ins, journal, Anchor, groups and Supporter.
- Premium content can't easily be copied by a static website, so the $4.99 price holds up.

The model already supports this. `Resource.access_level` has free, registered and premium levels, and `InteractiveResourceProgress` stores progress. We'd add a preview/upsell state rather than a hard redirect.

## 4. Resource ideas

Effort: **S** = template/content only, **M** = a new view or model, **L** = a new subsystem.

### A. Interactive worksheet library (Premium anchor, highest priority) — M
Interactive, savable versions of proven exercises:
- Cost-Benefit Analysis
- ABC (Activating event → Belief → Consequence)
- Urge Log
- HALT check
- Hierarchy of Values
- Lifestyle Balance Wheel
- Change Plan
- Trigger Identification (a management command already exists for this)
- Gratitude inventory
- 10th-step nightly inventory (secular and 12-step versions)

Access:
- **Free:** read the instructions and download a blank PDF. This is good for SEO: "cost benefit analysis worksheet addiction", "HALT worksheet" and similar searches.
- **Premium:**
  - Fill it in and save it, with version history.
  - "Ask Anchor to review this", which passes the worksheet to the coach as context.
  - Auto-link the worksheet to that day's check-in.
  - Export your completed workbook as a PDF.

This is the clearest market gap, and it reuses the relapse-plan PDF pipeline.

### B. Guided day-by-day programs ("Paths") — M/L
Short daily lessons (3–5 minutes) with one action each day. The action can link to a worksheet, a check-in, a group post or a journal prompt.

Proposed programs:
- *First 30 Days*
- *90-Day Foundations*
- *Navigating PAWS*
- *Rebuilding Relationships*
- *Sober Holidays* (seasonal, starting with Thanksgiving through New Year's)
- Substance tracks: *Opioids*, *Stimulants*, *Cannabis*, *Gambling*, *Sober-Curious / Moderation*

Access:
- **Free:** Days 1–7 of every program.
- **Premium:** the full program, plus a cohort group whose members start the same week. We already have `RecoveryGroup` and `GroupChallenge`.

This is the Reframe and This Naked Mind model at a third of the price. The cohort is the social hook that keeps people coming back.

### C. Daily Reflection (multi-path) — S/M
One short reading a day, with a prompt, shown on the progress home next to the pledge.

Access:
- **Free:** today's reading.
- **Premium:** the full archive, favorites, an audio version, and "reflect in journal".

The readings must be original writing; 12-step texts are copyrighted. Hazelden and Al-Anon have shown people will pay for this format.

### D. Audio library — M
Guided urge surfing, body scan, sleep wind-down, and a 3-minute "craving reset". These extend Craving SOS.

Access:
- **Free:** 2–3 sessions.
- **Premium:** the full library, with offline caching in the app. This fits `capacitor-offline.js`.

### E. "My Recovery Workbook" export — S/M
A single PDF that combines:
- the user's saved worksheets
- their relapse prevention plan
- check-in trend charts
- milestones
- pledge reasons

People can bring it to a therapist, IOP or sponsor. **Premium.** It extends the existing "Relapse plan PDF & journal export" perk.

### F. Family & Friends Companion — M
- A CRAFT / Invitation-to-Change style mini-course: communication scripts, rewarding sober behavior, letting natural consequences happen, self-care.
- A boundary-setting worksheet.
- Guidance on "what to say at the first-month milestone".

Access:
- **Free:** the first lessons, which serve SEO for "how to help an alcoholic family member" searches.
- **Full course:** included with the Premium **Supporter seat**. This gives the paying member a reason to invite a loved one, and the loved one becomes a new acquisition channel.

### G. Live sessions — M (mostly operational)
A monthly live workshop or Q&A (Zoom or in-app) with:
- an invited counselor or certified peer recovery specialist, or
- member-led "Recovery Circles".

Recordings go into a Premium replay library. Competitors charge $15–59/mo for this.

### H. Certificates & printables — S
- **Free:** shareable milestone certificates (30/60/90/365 days) that link back to the site. This drives growth.
- **Premium:**
  - custom designs
  - a printable year-in-review
  - printable trackers (meeting log, 90-in-90 tracker)

The 90-in-90 tracker can also feed the Court tier funnel.

### I. Self-screening tools — S (free; acquisition)
- **AUDIT** (alcohol) and **DAST-10** (drugs) self-screens. These are public-domain WHO and NIDA instruments.
- A "Am I a functional alcoholic?" quiz that reuses the high-traffic blog content.

Every result routes to crisis or professional resources and a free signup. **Needs clinical framing:** "screening, not diagnosis."

### J. Life-rebuild toolkits — S each (free and Premium mixed)
- Money: savings → debt payoff plan
- Returning to work, and explaining a résumé gap
- Dating in sobriety
- Sober travel
- Saying "no thanks" scripts
- A party/wedding survival plan
- A mocktail recipe collection (free, good for SEO and Pinterest)

### K. Court Compliance resource pack — S (Court tier)
- How to talk to your probation officer
- A meeting-attendance etiquette guide for first-timers
- A program-neutral meeting directory explainer
- Letter templates for requesting secular meetings

This adds value to the $29.99 tier and reinforces its position.

### L. Community-sourced "What to expect" timeline — M (free)
Anonymized, aggregated mood and craving averages by day count, drawn from check-ins. For example: "Members at day 30–45 report cravings dropping 40%."

I Am Sober's version is free and used for acquisition, so ours should be too. It needs an aggregation floor (for example, a minimum of 20 users per data point) to protect privacy.

## 5. Proposed rollout

| Phase | Work | Why first |
|---|---|---|
| **0 (1 day)** | Fix the premium gating bug. Add a "preview + upgrade" state instead of a redirect. Add a Premium callout and a "New" badge on `/resources/`. Track `resource_upsell_view` → `upgrade` conversions with the existing `ResourceUsage` and `ABTestingService`. | Nothing can be premium until this is done. |
| **1 (1–2 weeks)** | **A** (6 worksheets to start), **E** (workbook export), and **H** (free milestone certificate). | These reuse existing systems and give the clearest Premium value. |
| **2 (2–4 weeks)** | **B**: *First 30 Days* plus one substance track, with cohort groups. **C**: daily reflection (30 readings to start). **I**: screening tools. | Builds a daily habit and an SEO surface. |
| **3** | **F** (family course), **D** (audio), **K** (court pack), **J** (toolkits). | Broadens the audience. |
| **4** | **G** (live sessions) and **L** (community timeline). | Needs operations, or more check-in volume. |

**Metrics to watch:**
- Resource → Premium trial start rate
- Worksheet saves per member
- Program day-7 → day-8 conversion (the paywall moment)
- Day-30 retention of program starters vs. non-starters

## 6. Open questions

1. **Clinical review.** Do we have, or want, a licensed counselor or peer specialist to review worksheet, screening and program content? This affects I, B and G.
2. **Content production.** Who writes the programs and daily readings? You, AI-drafted with your editing, or a freelance writer? This sets the pace of Phase 2.
3. **Gating appetite.** Should new resources be Premium-only, or follow the "free blank / Premium saved" split proposed above?
4. **Audience mix.** What substances do the 423 members mostly list? This decides which track ships first after *First 30 Days*.
5. **Live sessions.** Is anyone available to host a monthly session?
6. **Audio.** Your own voice, a hired narrator, or text-to-speech?
7. **Trial length.** The pricing page says "7-day free trial" but CLAUDE.md says 14 days. Which is correct? It changes how much of a program fits inside the trial.
