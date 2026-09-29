# nmmobile



# Numbers Match Mobile App — Build Summary

All 21 files are in place. The app is ready. 🚀

## Project Structure

`mobile/nmmobile/`  
React Native + Expo app using the same stack and architectural patterns as the parent Minesweeper app.

---

# Architecture

```txt
index.js / App.js
→ Entry point + navigation setup
→ NavigationContainer + Stack Navigator

src/
├── context/
│   └── ThemeContext
│       → Auto / Light / Dark theme support
│       → Separate light + dark palettes
│       → Persisted with AsyncStorage
│
├── gameEngine.js
│   → Pure JavaScript port of numbers_match.js
│   → Core gameplay logic:
│      • canMatch
│      • areAdjacent
│      • calcPairScore
│      • countRowClearBonus
│      • findHint
│      • generateBoardClient
│      • boardNumber
│      • initialRows
│
├── hooks/
│   ├── useGameState
│   │   → useReducer state management
│   │   → Supported actions:
│   │      • INIT
│   │      • CELL_PRESS
│   │      • UNDO
│   │      • HINT
│   │      • ADD_LINES
│   │
│   └── useTimer
│       → Starts on first tap
│       → Stops on win
│       → Resets on new game
│
├── services/
│   ├── apiService
│   │   → fetchBoard()
│   │   → submitNMScore()
│   │   → fetchNMLeaderboard()
│   │   → Includes:
│   │      • 10-second timeout
│   │      • X-Client-Type header
│   │
│   └── storage
│       → AsyncStorage persistence
│       → Saves:
│          • playerName
│          • theme
│
├── components/
│   ├── BoardView
│   │   → FlatList with numColumns=9
│   │   → Memoized cells for performance
│   │   → Dynamic sizing based on screen width
│   │
│   ├── WinModal
│   │   → Displays:
│   │      • score
│   │      • time
│   │      • lines added
│   │   → Includes:
│   │      • player name input
│   │      • save score button (daily mode only)
│   │      • Daily / Random game buttons
│   │
│   └── AdBanner
│       → react-native-google-mobile-ads BANNER integration
│       → Uses TestIds during development
│
└── screens/
    ├── GameScreen
    │   → Includes:
    │      • Daily / Random mode bar
    │      • Stats row
    │      • Toolbar:
    │         - Undo
    │         - Hint
    │         - Add Lines
    │      • Game board
    │      • Ad banner
    │
    ├── LeaderboardScreen
    │   → Fetches:
    │      /api/numbers-match-scores/{date}
    │   → Displays:
    │      • medal rankings
    │      • score column
    │      • time column
    │
    ├── HowToPlayScreen
    │   → Includes:
    │      • matching rules
    │      • scoring table
    │      • strategy tips
    │
    └── SettingsScreen
        → Includes:
           • player name input
           • theme picker
             - Auto
             - Light
             - Dark
```


# Production Build Checklist

Before building for production you need to:

1. Replace `REPLACE_WITH_EAS_PROJECT_ID` in [app.json](vscode-webview://0quvgeann4v47crb206h378g7pmt27j3euk4bmv18k418jvf8vn3/mobile/nmmobile/app.json) after running `eas project:init`

2. Replace the AdMob ad unit IDs in [AdBanner.js](vscode-webview://0quvgeann4v47crb206h378g7pmt27j3euk4bmv18k418jvf8vn3/mobile/nmmobile/src/components/AdBanner.js) with Numbers Match-specific units from your AdMob account

3. Replace the placeholder icon/splash in `assets/` with Numbers Match branding