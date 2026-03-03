# WidgetKit Sobriety Counter Widget — Design

**Date:** 2026-03-03
**Goal:** Native iOS home screen widget showing days sober + milestone progress. Strongest proof the Capacitor app is NOT just a website wrapper (Apple Guideline 4.2).

## Architecture

A native Swift WidgetKit extension that displays the user's sobriety counter on their iOS home screen. Data flows from the web app → custom Capacitor plugin → App Group UserDefaults → widget. Since `sobriety_date` is a fixed date, the widget calculates days sober locally — no network requests needed after initial sync.

## Components

### 1. Custom Capacitor Plugin (`WidgetBridge.swift`, ~40 lines)
- Exposes `setWidgetData({ sobrietyDate: "2024-01-15" })` to JavaScript
- Writes to `UserDefaults(suiteName: "group.com.myrecoverypal.app")`
- Calls `WidgetCenter.shared.reloadAllTimelines()` to refresh widget
- Also exposes `clearWidgetData()` for logout/account deletion

### 2. JavaScript Bridge (`capacitor-widget.js`, ~30 lines)
- Calls `WidgetBridge.setWidgetData()` after login and on social feed load
- Reads sobriety_date from the page's existing Django context (already rendered in profile/feed)
- Calls `clearWidgetData()` on logout

### 3. Widget Extension (`SobrietyCounterWidget/`)
- **Small widget**: Days sober number (large), "days sober" label, next milestone text
- **Medium widget**: Days sober + circular progress ring toward next milestone + milestone label + app branding
- **TimelineProvider**: Generates entries every hour (recalculates days at midnight). Uses `.atEnd` reload policy.
- **Visual**: App's blue gradient (`#1e4d8b` → `#2d6cb5`), white text, SF Pro rounded numbers

### 4. App Group (`group.com.myrecoverypal.app`)
- Added to both main app + widget extension entitlements
- Shared UserDefaults stores: `sobriety_date` (ISO string), `display_name` (optional)

## Data Flow

```
Login/Feed load → JS reads sobriety_date from page → WidgetBridge.setWidgetData()
    → App Group UserDefaults → Widget TimelineProvider reads date
    → Calculates days sober locally → Renders SwiftUI view
```

## Milestone Logic

Same as Django `get_sobriety_milestone`:
```
Milestones: 1, 7, 14, 30, 60, 90, 180, 365, 730, 1095...
Progress = days since last milestone / days to next milestone
```

## Tap Behavior

Tapping widget opens the app (deep link to social feed — the default landing).

## Key Files

| File | Purpose |
|------|---------|
| `ios/App/App/WidgetBridge.swift` | Capacitor plugin — JS-to-native bridge |
| `ios/App/SobrietyCounterWidget/SobrietyCounterWidget.swift` | Widget extension entry point + TimelineProvider |
| `ios/App/SobrietyCounterWidget/SobrietyCounterWidgetViews.swift` | SwiftUI views for small + medium |
| `ios/App/SobrietyCounterWidget/Info.plist` | Widget extension config |
| `static/js/capacitor-widget.js` | JS bridge — syncs sobriety_date to native |
| `ios/App/App/App.entitlements` | Add App Group |
| `ios/App/SobrietyCounterWidget/SobrietyCounterWidget.entitlements` | Widget App Group |

## Bundle IDs

- Main app: `com.myrecoverypal.app`
- Widget extension: `com.myrecoverypal.app.SobrietyCounterWidget`
- App Group: `group.com.myrecoverypal.app`
