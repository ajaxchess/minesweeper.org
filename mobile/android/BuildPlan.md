# Minesweeper.org Android App — Build Plan

## Overview

The Android app is the same React Native + Expo managed workflow project as
the iOS app, rooted at `mobile/app/`. All game logic, screens, hooks, and
services are shared. No parallel React Native codebase is needed.

What remains is Android-specific: a platform-aware `X-Client-Type` header,
adaptive icon assets, a server-side client type addition, Google Play Console
setup, and the EAS submission workflow.

See `mobile/ios/Outline.md` for full product requirements,
`mobile/ios/APISpec.md`, `mobile/ios/BoardHashSpec.md`, and
`mobile/ios/NoGuessSolverSpec.md` for technical specs.

---

## Shared Code — Already Complete

All phases below were implemented as part of the iOS build. They run on
Android without modification because React Native is cross-platform.

| Phase | Description |
|---|---|
| 1 | Expo scaffold, React Navigation, AsyncStorage, theme provider |
| 2 | Game engine (neighbors, placeMines, isSolvable, calc3BV, calcBoardHash) |
| 3 | Board UI, tap/long-press/chord/pinch-to-zoom, game timer |
| 4 | Win flow, API score submission, offline fallback |
| 5 | Leaderboard fetch, local+server merge, dedup, Leaderboard UI |
| 6 | About, How-to-Play, Strategy (WebView), Settings screens |
| 7 | Auto/light/dark theme system |

---

## Phases

### Phase A1 — Platform-Aware `X-Client-Type` Header

The `apiService.js` currently sends `X-Client-Type: ios_app` on every
request. The server uses this header to attribute scores and exempt them from
daily cleanup. Android submissions must send `X-Client-Type: android_app`.

**Deliverables:**

- Update `src/services/apiService.js` to import `Platform` from
  `react-native` and set the header dynamically:
  ```js
  import { Platform } from 'react-native';
  const CLIENT_TYPE = Platform.OS === 'android' ? 'android_app' : 'ios_app';
  ```
- Update `APISpec.md` to document `android_app` as a valid `X-Client-Type`
  value alongside `ios_app`.
- Update `main.py` (backend): ensure the `android_app` client type is
  accepted and treated the same as `ios_app` (exempt from daily cleanup,
  scored separately if needed).

---

### Phase A2 — Adaptive Icon Assets

`app.json` already references adaptive icon assets. Placeholder files exist
in `mobile/app/assets/`. These must be replaced with production-quality
artwork before Play Store submission.

**Asset requirements:**

| File | Size | Notes |
|---|---|---|
| `android-icon-foreground.png` | 1024×1024 | Foreground layer on transparent background. Safe zone: center 66% (no content in outer 17% margin). |
| `android-icon-background.png` | 1024×1024 | Solid color or simple pattern. `app.json` background color: `#E6F4FE`. |
| `android-icon-monochrome.png` | 1024×1024 | White silhouette on transparent background. Used for themed/notification icons on Android 13+. |

**Deliverables:**

- Production-quality versions of all three adaptive icon files in
  `mobile/app/assets/`
- Visual QA on a physical Android device and emulator (round, squircle, and
  square icon shapes)
- Feature graphic: 1024×500 px PNG or JPEG, required by Google Play Store
  for the store listing page. Save as `mobile/android/assets/feature_graphic.png`.

---

### Phase A3 — Google Play Console Setup

One-time setup before first submission. Requires a Google Play Developer
account ($25 one-time fee).

**Deliverables:**

