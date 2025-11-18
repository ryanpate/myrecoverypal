#!/bin/bash

# MyRecoveryPal App Icon Integration Script
# This script copies app icons to the correct locations for iOS and Android

set -e

echo "=========================================="
echo "MyRecoveryPal App Icon Integration"
echo "=========================================="
echo ""

# Check if AppIcons directory exists
if [ ! -d "AppIcons" ]; then
    echo "ERROR: AppIcons directory not found!"
    echo "Make sure you're running this from the myrecoverypal project root."
    exit 1
fi

# iOS Icon Integration
echo "Step 1: iOS App Icons"
echo "--------------------"

if [ -d "ios/App/App/Assets.xcassets" ]; then
    # Check if source icons exist
    if [ -d "AppIcons/Assets.xcassets/AppIcon.appiconset" ]; then
        echo "Copying iOS icons..."

        # Backup existing icons (just in case)
        if [ -d "ios/App/App/Assets.xcassets/AppIcon.appiconset" ]; then
            echo "  - Removing default icons..."
            rm -rf ios/App/App/Assets.xcassets/AppIcon.appiconset
        fi

        # Copy new icons
        cp -r AppIcons/Assets.xcassets/AppIcon.appiconset ios/App/App/Assets.xcassets/

        echo "  ✓ iOS icons copied successfully!"
        echo ""
    else
        echo "  ⚠ AppIcons/Assets.xcassets/AppIcon.appiconset not found"
        echo "  Skipping iOS icon integration."
        echo ""
    fi
else
    echo "  ⚠ iOS project not found at ios/App/App/Assets.xcassets"
    echo "  Run 'npx cap add ios' first to create the iOS project."
    echo ""
fi

# Android Icon Integration
echo "Step 2: Android App Icons"
echo "-------------------------"

if [ -d "android/app/src/main/res" ]; then
    if [ -f "AppIcons/playstore.png" ]; then
        echo "Android icons require Android Studio's Image Asset tool."
        echo ""
        echo "To integrate Android icons:"
        echo "  1. Run: npm run cap:open:android"
        echo "  2. In Android Studio, right-click on 'app/src/main/res'"
        echo "  3. Select: New → Image Asset"
        echo "  4. For 'Source Asset', browse to: AppIcons/playstore.png"
        echo "  5. Icon Type: Launcher Icons (Adaptive and Legacy)"
        echo "  6. Name: ic_launcher"
        echo "  7. Click Next → Finish"
        echo ""
        echo "  The absolute path to your icon is:"
        echo "  $(pwd)/AppIcons/playstore.png"
        echo ""
    else
        echo "  ⚠ AppIcons/playstore.png not found"
        echo ""
    fi
else
    echo "  ⚠ Android project not found at android/app/src/main/res"
    echo "  Run 'npx cap add android' first to create the Android project."
    echo ""
fi

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "iOS:"
if [ -d "ios/App/App/Assets.xcassets/AppIcon.appiconset" ]; then
    icon_count=$(ls -1 ios/App/App/Assets.xcassets/AppIcon.appiconset/*.png 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✓ $icon_count icon files in place"
    echo "  → Open Xcode to verify: npm run cap:open:ios"
else
    echo "  ✗ Icons not installed"
fi
echo ""
echo "Android:"
echo "  → Follow the manual steps above using Android Studio"
echo ""
echo "App Store Submissions:"
echo "  → App Store Connect: Use AppIcons/appstore.png (1024x1024)"
echo "  → Google Play Console: Use AppIcons/playstore.png (512x512)"
echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Test iOS icons:"
echo "   npm run cap:open:ios"
echo "   Build and run - check home screen icon"
echo ""
echo "2. Set up Android icons:"
echo "   npm run cap:open:android"
echo "   Use Image Asset tool (steps above)"
echo ""
echo "3. Build for release:"
echo "   iOS: Xcode → Product → Archive"
echo "   Android: npm run build:android:release"
echo ""
