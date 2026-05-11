# Minesweeper.org — App Store Submission Guide

Developer account: Richard Cross (individual) — `ajaxchess@gmail.com`

---

## Prerequisites

### Node.js version

Metro (the Expo bundler) requires Node 20 or later — Node 18 is missing
`Array.prototype.toReversed()` and will fail at build time with
`configs.toReversed is not a function`. Check your version first:

```bash
node --version
```

If it's below 20, upgrade via [nvm](https://github.com/nvm-sh/nvm):

```bash
nvm install 20
nvm use 20
nvm alias default 20         # make 20 the default for new shells
node --version               # should print v20.x.x or higher
```

### One-time machine setup

```bash
npm install -g eas-cli
eas login                    # authenticate as ajaxchess@gmail.com
```

### One-time project setup (first submission only)

```bash
cd mobile/app
eas project:init             # creates expo.dev project and writes projectId into app.json
```

After `eas project:init`, commit the updated `app.json` (it will have a new
`extra.eas.projectId` field).

### Fill in eas.json

Open `mobile/app/eas.json` and complete the two blank fields under
`submit.production.ios`:

| Field | Where to find it |
|---|---|
| `ascAppId` | [appstoreconnect.apple.com](https://appstoreconnect.apple.com) → Apps → your app → App Information → Apple ID (10-digit number) |
| `appleTeamId` | [developer.apple.com/account](https://developer.apple.com/account) → Membership → Team ID (10-char string) |

---

## Build profiles

| Profile | Command | Output | Use for |
|---|---|---|---|
| `development` | `eas build --profile development --platform ios` | iOS Simulator build | Local dev with native modules |
| `preview` | `eas build --profile preview` | IPA (device) + APK | Team / stakeholder testing |
| `production` | `eas build --profile production` | IPA + AAB | App Store / Play Store |

`autoIncrement: true` on the production profile means EAS bumps
`buildNumber` (iOS) and `versionCode` (Android) automatically — never
touch those manually.

---

## Release workflow

Run these steps for every App Store release.

### 1. Refresh static HTML assets

```bash
cd mobile/ios/static_html
./renderscript.sh
cp howtoplay_content.html ../../app/assets/howtoplay_content.html
cp strategy_content.html  ../../app/assets/strategy_content.html
```

### 2. Bump the user-facing version (if applicable)

Edit `mobile/app/app.json`:
```json
"version": "1.1.0"
```

(`buildNumber` and `versionCode` are auto-incremented by EAS — leave them alone.)

### 3. Build for production

```bash
cd mobile/app
eas build --platform ios --profile production
```

EAS will prompt for Apple ID credentials on first run and cache them
in the EAS secrets store. The build runs in the cloud; you will receive
a link to download the IPA when it finishes.

### 4. Submit to TestFlight

```bash
eas submit --platform ios --profile production --latest
```

`--latest` picks up the most recent production build automatically.
The build will appear in TestFlight within a few minutes. Internal
testers can install it immediately; external testers require a one-time
beta review (usually < 24 hours).

### 5. Promote to App Store

Once TestFlight testing is complete:

1. Go to [appstoreconnect.apple.com](https://appstoreconnect.apple.com)
2. Select the build under **TestFlight**
3. Add it to an **App Store** version
4. Complete / update:
   - Release notes (What's New)
   - Screenshots (if UI changed)
   - App description / keywords (if changed)
5. Submit for Review

Apple review typically takes 1–3 days for updates, longer for initial
submissions. Submit early.

---

## App Store Connect metadata (set once, update as needed)

| Field | Value |
|---|---|
| Category | Games › Puzzle |
| Age rating | 4+ |
| Privacy policy URL | https://minesweeper.org/privacy |
| Support URL | https://minesweeper.org |
| Marketing URL | https://minesweeper.org |

---

## Android (Google Play)

```bash
# Build
eas build --platform android --profile production

# Submit to internal track
eas submit --platform android --profile production --latest
```

Requires `google-play-service-account.json` in `mobile/app/` (gitignored).
Obtain from Google Play Console → Setup → API access → Service accounts.

Promote from Internal → Production in the Play Console once testing is done.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Export compliance popup on upload | Confirm `ios.config.usesNonExemptEncryption: false` is in `app.json` |
| Build rejected — missing privacy manifest | Add required `NSPrivacyAccessedAPITypes` entries to `ios.privacyManifests` in `app.json` |
| `ascAppId` not found | Create the app record in App Store Connect first, then copy the Apple ID |
| Credentials expired | Run `eas credentials` to refresh |
