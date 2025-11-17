# MyRecoveryPal - Complete Mobile App Deployment Guide

This guide walks you through deploying your MyRecoveryPal Android and iOS apps from start to finish.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start - First Time Setup](#quick-start---first-time-setup)
3. [Android Deployment](#android-deployment)
4. [iOS Deployment](#ios-deployment)
5. [Troubleshooting](#troubleshooting)
6. [Ongoing Updates](#ongoing-updates)

---

## Prerequisites

### Required Tools

**For Android (Works on Windows, macOS, Linux):**
- Node.js 18+ ([download](https://nodejs.org/))
- Java Development Kit (JDK) 17+ ([download](https://adoptium.net/))
- Android Studio ([download](https://developer.android.com/studio))
- Google Play Console account ($25 one-time fee)

**For iOS (macOS only):**
- Xcode 14+ (from Mac App Store)
- CocoaPods: `sudo gem install cocoapods`
- Apple Developer account ($99/year)

### Verify Your Installation

```bash
# Check Node.js
node --version  # Should be 18+

# Check Java (for Android)
java -version   # Should be 17+

# Check npm
npm --version
```

---

## Quick Start - First Time Setup

### Step 1: Install Dependencies

```bash
cd /path/to/myrecoverypal
npm install
```

### Step 2: Verify Capacitor Setup

The platforms are already added! Verify with:

```bash
ls -la android/  # Should show Android project
ls -la ios/      # Should show iOS project
ls -la www/      # Should show web assets
```

### Step 3: Initial Sync

```bash
npm run cap:sync
```

This syncs your web assets and plugins to both platforms.

---

## Android Deployment

### Part 1: Development & Testing

#### 1.1 Open in Android Studio

```bash
npm run cap:open:android
```

This opens the Android project in Android Studio.

#### 1.2 Create a Virtual Device (if needed)

In Android Studio:
1. Click "Device Manager" (phone icon in toolbar)
2. Click "Create Device"
3. Select "Pixel 5" or similar
4. Download and select a system image (API 33+ recommended)
5. Click "Finish"

#### 1.3 Run the App

In Android Studio:
1. Select your device/emulator from the dropdown
2. Click the green "Run" button (▶)
3. App will launch in a few seconds

**What you'll see:** The app loads your production site (https://www.myrecoverypal.com) in a native wrapper.

#### 1.4 Test on a Physical Device

1. Enable Developer Options on your Android device:
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
2. Enable USB Debugging:
   - Settings → Developer Options → USB Debugging
3. Connect device via USB
4. In Android Studio, select your device
5. Click "Run"

### Part 2: Building for Release

#### 2.1 Generate a Signing Key

You need this to sign your app for the Play Store:

```bash
# On macOS/Linux:
keytool -genkey -v -keystore myrecoverypal-release.keystore -alias myrecoverypal -keyalg RSA -keysize 2048 -validity 10000

# On Windows:
keytool -genkey -v -keystore myrecoverypal-release.keystore -alias myrecoverypal -keyalg RSA -keysize 2048 -validity 10000
```

**Important:**
- Store this keystore file safely - you'll need it for all future updates
- Remember the password you set
- Keep the alias name (`myrecoverypal`)

#### 2.2 Configure Signing in Android Studio

1. In Android Studio, open `android/app/build.gradle`
2. Add before the `android {` block:

```gradle
// Store keystore credentials securely
def keystorePropertiesFile = rootProject.file("keystore.properties")
def keystoreProperties = new Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}
```

3. Inside the `android {` block, add:

```gradle
signingConfigs {
    release {
        keyAlias keystoreProperties['keyAlias']
        keyPassword keystoreProperties['keyPassword']
        storeFile file(keystoreProperties['storeFile'])
        storePassword keystoreProperties['storePassword']
    }
}

buildTypes {
    release {
        signingConfig signingConfigs.release
        minifyEnabled false
        proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
    }
}
```

4. Create `android/keystore.properties`:

```properties
storeFile=/path/to/myrecoverypal-release.keystore
storePassword=YOUR_KEYSTORE_PASSWORD
keyAlias=myrecoverypal
keyPassword=YOUR_KEY_PASSWORD
```

**Security:** Add `keystore.properties` to `.gitignore` immediately!

#### 2.3 Build the Release AAB

```bash
npm run build:android:release
```

The AAB file will be at: `android/app/build/outputs/bundle/release/app-release.aab`

### Part 3: Google Play Store Submission

#### 3.1 Create a Google Play Console Account

1. Go to [play.google.com/console](https://play.google.com/console)
2. Pay the $25 one-time developer fee
3. Complete your developer profile

#### 3.2 Create Your App

1. Click "Create app"
2. Fill in:
   - **App name:** MyRecoveryPal
   - **Default language:** English (United States)
   - **App or game:** App
   - **Free or paid:** Free (or paid if you prefer)
3. Accept declarations and click "Create app"

#### 3.3 Set Up Your App Store Listing

**Store listing:**
- Short description (80 chars max)
- Full description (4000 chars max)
- App icon (512x512 PNG)
- Feature graphic (1024x500 PNG)
- Screenshots (at least 2, recommended 8):
  - Phone: 16:9 or 9:16 ratio
  - 7-inch tablet: 16:9 or 9:16 ratio
  - 10-inch tablet: 16:9 or 9:16 ratio

**App categorization:**
- Category: Health & Fitness (or Medical)
- Content rating: Complete the questionnaire

**Contact details:**
- Email, phone (optional), website

#### 3.4 Upload Your App

1. Go to "Release" → "Production"
2. Click "Create new release"
3. Upload the AAB file: `android/app/build/outputs/bundle/release/app-release.aab`
4. Fill in release notes
5. Review and roll out to production

#### 3.5 Wait for Review

- Google typically reviews within 1-7 days
- You'll receive an email when approved
- App goes live automatically after approval

---

## iOS Deployment

### Part 1: Development & Testing

#### 1.1 Install CocoaPods Dependencies

```bash
cd ios/App
pod install
cd ../..
```

#### 1.2 Open in Xcode

```bash
npm run cap:open:ios
```

**Important:** Always open `ios/App/App.xcworkspace` (not `.xcodeproj`)

#### 1.3 Configure Signing

In Xcode:
1. Select the "App" project in the navigator
2. Select the "App" target
3. Go to "Signing & Capabilities" tab
4. Check "Automatically manage signing"
5. Select your Team (Apple Developer account)
6. Bundle Identifier should be: `com.myrecoverypal.app`

#### 1.4 Run on Simulator

1. Select a simulator from the device dropdown (e.g., "iPhone 15 Pro")
2. Click the "Run" button (▶)
3. App launches in the simulator

#### 1.5 Run on Physical Device

1. Connect your iOS device via USB
2. In Xcode, select your device from the dropdown
3. If prompted, trust the computer on your device
4. Click "Run"
5. On device: Settings → General → Device Management → Trust your developer certificate

### Part 2: Building for Release

#### 2.1 Update Version and Build Number

In Xcode:
1. Select "App" target
2. Go to "General" tab
3. Update:
   - **Version:** 1.0 (or your version)
   - **Build:** 1 (increment for each submission)

#### 2.2 Configure App Icons and Launch Screen

**App Icons:**
1. Place your icon in `ios/App/App/Assets.xcassets/AppIcon.appiconset/`
2. Or use the icon generator: `npm run icons:setup`

**Launch Screen:**
- Edit `ios/App/App/Base.lproj/LaunchScreen.storyboard` in Xcode
- Or leave the default

#### 2.3 Archive Your App

In Xcode:
1. Select "Any iOS Device" as the build target
2. Go to Product → Archive
3. Wait for the archive to complete
4. The Organizer window opens automatically

#### 2.4 Validate Your Archive

In the Organizer:
1. Select your archive
2. Click "Validate App"
3. Select your distribution certificate and provisioning profile
4. Wait for validation to complete
5. Fix any issues if validation fails

### Part 3: App Store Submission

#### 3.1 Create an Apple Developer Account

1. Go to [developer.apple.com](https://developer.apple.com)
2. Sign up for Apple Developer Program ($99/year)
3. Complete enrollment

#### 3.2 Create Your App in App Store Connect

1. Go to [appstoreconnect.apple.com](https://appstoreconnect.apple.com)
2. Click "My Apps" → "+" → "New App"
3. Fill in:
   - **Platform:** iOS
   - **Name:** MyRecoveryPal
   - **Primary Language:** English (U.S.)
   - **Bundle ID:** com.myrecoverypal.app
   - **SKU:** myrecoverypal-ios (or any unique ID)
4. Click "Create"

#### 3.3 Fill Out App Information

**App Information:**
- Name: MyRecoveryPal
- Subtitle (30 chars)
- Category: Health & Fitness (Primary)
- Category: Medical (Secondary, optional)

**Pricing and Availability:**
- Select your countries
- Set price (or free)

**App Privacy:**
- Complete the privacy questionnaire
- Link to your privacy policy

#### 3.4 Prepare Screenshots

Required sizes:
- 6.7" Display (iPhone 15 Pro Max): 1290 x 2796
- 6.5" Display (iPhone 11 Pro Max): 1284 x 2778
- 5.5" Display (iPhone 8 Plus): 1242 x 2208
- iPad Pro (12.9-inch): 2048 x 2732

**Tip:** Use Xcode simulators and Cmd+S to capture screenshots

#### 3.5 Upload Your Build

In Xcode Organizer:
1. Select your archive
2. Click "Distribute App"
3. Select "App Store Connect"
4. Select "Upload"
5. Follow the prompts
6. Wait for the upload to complete (can take 10-30 minutes)

In App Store Connect:
1. Go to your app → "TestFlight" tab
2. Wait for the build to process (shows "Processing" then "Ready to Submit")
3. Go to "App Store" tab
4. Click on your version (e.g., "1.0")
5. Under "Build", click "+" and select your uploaded build

#### 3.6 Submit for Review

1. Fill in all required fields:
   - Description
   - Keywords
   - Support URL
   - Marketing URL (optional)
   - Screenshots
2. Add release notes
3. Click "Submit for Review"

#### 3.7 Wait for Review

- Apple typically reviews within 1-3 days
- You may receive questions or rejection reasons
- Address any issues and resubmit
- Once approved, app goes live automatically (or on your scheduled date)

---

## Troubleshooting

### Android Issues

**Gradle build fails:**
```bash
cd android
./gradlew clean
cd ..
npm run cap:sync:android
```

**"SDK location not found":**
- Set `ANDROID_HOME` environment variable
- Or create `android/local.properties`:
```
sdk.dir=/path/to/Android/sdk
```

**App crashes on launch:**
- Check Logcat in Android Studio for errors
- Ensure your server URL is accessible
- Check AndroidManifest.xml permissions

### iOS Issues

**Pod install fails:**
```bash
cd ios/App
pod deintegrate
pod cache clean --all
pod install
cd ../..
```

**Signing errors:**
- Ensure your Apple ID is added in Xcode Preferences
- Check that your Bundle ID matches in App Store Connect
- Try "Clean Build Folder" (Cmd+Shift+K)

**Black screen on launch:**
- Check if server URL is accessible
- Check device logs in Console app (macOS)
- Ensure Info.plist has correct permissions

### General Issues

**"Command not found" errors:**
```bash
npm install
```

**App shows blank screen:**
- Verify https://www.myrecoverypal.com is accessible
- Check device internet connection
- For local testing, update `server.url` in `capacitor.config.json`

**Web changes not appearing:**
```bash
npm run cap:sync
```
Then rebuild in Android Studio/Xcode.

---

## Ongoing Updates

### Process for Updates

1. **Make changes to your Django app** (templates, static files, backend)
2. **Deploy to production server** (https://www.myrecoverypal.com)
3. **Test in web browser** to ensure changes work
4. **Sync to mobile apps:**
   ```bash
   npm run cap:sync
   ```
5. **Test in Android Studio/Xcode**
6. **Increment version/build number:**
   - Android: `android/app/build.gradle` → `versionCode` and `versionName`
   - iOS: Xcode → General tab → Version and Build
7. **Build release version:**
   - Android: `npm run build:android:release`
   - iOS: Xcode → Product → Archive
8. **Submit to stores** (follow the submission steps above)

### When to Submit Updates

**Required updates:**
- Security fixes
- Critical bugs
- Breaking API changes on your server

**Optional updates:**
- New features
- UI improvements
- Performance enhancements

**Tip:** Batch non-critical updates together to minimize review wait times.

### Version Numbering

Use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR:** Breaking changes (1.0.0 → 2.0.0)
- **MINOR:** New features (1.0.0 → 1.1.0)
- **PATCH:** Bug fixes (1.0.0 → 1.0.1)

**Build numbers:** Increment by 1 for each submission (1, 2, 3, ...)

---

## Key Configuration Files

### capacitor.config.json
```json
{
  "appId": "com.myrecoverypal.app",
  "appName": "MyRecoveryPal",
  "webDir": "www",
  "server": {
    "url": "https://www.myrecoverypal.com",
    "cleartext": true
  }
}
```

### package.json Scripts
- `npm run cap:sync` - Sync web assets to both platforms
- `npm run cap:open:android` - Open Android Studio
- `npm run cap:open:ios` - Open Xcode
- `npm run build:android:release` - Build release AAB

---

## Support Resources

**Official Documentation:**
- Capacitor: https://capacitorjs.com/docs
- Android: https://developer.android.com
- iOS: https://developer.apple.com

**App Store Guidelines:**
- Google Play: https://play.google.com/about/developer-content-policy/
- Apple App Store: https://developer.apple.com/app-store/review/guidelines/

**Questions?**
Email: ryan@myrecoverypal.com

---

## Next Steps Checklist

- [ ] Install prerequisites (Node.js, Java, Android Studio, Xcode)
- [ ] Run `npm install` in project directory
- [ ] Test Android app in emulator
- [ ] Test iOS app in simulator (if on macOS)
- [ ] Test on physical devices
- [ ] Generate app icons (all required sizes)
- [ ] Create screenshots for stores
- [ ] Write app descriptions
- [ ] Sign up for developer accounts
- [ ] Generate Android signing key
- [ ] Build release versions
- [ ] Submit to Google Play Store
- [ ] Submit to Apple App Store
- [ ] Wait for reviews
- [ ] Celebrate your app launch! 🎉

---

**Pro Tips:**

1. **Test thoroughly** before submitting - rejections delay your launch
2. **Use TestFlight** (iOS) and Internal Testing (Android) for beta testing
3. **Read store guidelines** carefully to avoid rejection
4. **Prepare for reviews** - allocate 1-2 weeks for the full process
5. **Monitor analytics** after launch to understand user behavior
6. **Plan your update strategy** - regular updates show active development

Happy deploying! 🚀📱
