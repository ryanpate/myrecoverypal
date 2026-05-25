# WidgetKit Sobriety Counter Widget — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a native iOS WidgetKit sobriety counter (small + medium sizes) to prove the app is not just a website wrapper (Apple Guideline 4.2).

**Architecture:** Custom Capacitor plugin (`WidgetBridge`) writes `sobriety_date` from JS to App Group UserDefaults. Widget extension reads it, calculates days sober locally, and displays a SwiftUI view with progress toward next milestone. A Ruby script using the `xcodeproj` gem adds the widget extension target to the Xcode project (safer than manual `pbxproj` editing).

**Tech Stack:** Swift 5, SwiftUI, WidgetKit, Capacitor 7, Ruby `xcodeproj` gem (1.27.0)

---

### Task 1: Add App Group to main app entitlements

**Files:**
- Modify: `ios/App/App/App.entitlements`

**Step 1: Add App Group entitlement**

In `ios/App/App/App.entitlements`, the current content is:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>aps-environment</key>
	<string>production</string>
</dict>
</plist>
```

Replace with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>aps-environment</key>
	<string>production</string>
	<key>com.apple.security.application-groups</key>
	<array>
		<string>group.com.myrecoverypal.app</string>
	</array>
</dict>
</plist>
```

**Step 2: Commit**

```bash
git add ios/App/App/App.entitlements
git commit -m "feat: add App Group entitlement for widget data sharing"
```

---

### Task 2: Create the WidgetBridge Capacitor plugin (native Swift)

**Files:**
- Create: `ios/App/App/WidgetBridge.swift`
- Create: `ios/App/App/MyViewController.swift`
- Modify: `ios/App/App/Base.lproj/Main.storyboard` (change ViewController class)

The plugin needs:
1. A Swift `CAPPlugin` subclass that writes to App Group UserDefaults
2. A custom `CAPBridgeViewController` subclass that registers the plugin
3. The storyboard updated to use the custom ViewController

**Step 1: Create `ios/App/App/WidgetBridge.swift`**

```swift
import Foundation
import Capacitor
import WidgetKit

@objc(WidgetBridge)
public class WidgetBridge: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "WidgetBridge"
    public let jsName = "WidgetBridge"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "setWidgetData", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "clearWidgetData", returnType: CAPPluginReturnPromise)
    ]

    private let suiteName = "group.com.myrecoverypal.app"

    @objc func setWidgetData(_ call: CAPPluginCall) {
        guard let sobrietyDate = call.getString("sobrietyDate") else {
            call.reject("sobrietyDate is required")
            return
        }

        guard let defaults = UserDefaults(suiteName: suiteName) else {
            call.reject("Cannot access App Group")
            return
        }

        defaults.set(sobrietyDate, forKey: "sobriety_date")

        if let displayName = call.getString("displayName") {
            defaults.set(displayName, forKey: "display_name")
        }

        defaults.synchronize()

        if #available(iOS 14.0, *) {
            WidgetCenter.shared.reloadAllTimelines()
        }

        call.resolve(["success": true])
    }

    @objc func clearWidgetData(_ call: CAPPluginCall) {
        guard let defaults = UserDefaults(suiteName: suiteName) else {
            call.reject("Cannot access App Group")
            return
        }

        defaults.removeObject(forKey: "sobriety_date")
        defaults.removeObject(forKey: "display_name")
        defaults.synchronize()

        if #available(iOS 14.0, *) {
            WidgetCenter.shared.reloadAllTimelines()
        }

        call.resolve(["success": true])
    }
}
```

**Step 2: Create `ios/App/App/MyViewController.swift`**

This subclass registers our custom plugin with the Capacitor bridge:

```swift
import UIKit
import Capacitor

class MyViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(WidgetBridge())
    }
}
```

**Step 3: Update `ios/App/App/Base.lproj/Main.storyboard`**

Find the line:
```xml
<viewController id="BYZ-38-t0r" customClass="CAPBridgeViewController" customModule="Capacitor" sceneMemberID="viewController"/>
```

Replace with:
```xml
<viewController id="BYZ-38-t0r" customClass="MyViewController" customModule="App" sceneMemberID="viewController"/>
```

This tells the storyboard to use our custom ViewController instead of the default Capacitor one.

**Step 4: Commit**