- Google Play Developer account created (or existing account confirmed)
- App record created in [Play Console](https://play.google.com/console):
  - App name: **Minesweeper.org**
  - Default language: English (United States)
  - App or game: **Game**
  - Free or paid: **Free**
- Store listing completed:
  - Short description (≤80 chars): e.g. "Classic minesweeper with no-guess mode, duels, and leaderboards."
  - Full description (≤4000 chars): adapt from `templates/about.html`
  - App icon (512×512 PNG): export from adaptive icon foreground at 512 px
  - Feature graphic (1024×500): from Phase A2
  - Phone screenshots: at least 2, from a Pixel emulator
  - Tablet screenshots: at least 1, from a 7" emulator (optional for initial submission)
- Content rating questionnaire completed (expected: Everyone / PEGI 3)
- Privacy policy URL confirmed live: `https://minesweeper.org/privacy`
- Target audience: **Everyone**
- Category: **Games > Puzzle**
- Tags: minesweeper, puzzle, logic, no-guess

---

### Phase A4 — EAS Build Service Account

EAS automated submission requires a Google Play service account with the
**Release Manager** role.

**Deliverables:**

- Google Cloud service account created via
  Google Play Console → Setup → API access → Service accounts
- Service account granted **Release Manager** permission in Play Console
- JSON key downloaded and placed at `mobile/app/google-play-service-account.json`
  (this file is gitignored — never commit it)
- `eas.json` `submit.production.android.serviceAccountKeyPath` confirmed
  pointing to `./google-play-service-account.json`

---

### Phase A5 — EAS Build and Play Store Submission

**Build profiles** (already in `eas.json`):

| Profile | Command | Output | Use for |
|---|---|---|---|
| `preview` | `eas build --profile preview --platform android` | APK | Device / stakeholder testing |
| `production` | `eas build --profile production --platform android` | AAB | Play Store |

`autoIncrement: true` on the production profile bumps `versionCode` automatically.

**Release workflow:**

1. Refresh static HTML assets (same as iOS):
   ```bash
   cd mobile/ios/static_html
   ./renderscript.sh
   cp howtoplay_content.html ../../app/assets/howtoplay_content.html
   cp strategy_content.html  ../../app/assets/strategy_content.html
   ```

2. Bump user-facing version if applicable — edit `mobile/app/app.json`:
   ```json
   "version": "1.1.0"
   ```
   (`versionCode` is auto-incremented by EAS — do not touch it.)

3. Build for production:
   ```bash
   cd mobile/app
   eas build --platform android --profile production
   ```

4. Submit to internal track:
   ```bash
   eas submit --platform android --profile production --latest
   ```

5. Promote to production in Play Console:
   - Play Console → Testing → Internal testing → select build → Promote to Production
   - Complete rollout percentage (100% for initial release)

**Deliverables:**

- First internal-track build installed and tested on a physical Android device
- All six game modes verified (beginner/intermediate/expert × guess/no-guess)
- Score submission sending `android_app` client type confirmed in server logs
- App promoted to Play Store production

---

### Phase A6 — Android-Specific UX Verification

Android has hardware and OS-level behaviors that differ from iOS.

**Deliverables:**

- Hardware back button: navigates back correctly within the stack; does not
  exit the app from the Game screen without confirmation (React Navigation
  handles this by default — verify no regressions)
- Edge-to-edge display: board renders correctly on devices with a notch,
  punch-hole camera, or gesture navigation bar (no content clipped)
- Keyboard behavior on Settings screen: player name TextInput dismisses
  correctly on Android (no layout shift issues)
- Tablet layout (10"): board fits without overflow; leaderboard readable

---

## Task List

| # | Phase | Task | Status |
|---|---|---|---|
| 1 | Shared | All Phases 1–7 from iOS build | done |
| 2 | A1 | Update apiService.js: Platform-aware X-Client-Type header | pending |
| 3 | A1 | Update APISpec.md: document android_app as valid client type | pending |
| 4 | A1 | Update main.py: accept android_app client type server-side | pending |
| 5 | A2 | Design production adaptive icon (foreground / background / monochrome) | pending |
| 6 | A2 | Create feature graphic 1024×500 for Play Store listing | pending |
| 7 | A3 | Create app record in Google Play Console; complete store listing | pending |
| 8 | A3 | Complete content rating questionnaire | pending |
| 9 | A4 | Create Google Play service account; download JSON key | pending |
| 10 | A5 | eas build --platform android --profile preview; install and smoke-test | pending |
| 11 | A5 | eas build --platform android --profile production | pending |
| 12 | A5 | eas submit --platform android --profile production --latest | pending |
| 13 | A5 | Promote from internal track to Play Store production | pending |
| 14 | A6 | Verify hardware back button, edge-to-edge, keyboard, tablet layout | pending |

---

## Parallelization Notes

- Tasks 2–4 (X-Client-Type) can be done independently of icon design (5–6).
- Tasks 7–8 (Play Console setup) can be done before the first build.
- Task 9 (service account) must be done before Task 12 (submit).
- Tasks 10–11 (builds) can overlap with Task 7 (store listing) — Play Console
  accepts builds before the listing is finalized.
- Task 14 (UX verification) should run in parallel with internal-track testing
  (Task 12).

---

## Differences from iOS Build

| Area | iOS | Android |
|---|---|---|
| `X-Client-Type` | `ios_app` | `android_app` |
| Icon format | Single PNG (App Store) + Expo auto-resize | Adaptive icon (foreground / background / monochrome layers) |
| Store asset | Screenshots + app preview video (optional) | Screenshots + feature graphic (required) |
| Build output | IPA | AAB (production) / APK (testing) |
| Distribution | TestFlight → App Store | Internal track → Play Store |
| Submission tool | `eas submit --platform ios` | `eas submit --platform android` |
| Credentials | Apple ID + provisioning profile (EAS-managed) | Google Play service account JSON |
| Review time | 1–3 days (initial), ~24 hours (update) | ~3 days (initial), ~hours (update) |
| Privacy manifest | `NSPrivacyAccessedAPITypes` required | Not required |
| Encryption declaration | `usesNonExemptEncryption: false` in app.json | Not required |

---

## Risk Items

**Phase A1 — Server-side android_app**: The server's daily score cleanup
exemption and client attribution logic must be tested with the new client
type string before the app ships. Coordinate with backend before first
production build.

**Phase A2 — Adaptive icon safe zone**: Android crops the foreground layer
into various shapes (circle, squircle, square). All recognizable elements
must fit within the center 66% of the 1024×1024 canvas. Test on at least
three device icon shapes before submitting.

**Phase A4 — Service account permissions**: Google Play API access setup is
notoriously slow to propagate. Create the service account at least 24 hours
before the first intended submission.

**Phase A6 — Edge-to-edge**: Expo SDK 55 enables `edge-to-edge` by default
on Android 15+ devices. Verify the board and bottom navigation bar are not
obscured by system gesture insets.
