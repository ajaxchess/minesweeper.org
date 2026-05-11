## Post-Launch Feature Requests

---

### Preferences Page  ← IN PROGRESS (questions pending)

Replaces / extends the existing Settings screen.

**Default Game Mode**
One combined selector covering all 6 combinations:
  Beginner | Beginner No-Guess | Intermediate | Intermediate No-Guess | Expert | Expert No-Guess
  - CLARIFIED: vertical radio list — tappable rows with a checkmark on the selected one.
    If it doesn't look right in practice, fall back to two separate rows (Mode + No-Guess toggle).
  - Replaces the current two separate segmented controls (Mode + Board type).
  - DEFAULT CHANGE: No-Guess should be the default for new installs.

**Sound**
  - On / Off toggle (default: On).
  - CLARIFIED: Preferences sets the initial sound state when the app is opened.
    The existing in-game 🔇 mute toggle continues to work within a session.
  - Implementation: `useSounds` initialises `muted` from `prefs:sound` on startup;
    the in-game toggle only affects in-session state, not the stored pref.

**Player Name**
  - Text field for score submission display name.
  - Already implemented in SettingsScreen (prefs:player_name).
  - Autosubmit section below is only shown when a name is set.

**Autosubmit High Scores**  (conditional — only visible when Player Name is set)
  - Yes / No toggle.
  - CLARIFIED: fires on every win (not personal-bests-only).
  - CLARIFIED: ad banner also refreshes on every win (moves "Refresh ad on win" from
    the longer-term list into this feature — implemented at the same time).

**On Win**  (conditional — only visible when Autosubmit = Yes)
  - CLARIFIED: Summary is the default.  New Game is the opt-in behaviour.
  - Summary: auto-submit fires, then show the full win summary (existing WinModal or
    equivalent) — user dismisses manually.
  - New Game: auto-submit fires, a compact toast at the *bottom of the game screen*
    shows Time / Efficiency / 3BV and fades out after 5 seconds, then the board
    resets automatically.  No modal, no tap required.

**About**  (bottom of Preferences screen)
  Text: "This game is dedicated to Diana, Princess of Wales.
         Her dream to ban landmines lives on at minesweeper.org."
  - CLARIFIED: Simple text + tappable "minesweeper.org" link (opens minesweeper.org/about).
    Kept compact to leave maximum space for the preference controls above.
  - Photo of Diana: deferred to a later release (confirmed).
  - Note: a separate AboutScreen.js already exists in the app — this About section
    is in addition to that screen, not a replacement.

---

### Longer-term items (not yet scheduled)

Session stats if you have autosubmit and New Game on Win and Lose set

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

Refresh ad in the banner on every game win  ← MOVED INTO Preferences feature above