```bash
git add ios/App/App/WidgetBridge.swift ios/App/App/MyViewController.swift ios/App/App/Base.lproj/Main.storyboard
git commit -m "feat: add WidgetBridge Capacitor plugin for widget data sharing

Custom plugin writes sobriety_date to App Group UserDefaults.
MyViewController registers the plugin with the Capacitor bridge."
```

---

### Task 3: Create the JavaScript bridge

**Files:**
- Create: `static/js/capacitor-widget.js`
- Modify: `templates/base.html` (add sobriety_date meta tag + script tag)

**Step 1: Create `static/js/capacitor-widget.js`**

```javascript
/**
 * Capacitor Widget Bridge
 * Syncs sobriety_date to native App Group UserDefaults for the iOS widget.
 * Exits immediately in browser -- zero impact on web.
 */
(function() {
    'use strict';

    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var WidgetBridge = window.Capacitor.registerPlugin('WidgetBridge');

    function syncWidgetData() {
        var meta = document.querySelector('meta[name="sobriety-date"]');
        var sobrietyDate = meta ? meta.getAttribute('content') : '';
        if (!sobrietyDate) return;

        var nameMeta = document.querySelector('meta[name="display-name"]');
        var displayName = nameMeta ? nameMeta.getAttribute('content') : '';

        WidgetBridge.setWidgetData({
            sobrietyDate: sobrietyDate,
            displayName: displayName
        }).catch(function(err) {
            console.warn('[Widget] sync error:', err);
        });
    }

    // Sync on page load
    if (document.readyState === 'complete') {
        syncWidgetData();
    } else {
        window.addEventListener('load', syncWidgetData);
    }

    // Re-sync when app returns to foreground
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            syncWidgetData();
        }
    });

    // Expose for logout cleanup
    window.MRPWidget = {
        clear: function() {
            return WidgetBridge.clearWidgetData().catch(function() {});
        }
    };
})();
```

**Step 2: Add sobriety_date meta tag to `templates/base.html`**

Find the existing meta tags area in the `<head>` section. After the RevenueCat API key meta tag (or any other meta tags near the top), add these lines. They must be inside `{% if user.is_authenticated %}`:

Find this pattern in `templates/base.html` inside the `<head>`:
```html
{% if user.is_authenticated %}
```

Inside that block (or create one if needed near the other meta tags), add:

```html
{% if user.is_authenticated and user.sobriety_date %}
<meta name="sobriety-date" content="{{ user.sobriety_date|date:'Y-m-d' }}">
<meta name="display-name" content="{{ user.get_short_name }}">
{% endif %}
```

**Step 3: Add script tag to `templates/base.html`**

Find the Capacitor script section (near line 1141 where `capacitor-native.js` is loaded). Add after the `capacitor-offline.js` script tag:

```html
<!-- Capacitor Widget Bridge (native app only) -->
<script src="{% static 'js/capacitor-widget.js' %}?v=20260303d"></script>
```

**Step 4: Commit**

```bash
git add static/js/capacitor-widget.js templates/base.html
git commit -m "feat: add JS widget bridge to sync sobriety_date to native

Reads sobriety_date from meta tag, sends to WidgetBridge plugin
which writes to App Group UserDefaults for the iOS widget."
```

---

### Task 4: Create widget extension files

**Files:**
- Create: `ios/App/SobrietyCounterWidget/SobrietyCounterWidget.swift`
- Create: `ios/App/SobrietyCounterWidget/SobrietyCounterWidgetViews.swift`
- Create: `ios/App/SobrietyCounterWidget/Info.plist`
- Create: `ios/App/SobrietyCounterWidget/SobrietyCounterWidget.entitlements`

**Step 1: Create widget entitlements file**

Create `ios/App/SobrietyCounterWidget/SobrietyCounterWidget.entitlements`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>com.apple.security.application-groups</key>
	<array>
		<string>group.com.myrecoverypal.app</string>
	</array>
</dict>
</plist>
```

**Step 2: Create widget Info.plist**

Create `ios/App/SobrietyCounterWidget/Info.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>en</string>
	<key>CFBundleDisplayName</key>
	<string>Sobriety Counter</string>
	<key>CFBundleExecutable</key>
	<string>$(EXECUTABLE_NAME)</string>
	<key>CFBundleIdentifier</key>
	<string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>$(PRODUCT_NAME)</string>
	<key>CFBundlePackageType</key>
	<string>$(PRODUCT_BUNDLE_PACKAGE_TYPE)</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0.0</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>NSExtension</key>
	<dict>
		<key>NSExtensionPointIdentifier</key>
		<string>com.apple.widgetkit-extension</string>
	</dict>
