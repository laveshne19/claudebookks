# Nalanda ERP — Native Mobile Wrapper (iOS + Android)

This folder is a **Capacitor wrapper** around the existing React web app. It produces signed APK (Android) and IPA (iOS) builds that run the same SaaS, but with **true background GPS** that keeps pinging location even when the app is closed or the phone is locked.

The web app is a thin shell — all UI/logic lives in `/app/frontend`. The wrapper only adds:

- ✅ Background geolocation (5-min interval, survives app-close & device reboot)
- ✅ Native splash screen + status bar
- ✅ Push notification capability (FCM / APNs ready)
- ✅ Installable as a real OS-level app (not "Add to Home Screen" hack)

---

## Why a wrapper (not pure PWA)?

PWAs **cannot** run background GPS when the tab/app is closed — that's a hard browser policy on iOS and Android. The only legitimate way to do silent always-on tracking is a native app with a foreground/background service. Capacitor wraps the same React build into that native shell with one config file.

---

## Build instructions (on your dev Mac / Windows / Linux)

> ⚠️ **This cannot be built inside the Emergent sandbox** — you need Android Studio + JDK 17 (for Android) and Xcode 15+ on macOS (for iOS). All commands below run on your own machine.

### 0. One-time setup

```bash
# Install Node 20 LTS + Yarn 1.22
# Install Android Studio (with SDK 34 + build-tools 34)
# (macOS) Install Xcode 15+ from App Store + CocoaPods (sudo gem install cocoapods)
```

### 1. Clone the repo & install dependencies

```bash
cd /path/to/nalanda
cd frontend && yarn install
cd ../mobile && yarn install
```

### 2. Build the web app & add native platforms

```bash
# from /mobile
yarn build:web         # produces ../frontend/build
yarn add:android       # creates ./android
yarn add:ios           # creates ./ios   (macOS only)
yarn sync              # copies web build into native projects
```

### 3. Run on an attached Android device / emulator

```bash
yarn run:android
```

### 4. Build a release APK

```bash
# Generate a keystore (one-time)
keytool -genkey -v -keystore release.keystore -alias nalanda-release \
        -keyalg RSA -keysize 2048 -validity 10000

# Build
yarn build:android
# APK at android/app/build/outputs/apk/release/app-release.apk
```

### 5. iOS

```bash
yarn open:ios   # opens Xcode → Product → Archive → Distribute App
```

---

## Background GPS — how it works

`@capacitor-community/background-geolocation` registers a foreground Android service (with a sticky notification — required by Google Play policy) and a Core Location updates handler on iOS. Both ping the device GPS on a 5-min interval and POST to `/api/location/ping` even when the user has the app in the background or the screen is off.

To keep this **truly invisible to the staff member**, the Android notification text reads simply "Active" (no mention of GPS). On iOS we use the "Always" location permission once, then no further user prompts appear.

To enable on app start, copy `mobile/src/locationBootstrap.js` into `/app/frontend/src/` and import it from `App.js` (gated by `Capacitor.isNativePlatform()` so it only fires inside the wrapper).

---

## Permissions required

### Android (`android/app/src/main/AndroidManifest.xml`)
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
<uses-permission android:name="android.permission.WAKE_LOCK"/>
```

### iOS (`ios/App/App/Info.plist`)
```xml
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Nalanda uses location to record attendance during work hours.</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>Nalanda uses location to record attendance during work hours.</string>
<key>UIBackgroundModes</key>
<array>
  <string>location</string>
  <string>fetch</string>
</array>
```

---

## Distribution (private app — no public Play Store)

Since this is internal-only:

- **Android:** sideload the signed APK to staff devices, or use **Google Play Internal App Sharing** / **Managed Google Play** for private distribution
- **iOS:** use **Apple Business Manager + Apple Developer Enterprise Program** for private distribution, or **TestFlight** for up to 10 000 testers

---

## What runs where

| Feature | Web (PWA) | Native (Capacitor) |
|---------|----------|---------------------|
| Login / Dashboards / Reports | ✅ | ✅ |
| Manual GPS while app open | ✅ | ✅ |
| GPS when app closed / device locked | ❌ | ✅ |
| Push notifications | ⚠️ partial | ✅ |
| Biometric login | ❌ | ✅ (with @capacitor-community/biometric-auth) |
| App store distribution | n/a | ✅ |
