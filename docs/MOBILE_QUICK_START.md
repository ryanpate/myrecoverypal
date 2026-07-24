# MyRecoveryPal Mobile Apps - Quick Start Guide

## For the Impatient

Want to get the mobile apps running quickly? Here's the express version:

### Prerequisites Check

```bash
# Check Node.js (need 18+)
node --version

# Check Java (need 17+, for Android)
java -version

# Check if you have Android Studio or Xcode
# Android: Check if `android` folder builds
# iOS: Need macOS with Xcode installed
```

### Quick Commands

```bash
# 1. Sync web assets to native apps (do this after ANY web changes)
npm run cap:sync

# 2. Open in Android Studio (to test/build Android)
npm run cap:open:android

# 3. Open in Xcode (to test/build iOS - macOS only)
npm run cap:open:ios

# 4. Run on connected Android device
npm run cap:run:android

# 5. Run on connected iOS device (macOS only)
npm run cap:run:ios
```

### Testing the Apps Right Now

**Android (any OS):**
1. Install Android Studio from https://developer.android.com/studio
2. Run: `npm run cap:open:android`
3. Click the green Play button in Android Studio
4. App opens in emulator or connected device

**iOS (macOS only):**
1. Install Xcode from Mac App Store
2. Run: `npm run cap:open:ios`
3. Click the Play button in Xcode
4. App opens in simulator or connected device

### What You'll See

The app will load your production website (https://www.myrecoverypal.com) in a native wrapper. It looks and feels like a real app, with:
- Native navigation
- Splash screen
- App icon on home screen
- Works offline (thanks to PWA service worker)
- Push notification support (when configured)

### Making Changes

**Web Changes:**
1. Update your Django templates/static files
2. Run: `npm run cap:sync`
3. Rebuild in Android Studio/Xcode

**Native Changes:**
1. Open Android Studio: `npm run cap:open:android`
2. Or open Xcode: `npm run cap:open:ios`
3. Edit native code directly in IDE
4. Build and test

### Building for Release

**Android:**
```bash
# Creates an AAB file for Google Play Store
npm run build:android:release

# Find it at: android/app/build/outputs/bundle/release/app-release.aab
```

**iOS:**
```bash
# Open Xcode
npm run cap:open:ios

# In Xcode: Product → Archive → Upload to App Store
```

### Common Issues

**"Command not found" errors:**
- Make sure you ran `npm install` first
- Check that Node.js and npm are installed

**Android build fails:**
```bash
cd android
./gradlew clean
cd ..
npm run cap:sync:android
```

**iOS build fails:**
```bash
cd ios
pod deintegrate
pod install
cd ..
npm run cap:sync:ios
```

**App shows blank screen:**
- Check if https://www.myrecoverypal.com is accessible
- Check device/emulator has internet connection
- For local testing, update server URL in capacitor.config.json

### Current Configuration

- **App Name:** MyRecoveryPal
- **App ID:** com.myrecoverypal.app
- **Server URL:** https://www.myrecoverypal.com
- **Platforms:** Android & iOS

### Need More Details?

See the comprehensive guide: [MOBILE_APP_GUIDE.md](MOBILE_APP_GUIDE.md)

### Quick Scripts Reference

| Command | What it does |
|---------|-------------|
| `npm run cap:sync` | Sync web changes to both platforms |
| `npm run cap:sync:android` | Sync to Android only |
| `npm run cap:sync:ios` | Sync to iOS only |
| `npm run cap:open:android` | Open Android project in Android Studio |
| `npm run cap:open:ios` | Open iOS project in Xcode |
| `npm run cap:run:android` | Build and run on Android device |
| `npm run cap:run:ios` | Build and run on iOS device |
| `npm run build:android:debug` | Build debug APK |
| `npm run build:android:release` | Build release AAB for Play Store |
| `npm run icons:setup` | Generate app icons (needs ImageMagick) |

### Next Steps for App Store Submission

1. **Sign up for developer accounts:**
   - Google Play: $25 one-time (https://play.google.com/console)
   - Apple App Store: $99/year (https://developer.apple.com)

2. **Prepare your app:**
   - Generate proper app icons (all sizes)
   - Create screenshots on various devices
   - Write app descriptions
   - Set up signing keys/certificates

3. **Build release versions:**
   - Android: `npm run build:android:release`
   - iOS: Archive in Xcode

4. **Upload to stores:**
   - Google Play: Upload AAB file
   - Apple App Store: Upload through Xcode

5. **Wait for review:**
   - Google: Usually 1-7 days
   - Apple: Usually 1-3 days

### Tips

- **Always sync after web changes:** Run `npm run cap:sync` whenever you update the Django app
- **Test on real devices:** Emulators are good, but real devices show true performance
- **Use production server:** The current config points to production - perfect for testing the real experience
- **Leverage existing PWA:** Your service worker already handles offline - the apps just wrap it!

### Support

Questions? Check [MOBILE_APP_GUIDE.md](MOBILE_APP_GUIDE.md) or email ryan@myrecoverypal.com

---

Happy building! 🚀📱
