# Drawing attention to the new library and Premium (2026-10-03)

The new resources library was invisible from the landing page and the pricing page: worksheets, the Workbook PDF, guided programs, daily reflections, guided audio and the family course. Before this change, Premium was sold almost entirely on Anchor.

## Shipped in this change

- **Landing page (`apps/core/templates/core/index.html`):**
  - A "New" tag in the hero that jumps to the toolkit.
  - A **Your recovery toolkit** section with six cards: audio, programs, reflections, worksheets, the family course and Craving SOS. Each card has an honest Free / Premium label.
  - A **Free vs Premium** section that reads live prices from `SubscriptionPlan`. The prices are `stripe-only`, so they're hidden in the iOS app.
  - The JSON-LD FAQ now mentions the library.
- **Pricing page:** both the Free and Premium lists now include the library. The Supporter seat mentions the family course.
- **Progress-home upsell card:** the copy names the library. It used to promise "unlimited Anchor coaching", which was wrong (it's 20 a day). The trial line only shows to people who are eligible for a trial.
- **"What's new" popup** (`templates/partials/_whats_new.html`, plus the `apps.core.context_processors.whats_new` processor). Details in the next section.
- **GA4:** `view_promotion` and `select_promotion` events, each with a `promotion_id`.
  - Landing page: `landing_*`.
  - Popup: `whats_new_*`.
  - Upsell card: `progress_upsell_card`.
  - In GA, go to Reports, then Monetization, then Promotions, or build an Exploration on `promotion_id`.

## Pop-ups: what we found, and the rules we chose

- **No pop-ups for anonymous visitors from search.**
  - Google demotes mobile pages that cover content with an interstitial as the visitor arrives from search.
  - Organic search is our weakest channel, so a landing-page pop-up would cost more than it earns.
  - Visitors get inline sections and the hero "New" tag instead.
- **Members get one popup per announcement, on calm pages only:**
  - It only appears on the progress home, the social feed and the resources hub.
  - It never appears on crisis, SOS, Anchor, check-in, checkout, onboarding or login pages. Someone mid-craving should never be interrupted by an ad.
  - It doesn't appear in a member's first day, since onboarding covers that.
  - It doesn't appear to Supporter-tier family members.
  - It waits about 2 seconds, and doesn't open over another dialog or while someone is typing.
  - It's shown once per browser per `WHATS_NEW_VERSION`. To announce the next batch of features, bump that constant.
- **Premium members** get a "here's what's included" version with no upsell. This is retention, not sales.
- **iOS (App Store Guideline 3.1.1):** the popup shows no web price. Its button goes to the pricing page, which shows the Apple purchase flow inside the app.
- **Found while auditing (not changed here):**
  - The two trial banners in `templates/base.html` (`#trialBanner` and `.trial-countdown-banner`) show "$9.99/mo" and "Upgrade Now" with no `stripe-only` class, so they appear in the iOS app.
  - Showing a web price in the app is a Guideline 3.1 review risk.
  - Suggested fix: add `stripe-only`, plus an `iap-only` variant that calls `MRPIAP.showPurchaseUI()`.

## More ideas, ranked by likely impact per effort

### Do next (small, high intent)

1. **A one-time announcement email to all members.**
   - The members have never been told about any of this. Use the Resend broadcast or a `send_feature_announcement` management command with a dry run.
   - Subject idea: "We built you a recovery toolkit". Lead with the free craving audio, which is a gift, then mention Premium.
   - This is probably the single biggest lever for the current members.
2. **The upgrade moment at the end of the free days.**
   - When someone finishes day 7 of First 30 Days, or day 3 of a track, show a celebration card: "You finished week one. Keep going: 23 lessons left."
   - The trial button sits on the card. This is the highest-intent point in the whole product.
3. **A "Library" link in the main nav with a "New" dot.**
   - The library is currently three clicks deep, under Tools, then Recovery Resources.
   - A top-level link, or a bottom-tab item in the app, makes it part of the daily loop.
4. **A one-time push notification to app users.**
   - Push already works on both Android (FCM) and iOS (APNs). Example: "New: press play when a craving hits. Guided audio is here, free."
   - Point it at the free audio, not at Premium, so it reads as help rather than an ad.
5. **Audio previews.**
   - Locked Premium sessions could play their first 60 seconds, then fade into "Keep listening with Premium". Hearing the voice sells it better than a lock icon.

### In the product, tied to what the person is doing

6. **After a struggling or high-craving check-in:** offer the free urge-surfing audio, with Anchor, as one-tap help.
   - This is a retention play, never an upsell. Never show Premium here.
7. **Evening:** at the member's local 9 PM, offer "Evening check-out" (free members get a 1-minute preview). The per-user timezone support already exists.
8. **The weekly digest email:** add a "This week's reflection + one guided session" block. It brings people back to the library weekly.
9. **The trial-ending email:** personalize it with what they actually used during the trial. "You listened to 4 sessions and finished 6 lessons. Keep them."
10. **Journal:** after an entry, suggest the related worksheet. For example, a resentment entry leads to the Thought Record.

### Pricing and offers (talk these through first)

11. **A founding-member annual offer for the current members.**
    - A time-limited Stripe coupon, for example 40% off the first year of annual.
    - Show it in the announcement email and the popup, and make it `stripe-only`.
12. **A reverse trial for new signups.**
    - Give 7 days of Premium with no card, then drop to Free with a summary of what they used. Test it with the existing A/B system (`apps/accounts/ab_testing.py`) against the card trial.
    - Reverse trials usually convert better for content products.
13. **Gift Premium:** let a Supporter, or anyone, buy a member a month or a year. Family members are motivated buyers.

### Getting new people in (acquisition)

14. **Shareable reflection cards:** a branded image of today's reading for Instagram and TikTok, linking back to the free reading. Daily content without daily writing.
15. **SEO pages for the audio and programs.**
    - The audio pages are already in the sitemap. Add blog posts that link to them, for example "Free guided urge-surfing audio" and "What to do in the first 30 days sober".
    - Submit them in Search Console.
16. **Milestone posts in the feed:** an opt-in "X finished First 30 Days 🎉". This is social proof that sparks curiosity in the feed.
17. **App Store refresh:** new screenshots of audio and programs, plus "What's New" text for the iOS build that adds background audio.
