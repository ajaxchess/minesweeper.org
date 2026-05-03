## Post-Launch Feature Requests

---

### Preferences Page  ← IN PROGRESS (questions pending)

Replaces / extends the existing Settings screen.

**Default Game Mode**
One combined selector covering all 6 combinations:
  Beginner | Beginner No-Guess | Intermediate | Intermediate No-Guess | Expert | Expert No-Guess
  - Currently implemented as two separate segmented controls (Mode + Board type).
  - UI approach TBD: vertical radio list or picker/dropdown (6 options don't fit on one row).
  - DEFAULT CHANGE: No-Guess should be the default for new installs.

**Sound**
  - On / Off toggle (default: On).
  - Open question: same setting as the existing in-game 🔇 mute button, or separate?
  - Currently `useSounds` stores `sound_muted` independently of the prefs object.
    Plan: unify into `prefs:sound` so both the Settings screen and the in-game toggle
    read/write the same value.

**Player Name**
  - Text field for score submission display name.
  - Already implemented in SettingsScreen (prefs:player_name).
  - Autosubmit section below is only shown when a name is set.

**Autosubmit High Scores**  (conditional — only visible when Player Name is set)
  - Yes / No toggle.
  - Open question: submit every win, or only personal bests?
  - Open question: when Yes, does the WinModal disappear entirely (silent background POST
    with a brief toast), or does it still appear but pre-submitted?

**On Win**  (conditional — only visible when Autosubmit = Yes)
  - New Game — immediately reset and start again after auto-submit.
  - Summary — show the game stats (below the board or as a condensed card) then
    auto-dismiss after 10 seconds (per original PostLaunchFeatureRequests note).
  - Open question: which is the default?

**About**  (bottom of Preferences screen)
  Text: "This game is dedicated to Diana, Princess of Wales.
         Her dream to ban landmines lives on at minesweeper.org."
  - "minesweeper.org" — tappable link to minesweeper.org/about? (TBD)
  - Photo of Diana: deferred to a later release (see Longer-term items below).
  - Photo of Honey: deferred to a later release.
  - Note: a separate AboutScreen.js already exists in the app — the About *section*
    on the Preferences page is in addition to that screen, not a replacement.

---

### Longer-term items (not yet scheduled)

Replay game modelled after the replay on the main site

Music
  Music On/Off toggle on Preferences page (deferred — no music assets yet)

Full About section (future)
  Lady Di's Mobile App is brought to you by Minesweeper.org
  Our application is dedicated to Diana, Princess of Wales
  Her dream of banning landmines may not happen in her lifetime
  but we are dedicated to making it come true some day.
  Link to https://minesweeper.org/about
  Picture of Diana
  Picture of Honey

Share just-played game on Facebook

Share just-played game by URL

Refresh ad in the banner on every game win
