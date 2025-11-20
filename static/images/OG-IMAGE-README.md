# Open Graph Image Required

## Missing File: og-image.png

The site references `static/images/og-image.png` in the base template for social media sharing (Facebook, Twitter, LinkedIn, etc.). This file is currently missing and needs to be created.

## Requirements

- **Filename:** `og-image.png`
- **Location:** `/static/images/og-image.png`
- **Dimensions:** 1200 x 630 pixels (Facebook/Twitter recommended size)
- **Format:** PNG or JPG
- **File Size:** Under 5MB (ideally under 300KB for fast loading)

## Content Suggestions

The image should include:
- MyRecoveryPal logo
- Tagline: "Heal Together, Grow Together" or "Your Recovery Support Community"
- Visual elements that represent community, support, and healing
- Brand colors: #1e4d8b (dark blue), #4db8e8 (light blue), #52b788 (green)

## Design Tools

You can create this image using:
- **Canva** (free, easy): canva.com
- **Figma** (free, professional): figma.com
- **Adobe Express** (free): adobe.com/express
- **Photoshop/Illustrator** (professional)

## Template/Size

Use these dimensions in your design tool:
- Width: 1200px
- Height: 630px
- Aspect ratio: 1.91:1

## Why It Matters

When someone shares your site on social media, this image appears as the preview. A good OG image:
- Increases click-through rates from social posts
- Makes your links look professional
- Helps with brand recognition
- Improves social media engagement

## Current Fallback

Until this image is created, the site uses the default from `seo_defaults` context processor. Social shares will still work but may not look as polished.

## After Creating

1. Save the image as `og-image.png`
2. Upload to `/static/images/`
3. Run `python manage.py collectstatic` to copy to production
4. Test with Facebook Debugger: https://developers.facebook.com/tools/debug/
5. Test with Twitter Card Validator: https://cards-dev.twitter.com/validator
