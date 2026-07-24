#!/bin/bash

# MyRecoveryPal Android Setup Script
# Adds required permissions to AndroidManifest.xml after Capacitor creates the project

set -e

MANIFEST_PATH="android/app/src/main/AndroidManifest.xml"

echo "=========================================="
echo "MyRecoveryPal Android Setup"
echo "=========================================="
echo ""

# Check if Android project exists
if [ ! -f "$MANIFEST_PATH" ]; then
    echo "ERROR: AndroidManifest.xml not found!"
    echo "Run 'npx cap add android' first to create the Android project."
    exit 1
fi

# Check if POST_NOTIFICATIONS permission already exists
if grep -q "android.permission.POST_NOTIFICATIONS" "$MANIFEST_PATH"; then
    echo "✓ POST_NOTIFICATIONS permission already present"
else
    echo "Adding POST_NOTIFICATIONS permission..."

    # Add the permission after the existing INTERNET permission
    if grep -q "android.permission.INTERNET" "$MANIFEST_PATH"; then
        sed -i.bak 's|<uses-permission android:name="android.permission.INTERNET" />|<uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>|' "$MANIFEST_PATH"
        rm -f "${MANIFEST_PATH}.bak"
        echo "✓ POST_NOTIFICATIONS permission added"
    else
        # If no INTERNET permission, add before </manifest>
        sed -i.bak 's|</manifest>|    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n</manifest>|' "$MANIFEST_PATH"
        rm -f "${MANIFEST_PATH}.bak"
        echo "✓ POST_NOTIFICATIONS permission added"
    fi
fi

echo ""
echo "Android setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run: npm run cap:sync"
echo "  2. Open Android Studio: npm run cap:open:android"
echo "  3. Build and test your app"
echo ""