</dict>
</plist>
```

**Step 3: Create the main widget file**

Create `ios/App/SobrietyCounterWidget/SobrietyCounterWidget.swift`:

```swift
import WidgetKit
import SwiftUI

// MARK: - Data Model

struct SobrietyEntry: TimelineEntry {
    let date: Date
    let daysSober: Int
    let sobrietyDate: Date?
    let currentMilestone: Int
    let nextMilestone: Int
    let progress: Double
    let displayName: String
}

// MARK: - Milestone Logic

struct MilestoneHelper {
    static let milestones = [1, 7, 14, 30, 60, 90, 180, 365, 730, 1095, 1460, 1825]

    static func calculate(daysSober: Int) -> (current: Int, next: Int, progress: Double) {
        var current = 0
        var next = milestones.first ?? 1

        for m in milestones {
            if daysSober >= m {
                current = m
            } else {
                next = m
                break
            }
        }

        // If past all milestones, next is the next yearly
        if daysSober >= (milestones.last ?? 1825) {
            current = daysSober - (daysSober % 365)
            if current == daysSober { current = daysSober - 365 }
            next = current + 365
        }

        let range = Double(next - current)
        let progress = range > 0 ? Double(daysSober - current) / range : 1.0
        return (current, next, min(max(progress, 0), 1))
    }
}

// MARK: - Timeline Provider

struct SobrietyTimelineProvider: TimelineProvider {
    private let suiteName = "group.com.myrecoverypal.app"

