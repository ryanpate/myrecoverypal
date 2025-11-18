# iOS Safe Area Fix - Implementation Guide

This document explains the changes made to fix the iOS status bar/notch/Dynamic Island obstruction issue in your MyRecoveryPal mobile app.

## Problem

The iOS app was displaying content behind the status bar, camera notch, and Dynamic Island, making the top menu and other UI elements difficult to use.

## Solution Overview

We implemented iOS safe area support using CSS environment variables and updated the Capacitor configuration. This ensures content appears in the safe viewing area on all iPhone models.

## Changes Made

### 1. Capacitor Configuration (`capacitor.config.json`)

Added Status Bar plugin configuration:

```json
"StatusBar": {
  "style": "Light",
  "backgroundColor": "#1e4d8b",
  "overlaysWebView": false
}
```

- **style**: "Light" makes status bar icons white (good for dark backgrounds)
- **backgroundColor**: Matches your brand color
- **overlaysWebView**: false prevents overlay issues

### 2. Package Dependencies (`package.json`)

Added the Status Bar plugin:

```json
"@capacitor/status-bar": "^7.0.1"
```

### 3. Django Base Template (`templates/base.html`)

#### Viewport Meta Tag (Line 9)
Changed from:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
```

To:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
```

**Key addition**: `viewport-fit=cover` tells iOS to use the full screen including safe areas.

#### Status Bar Style (Line 11)
Changed from:
```html
<meta name="apple-mobile-web-app-status-bar-style" content="default">
```

To:
```html
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
```

This creates a modern translucent status bar effect.

#### CSS Safe Area Variables (Lines 148-152)
Added to `:root`:
```css
/* iOS Safe Area Insets - Critical for notch/Dynamic Island support */
--safe-area-inset-top: env(safe-area-inset-top);
--safe-area-inset-right: env(safe-area-inset-right);
--safe-area-inset-bottom: env(safe-area-inset-bottom);
--safe-area-inset-left: env(safe-area-inset-left);
```

These CSS variables automatically adjust based on the device's safe areas.

#### Body Padding (Lines 162-170)
Changed from:
```css
body {
    padding-top: 70px; /* Account for fixed nav */
}
```

To:
```css
body {
    padding-top: max(70px, calc(70px + var(--safe-area-inset-top)));
    /* Account for fixed nav + iOS safe area */
    padding-left: var(--safe-area-inset-left);
    padding-right: var(--safe-area-inset-right);
}
```

**Result**: Body content now starts below the navbar AND safe area.

#### Navigation Bar (Lines 661-674)
Added safe area padding:
```css
nav {
    position: fixed;
    top: 0;
    /* ... other styles ... */
    padding-top: var(--safe-area-inset-top);
    padding-left: var(--safe-area-inset-left);
    padding-right: var(--safe-area-inset-right);
}
```

**Result**: Top navbar now sits properly below the notch/status bar.

#### Mobile Bottom Navigation (Lines 963-982)
Added safe area padding for the home indicator:
```css
.mobile-bottom-nav {
    padding-bottom: max(4px, calc(4px + var(--safe-area-inset-bottom)));
    padding-left: var(--safe-area-inset-left);
    padding-right: var(--safe-area-inset-right);
    height: auto;
    min-height: 56px;
}
```

**Result**: Bottom navigation sits above the iPhone home indicator.

## Next Steps - What You Need to Do

### Step 1: Install the Status Bar Plugin

On your local machine, run:

```bash
cd /path/to/myrecoverypal
npm install
```

This installs the new `@capacitor/status-bar` plugin.

### Step 2: Sync Capacitor

```bash
npm run cap:sync
```

This copies the updated configuration to your iOS project.

### Step 3: Test in Xcode Simulator

```bash
npm run cap:open:ios
```

1. In Xcode, select an iPhone with a notch (iPhone 14 Pro, 15 Pro, etc.)
2. Click Run (▶)
3. The app should now display correctly with content below the status bar

### Step 4: Deploy Django Changes to Production

The template changes (`base.html`) need to be deployed to your production server:

```bash
# On your local machine
git add templates/base.html
git commit -m "Fix iOS safe area issues for mobile app"
git push origin main

# Then deploy to Railway (or your hosting platform)
# Railway auto-deploys on push, or use your deployment process
```

**Important**: The mobile app loads from https://www.myrecoverypal.com, so the template changes must be live on production for the app to see them.

### Step 5: Rebuild iOS App

After deploying to production:

1. Open Xcode: `npm run cap:open:ios`
2. Clean build folder: Product → Clean Build Folder (Cmd+Shift+K)
3. Run the app again
4. The app will now load the updated HTML from your production server

## How It Works

### CSS Environment Variables

iOS provides special CSS environment variables that represent the safe areas:

- `env(safe-area-inset-top)` - Space for status bar/notch (typically 47px on notched phones)
- `env(safe-area-inset-bottom)` - Space for home indicator (typically 34px)
- `env(safe-area-inset-left)` - Space for left edge (0 in portrait, varies in landscape)
- `env(safe-area-inset-right)` - Space for right edge (0 in portrait, varies in landscape)

### The `max()` Function

```css
padding-top: max(70px, calc(70px + var(--safe-area-inset-top)));
```

This ensures:
- On regular phones (no notch): Uses 70px
- On notched phones: Uses 70px + safe area (e.g., 70px + 47px = 117px)
- Always uses whichever is larger

## Testing Checklist

Test on these iPhone simulators:
- [ ] iPhone 15 Pro (Dynamic Island)
- [ ] iPhone 14 Pro (notch)
- [ ] iPhone SE (no notch)
- [ ] iPad (different safe areas)

Test these orientations:
- [ ] Portrait mode
- [ ] Landscape mode (safe areas appear on sides)

## Troubleshooting

### Content Still Behind Status Bar

**Cause**: Template changes not deployed to production
**Solution**: Deploy `base.html` to production server

### Status Bar Wrong Color

**Cause**: Capacitor not synced
**Solution**: Run `npm run cap:sync`

### Changes Not Appearing

**Cause**: Browser cache or old build
**Solution**:
```bash
# Clean and rebuild
npm run cap:sync
# In Xcode: Product → Clean Build Folder
# Then rebuild
```

### Works in Simulator but Not on Device

**Cause**: Need to reinstall the app
**Solution**: Delete app from device, then reinstall from Xcode

## Additional Resources

- [iOS Safe Area Guide](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)
- [Capacitor Status Bar Docs](https://capacitorjs.com/docs/apis/status-bar)
- [CSS env() Function](https://developer.mozilla.org/en-US/docs/Web/CSS/env)

## Support

If you encounter issues:
1. Check that production server has the updated templates
2. Verify `npm run cap:sync` completed successfully
3. Try cleaning Xcode build folder
4. Test on multiple iPhone models in simulator

---

**Quick Reference**:
- iOS safe area CSS: `env(safe-area-inset-top)`, `env(safe-area-inset-bottom)`, etc.
- Status bar plugin: `@capacitor/status-bar`
- Deploy to production for changes to appear in app