    func placeholder(in context: Context) -> SobrietyEntry {
        SobrietyEntry(
            date: Date(),
            daysSober: 42,
            sobrietyDate: nil,
            currentMilestone: 30,
            nextMilestone: 60,
            progress: 0.4,
            displayName: ""
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (SobrietyEntry) -> Void) {
        completion(makeEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SobrietyEntry>) -> Void) {
        let entry = makeEntry()

        // Refresh at midnight to update the day count
        let calendar = Calendar.current
        let tomorrow = calendar.startOfDay(for: calendar.date(byAdding: .day, value: 1, to: Date())!)
        let timeline = Timeline(entries: [entry], policy: .after(tomorrow))
        completion(timeline)
    }

    private func makeEntry() -> SobrietyEntry {
        let defaults = UserDefaults(suiteName: suiteName)
        let dateString = defaults?.string(forKey: "sobriety_date") ?? ""
        let displayName = defaults?.string(forKey: "display_name") ?? ""

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"

        guard !dateString.isEmpty, let sobrietyDate = formatter.date(from: dateString) else {
            return SobrietyEntry(
                date: Date(),
                daysSober: 0,
                sobrietyDate: nil,
                currentMilestone: 0,
                nextMilestone: 1,
                progress: 0,
                displayName: displayName
            )
        }

        let daysSober = Calendar.current.dateComponents([.day], from: sobrietyDate, to: Date()).day ?? 0
        let milestone = MilestoneHelper.calculate(daysSober: daysSober)

        return SobrietyEntry(
            date: Date(),
            daysSober: max(daysSober, 0),
            sobrietyDate: sobrietyDate,
            currentMilestone: milestone.current,
            nextMilestone: milestone.next,
            progress: milestone.progress,
            displayName: displayName
        )
    }
}

// MARK: - Widget Configuration

@main
struct SobrietyCounterWidget: Widget {
    let kind = "SobrietyCounterWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: SobrietyTimelineProvider()) { entry in
            SobrietyWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("Sobriety Counter")
        .description("Track your days in recovery.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
```

**Step 4: Create the SwiftUI views file**

Create `ios/App/SobrietyCounterWidget/SobrietyCounterWidgetViews.swift`:

```swift
import SwiftUI
import WidgetKit

// MARK: - Color Constants

extension Color {
    static let mrpBlue = Color(red: 30/255, green: 77/255, blue: 139/255)       // #1e4d8b
    static let mrpLightBlue = Color(red: 45/255, green: 108/255, blue: 181/255) // #2d6cb5
    static let mrpGreen = Color(red: 82/255, green: 183/255, blue: 136/255)     // #52b788
}

// MARK: - Entry View (routes to correct size)

struct SobrietyWidgetEntryView: View {
    var entry: SobrietyEntry
    @Environment(\.widgetFamily) var family

    var body: some View {
        switch family {
        case .systemSmall:
            SmallWidgetView(entry: entry)
        case .systemMedium:
            MediumWidgetView(entry: entry)
        default:
            SmallWidgetView(entry: entry)
        }
    }
}

// MARK: - Small Widget

struct SmallWidgetView: View {
    var entry: SobrietyEntry

    var body: some View {
        ZStack {
            LinearGradient(
                gradient: Gradient(colors: [.mrpBlue, .mrpLightBlue]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            if entry.sobrietyDate != nil {
                VStack(spacing: 4) {
                    Text("\(entry.daysSober)")
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                        .minimumScaleFactor(0.5)
                        .lineLimit(1)

                    Text(entry.daysSober == 1 ? "day sober" : "days sober")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.white.opacity(0.85))

                    Spacer().frame(height: 4)

                    Text(milestoneText)
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(.mrpGreen)
                        .lineLimit(1)
                }
                .padding(.vertical, 12)
            } else {
                VStack(spacing: 8) {
                    Image(systemName: "heart.circle.fill")
                        .font(.system(size: 32))
                        .foregroundColor(.white.opacity(0.8))
                    Text("Open app to\nset your date")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white.opacity(0.85))
                        .multilineTextAlignment(.center)
                }
            }
        }
        .widgetURL(URL(string: "myrecoverypal://social-feed"))
    }

    private var milestoneText: String {
        let daysTo = entry.nextMilestone - entry.daysSober
        if daysTo <= 0 { return "Milestone reached!" }
        return "\(daysTo)d to \(formatMilestone(entry.nextMilestone))"
    }

    private func formatMilestone(_ days: Int) -> String {
        if days >= 365 {
            let years = days / 365
            return "\(years) year\(years > 1 ? "s" : "")"
        } else if days >= 30 {
            let months = days / 30
            return "\(months) month\(months > 1 ? "s" : "")"
        } else {
            return "\(days) days"
        }
    }
}

// MARK: - Medium Widget

struct MediumWidgetView: View {
    var entry: SobrietyEntry

    var body: some View {
        ZStack {
            LinearGradient(
                gradient: Gradient(colors: [.mrpBlue, .mrpLightBlue]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            if entry.sobrietyDate != nil {
                HStack(spacing: 16) {
                    // Left: Progress Ring
                    ZStack {
                        Circle()
                            .stroke(Color.white.opacity(0.2), lineWidth: 8)
                        Circle()
                            .trim(from: 0, to: CGFloat(entry.progress))
                            .stroke(Color.mrpGreen, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                            .rotationEffect(.degrees(-90))
                        VStack(spacing: 0) {
                            Text("\(entry.daysSober)")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                                .foregroundColor(.white)
                                .minimumScaleFactor(0.5)
                                .lineLimit(1)
                            Text("days")
                                .font(.system(size: 10, weight: .medium))
                                .foregroundColor(.white.opacity(0.8))
                        }
                    }
                    .frame(width: 90, height: 90)

                    // Right: Details
                    VStack(alignment: .leading, spacing: 6) {
                        Text("MyRecoveryPal")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(.white.opacity(0.6))
                            .textCase(.uppercase)
                            .tracking(0.5)

                        Text(entry.daysSober == 1 ? "1 Day Sober" : "\(entry.daysSober) Days Sober")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)

                        Spacer().frame(height: 2)

                        // Next milestone
                        let daysTo = entry.nextMilestone - entry.daysSober
                        if daysTo > 0 {
                            HStack(spacing: 4) {
                                Image(systemName: "flag.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(.mrpGreen)
                                Text("\(daysTo) days to \(formatMilestone(entry.nextMilestone))")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.white.opacity(0.85))
                            }
                        } else {
                            HStack(spacing: 4) {
                                Image(systemName: "star.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(.mrpGreen)
                                Text("Milestone reached!")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.mrpGreen)
                            }
                        }

                        // Progress bar
                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                RoundedRectangle(cornerRadius: 3)
                                    .fill(Color.white.opacity(0.2))
                                    .frame(height: 6)
                                RoundedRectangle(cornerRadius: 3)
                                    .fill(Color.mrpGreen)
                                    .frame(width: geo.size.width * CGFloat(entry.progress), height: 6)
                            }
                        }
                        .frame(height: 6)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            } else {
                HStack(spacing: 16) {
                    Image(systemName: "heart.circle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.white.opacity(0.8))
                    VStack(alignment: .leading, spacing: 4) {
                        Text("MyRecoveryPal")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                        Text("Open the app to set your sobriety date and start tracking.")
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.8))
                    }
                }
                .padding(.horizontal, 16)
            }
        }
        .widgetURL(URL(string: "myrecoverypal://social-feed"))
    }

    private func formatMilestone(_ days: Int) -> String {
        if days >= 365 {
            let years = days / 365
            return "\(years) year\(years > 1 ? "s" : "")"
        } else if days >= 30 {
            let months = days / 30
            return "\(months) month\(months > 1 ? "s" : "")"
        } else {
            return "\(days) days"
        }
    }
}

// MARK: - Previews

struct SobrietyWidget_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            SmallWidgetView(entry: SobrietyEntry(
                date: Date(), daysSober: 42, sobrietyDate: Date(),
                currentMilestone: 30, nextMilestone: 60, progress: 0.4, displayName: "Ryan"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))

            MediumWidgetView(entry: SobrietyEntry(
                date: Date(), daysSober: 42, sobrietyDate: Date(),
                currentMilestone: 30, nextMilestone: 60, progress: 0.4, displayName: "Ryan"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))

            // Empty state
            SmallWidgetView(entry: SobrietyEntry(
                date: Date(), daysSober: 0, sobrietyDate: nil,
                currentMilestone: 0, nextMilestone: 1, progress: 0, displayName: ""
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
        }
    }
}
```

**Step 5: Commit**

```bash
git add ios/App/SobrietyCounterWidget/
git commit -m "feat: add WidgetKit sobriety counter extension files

Small widget: days sober count + next milestone text
Medium widget: progress ring + days sober + milestone bar
Both use App Group UserDefaults for data, refresh at midnight."
```

---

### Task 5: Add widget extension target to Xcode project

**Files:**
- Create: `scripts/add_widget_target.rb` (temporary, can delete after running)
- Modify: `ios/App/App.xcodeproj/project.pbxproj` (programmatically)

This is the most critical task. We use the `xcodeproj` Ruby gem (same library CocoaPods uses) to safely add the extension target.

**Step 1: Create the Ruby script**

Create `scripts/add_widget_target.rb`:

```ruby
#!/usr/bin/env ruby
require 'xcodeproj'

project_path = File.join(__dir__, '..', 'ios', 'App', 'App.xcodeproj')
project = Xcodeproj::Project.open(project_path)

# Check if target already exists
if project.targets.any? { |t| t.name == 'SobrietyCounterWidget' }
  puts "Target 'SobrietyCounterWidget' already exists. Skipping."
  exit 0
end

# Create the widget extension target
widget_target = project.new_target(
  :app_extension,
  'SobrietyCounterWidget',
  :ios,
  '14.0'
)

# Set bundle identifier and build settings for all configs
widget_target.build_configurations.each do |config|
  config.build_settings['PRODUCT_BUNDLE_IDENTIFIER'] = 'com.myrecoverypal.app.SobrietyCounterWidget'
  config.build_settings['SWIFT_VERSION'] = '5.0'
  config.build_settings['INFOPLIST_FILE'] = 'SobrietyCounterWidget/Info.plist'
  config.build_settings['CODE_SIGN_ENTITLEMENTS'] = 'SobrietyCounterWidget/SobrietyCounterWidget.entitlements'
  config.build_settings['ASSETCATALOG_COMPILER_WIDGET_BACKGROUND_COLOR_NAME'] = 'WidgetBackground'
  config.build_settings['TARGETED_DEVICE_FAMILY'] = '1,2'
  config.build_settings['MARKETING_VERSION'] = '1.0.0'
  config.build_settings['CURRENT_PROJECT_VERSION'] = '1'
  config.build_settings['GENERATE_INFOPLIST_FILE'] = 'NO'
  config.build_settings['PRODUCT_NAME'] = '$(TARGET_NAME)'
  config.build_settings['LD_RUNPATH_SEARCH_PATHS'] = [
    '$(inherited)',
    '@executable_path/Frameworks',
    '@executable_path/../../Frameworks'
  ]
end

# Create file group
widget_group = project.main_group.new_group('SobrietyCounterWidget', 'SobrietyCounterWidget')

# Add source files
swift_files = [
  'SobrietyCounterWidget/SobrietyCounterWidget.swift',
  'SobrietyCounterWidget/SobrietyCounterWidgetViews.swift'
]

swift_files.each do |path|
  file_ref = widget_group.new_file(path)
  widget_target.source_build_phase.add_file_reference(file_ref)
end

# Add Info.plist and entitlements as file references (not in build phase)
widget_group.new_file('SobrietyCounterWidget/Info.plist')
widget_group.new_file('SobrietyCounterWidget/SobrietyCounterWidget.entitlements')

# Embed the widget extension in the main app
app_target = project.targets.find { |t| t.name == 'App' }
if app_target
  # Add embed extension build phase if it doesn't exist
  embed_phase = app_target.build_phases.find { |p| p.is_a?(Xcodeproj::Project::Object::PBXCopyFilesBuildPhase) && p.symbol_dst_subfolder_spec == :plug_ins }

  unless embed_phase
    embed_phase = project.new(Xcodeproj::Project::Object::PBXCopyFilesBuildPhase)
    embed_phase.name = 'Embed App Extensions'
    embed_phase.symbol_dst_subfolder_spec = :plug_ins
    app_target.build_phases << embed_phase
  end

  # Add widget product to embed phase
  build_file = embed_phase.add_file_reference(widget_target.product_reference)
  build_file.settings = { 'ATTRIBUTES' => ['RemoveHeadersOnCopy'] }

  # Add target dependency
  app_target.add_dependency(widget_target)
end

# Also add WidgetBridge.swift and MyViewController.swift to the main App target's source build phase
# if they aren't already there
app_group = project.main_group.find_subpath('App', false)
if app_group
  ['App/WidgetBridge.swift', 'App/MyViewController.swift'].each do |path|
    # Check if file reference already exists
    existing = app_group.files.find { |f| f.path == File.basename(path) }
    unless existing
      file_ref = app_group.new_file(path)
      app_target.source_build_phase.add_file_reference(file_ref) if app_target
    end
  end
end

project.save

puts "Successfully added SobrietyCounterWidget extension target."
puts "Bundle ID: com.myrecoverypal.app.SobrietyCounterWidget"
puts "Deployment target: iOS 14.0"
```

**Step 2: Run the script**

Run:
```bash
ruby scripts/add_widget_target.rb
```

Expected output:
```
Successfully added SobrietyCounterWidget extension target.
Bundle ID: com.myrecoverypal.app.SobrietyCounterWidget
Deployment target: iOS 14.0
```

**Step 3: Verify the project opens and builds**

Run:
```bash
xcodebuild -workspace ios/App/App.xcworkspace -scheme App \
  -configuration Release -destination 'generic/platform=iOS' \
  CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build 2>&1 | tail -5
```

Expected: `BUILD SUCCEEDED`

**Step 4: Commit**

```bash
git add ios/App/App.xcodeproj/project.pbxproj scripts/add_widget_target.rb
git commit -m "feat: add SobrietyCounterWidget extension target to Xcode project

Uses xcodeproj gem to safely add the widget extension target,
embed it in the main app, and register Swift source files."
```

---

### Task 6: Build verification and cache busting

**Files:**
- Modify: `templates/base.html` (already modified in Task 3)

**Step 1: Sync Capacitor**

Run:
```bash
npx cap sync ios
```

**Step 2: Build and verify**

Run:
```bash
xcodebuild -workspace ios/App/App.xcworkspace -scheme App \
  -configuration Release -destination 'generic/platform=iOS' \
  CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build 2>&1 | tail -10
```

Expected: `BUILD SUCCEEDED`

**Step 3: If build issues, fix and re-run**

Common issues:
- Missing `WidgetKit` framework link: add to widget target's frameworks build phase
- Swift version mismatch: ensure both targets use Swift 5.0
- Code signing: ignore for unsigned builds (`CODE_SIGNING_REQUIRED=NO`)

**Step 4: Final commit**

```bash
git add ios/
git commit -m "chore: sync Capacitor iOS project with widget extension"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | App Group entitlement | `App.entitlements` |
| 2 | WidgetBridge plugin + ViewController | `WidgetBridge.swift`, `MyViewController.swift`, `Main.storyboard` |
| 3 | JS bridge + meta tags | `capacitor-widget.js`, `base.html` |
| 4 | Widget extension Swift files | `SobrietyCounterWidget/*.swift`, `Info.plist`, entitlements |
| 5 | Xcode project target setup | `project.pbxproj` via Ruby script |
| 6 | Build verification | Sync + build |
