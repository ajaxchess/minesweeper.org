There are 48 teams in the 2026 world cup.  I want to make a Tametsi 2026 World Cup Celebration page.
We will need a link in the menu and a banner if you haven't set your fan flag.
Your fan flag is the flag that will display on all scores in the 2026worldcup tree.
Your country flag is the flag of your home country and that will still display if you play regular minesweeper on the associated high score list for that game.

There will be a new database field, the 2026 fan flag, which is selected among the 48 teams in the cup.
You can set this in your profile or on any of the pages in the 2026worldcup tree

**Implementation note (2026-05-10):** The fan flag selector is live on the profile page (`/profile`).
- Database table: `user_profiles`
- Database column: `2026_world_cup_fan_flag` (VARCHAR 16, nullable)
- Python model attribute: `UserProfile.wc2026_fan` (mapped via SQLAlchemy `name=` parameter)
- API endpoint: `POST /api/profile/wc2026-fan`

There's a little ambiguity in this document.  Each country is playing games in the world cup.  We want to keep everyone up-to-date on how those games are going.
So the https://minesweeper.org/2026worldcup will have all the latest world cup news.  What games are coming up.  What scores have happened already.  Which teams
are winning their groups.  We will be providing that data and that will update the content for the main page and the teams page.

There is also a fan event where fans play Tametsi.  The site will track how many games the fans win and will have leaderboards for fans and for country.

So 
minesweeper.org/2026worldcup
minesweeper.org/2026worldcup/algeria
...
minesweeper.org/2026worldcup/uzbekistan

Each page will have information about the country and a list of when they are playing.

There should be a main page with a list of all the groups and all the countries in the group.
The countries should be clickable so that you to to that page's homepage.

If the user logs in, they should be able to set their preferred time zone.
Then the country game times will show in that time zone.

We will focus on the group stage.  The idea is to have a web page that has all 48 teams.  You can click on a country and you get a Tametsi game that uses the colors of that team.
The country page will list the other countries in the group and when that team will play their group games.
There will be a Tametsi board on each countries home page.  The standard board will be (no guess)
15 squares (x) and 9 squares (y)  The country's primary color will fill the top 5 squares and the secondary color will fill the bottom 4 squares.  There will be 20 mines.
Whenever you flag a mine, the flag icon will be the fan flag of your selected world cup favorite team.
The Tametsi rules will be:  There will be a white number which is the total number of mines on that row or column.  Above or to the left will be a green number which is the number of mines
that have not yet been flagged on that row or column.  Above and to the left of the board will be a count of the number of unflagged mines in the part of the board with the primary or secondary color.
There will be a starting x on the top left of the board.
You can also select a Tametsi hard board and you will get a board of 30x18 with 99 mines.  This should also be no guess. Hard will have the top 9 rows be the primary color and the bottom 9 rows be the secondary
color for that team.

For example:
Canada upper 5 rows will be in Red (FF0000) and the bottom 4 rows will be in White (FFFFFF).
3 (red)
3 (white)
    141 (green)
    141 (white)
1 1 oxo
0 0 ooo
0 0 ooo
0 1 oxo
0 1 oxo
...
2 2 xox
0 0 ooo
1 1 oxo
0 0 ooo

There would be two numbers above and the the left of the board: a Red 3 and a White 3
Suppose the player flags mine at 1,9.  The green 4 -> 3.  The red 3 -> 2.  The flag displayed over the mine would be a Canadian flag

Each country will have a leaderboard for that country.  Users who are logged in will have their scores stay on the leaderboard during the entire period of the World Cup.

Please put a note on each country page regarding if they are a signatory to the Ottawa Treaty and have a link out to the wikipedia page:
https://en.wikipedia.org/wiki/Ottawa_Treaty
Status                 Nations
Signatories / Parties, "Algeria, Argentina, Australia, Austria, Belgium, Bosnia & Herzegovina, Brazil, Canada, Cape Verde, Colombia, Croatia, Czechia, DR Congo, Ecuador, France, Germany, Ghana, Haiti, Iraq, Ivory Coast, Japan, Jordan, Mexico, Netherlands, New Zealand, Norway, Panama, Paraguay, Portugal, Senegal, South Africa, Spain, Sweden, Switzerland, Tunisia, Türkiye, United Kingdom (England, Scotland), Uruguay."
Non-Signatories,       "Egypt, Iran, Morocco, Saudi Arabia, South Korea, USA, Uzbekistan."


Here are the countries:

Nation,Primary Hex,Primary RGB,Secondary Hex,Secondary RGB
Algeria,#FFFFFF,"(255, 255, 255)",#006233,"(0, 98, 51)"
Argentina,#75AADB,"(117, 170, 219)",#FFFFFF,"(255, 255, 255)"
Australia,#FFCD00,"(255, 205, 0)",#005031,"(0, 80, 49)"
Austria,#ED2939,"(237, 41, 57)",#FFFFFF,"(255, 255, 255)"
Belgium,#BA0C2F,"(186, 12, 47)",#FFCD00,"(255, 205, 0)"
Bosnia & Herz.,#002395,"(0, 35, 149)",#FECB00,"(254, 203, 0)"
Brazil,#FFDF00,"(255, 223, 0)",#009B3A,"(0, 155, 58)"
Canada,#FF0000,"(255, 0, 0)",#FFFFFF,"(255, 255, 255)"
Cape Verde,#003893,"(0, 56, 147)",#F7D117,"(247, 209, 23)"
Colombia,#FCD116,"(252, 209, 22)",#003893,"(0, 56, 147)"
Croatia,#FF0000,"(255, 0, 0)",#FFFFFF,"(255, 255, 255)"
Curaçao,#002B7F,"(0, 43, 127)",#F9D616,"(249, 214, 22)"
Czech Republic,#ED1B24,"(237, 27, 36)",#11457E,"(17, 69, 126)"
DR Congo,#007FFF,"(0, 127, 255)",#F7D117,"(247, 209, 23)"
Ecuador,#FFDD00,"(255, 221, 0)",#034EA2,"(3, 78, 162)"
Egypt,#E20111,"(226, 1, 17)",#000000,"(0, 0, 0)"
England,#FFFFFF,"(255, 255, 255)",#000040,"(0, 0, 64)"
France,#21304D,"(33, 48, 77)",#ED2939,"(237, 41, 57)"
Germany,#FFFFFF,"(255, 255, 255)",#000000,"(0, 0, 0)"
Ghana,#FFFFFF,"(255, 255, 255)",#000000,"(0, 0, 0)"
Haiti,#00209F,"(0, 32, 159)",#D21034,"(210, 16, 52)"
Iran,#FFFFFF,"(255, 255, 255)",#DA291C,"(218, 41, 28)"
Iraq,#007A33,"(0, 122, 51)",#FFFFFF,"(255, 255, 255)"
Ivory Coast,#FF8200,"(255, 130, 0)",#009E60,"(0, 158, 96)"
Japan,#000555,"(0, 5, 85)",#FFFFFF,"(255, 255, 255)"
Jordan,#FFFFFF,"(255, 255, 255)",#CE1126,"(206, 17, 38)"
Mexico,#006847,"(0, 104, 71)",#FFFFFF,"(255, 255, 255)"
Morocco,#C1272D,"(193, 39, 45)",#006233,"(0, 98, 51)"
Netherlands,#FF4F00,"(255, 79, 0)",#FFFFFF,"(255, 255, 255)"
New Zealand,#FFFFFF,"(255, 255, 255)",#000000,"(0, 0, 0)"
Norway,#EF2B2D,"(239, 43, 45)",#002868,"(0, 40, 104)"
Panama,#DA121A,"(218, 18, 26)",#072357,"(7, 35, 87)"
Paraguay,#D52B1E,"(213, 43, 30)",#FFFFFF,"(255, 255, 255)"
Portugal,#E42518,"(228, 37, 24)",#046A38,"(4, 106, 56)"
Qatar,#8A1538,"(138, 21, 56)",#FFFFFF,"(255, 255, 255)"
Saudi Arabia,#006C35,"(0, 108, 53)",#FFFFFF,"(255, 255, 255)"
Scotland,#002D56,"(0, 45, 86)",#FFFFFF,"(255, 255, 255)"
Senegal,#FFFFFF,"(255, 255, 255)",#11A335,"(17, 163, 53)"
South Africa,#FFCD00,"(255, 205, 0)",#007A33,"(0, 122, 51)"
South Korea,#ED1C24,"(237, 28, 36)",#000000,"(0, 0, 0)"
Spain,#C60B1E,"(198, 11, 30)",#FFC400,"(255, 196, 0)"
Sweden,#FECC00,"(254, 204, 0)",#006AA7,"(0, 106, 167)"
Switzerland,#D52B1E,"(213, 43, 30)",#FFFFFF,"(255, 255, 255)"
Tunisia,#FFFFFF,"(255, 255, 255)",#E70013,"(231, 0, 19)"
Türkiye,#E30A17,"(227, 10, 23)",#FFFFFF,"(255, 255, 255)"
Uruguay,#75AADB,"(117, 170, 219)",#000000,"(0, 0, 0)"
USA,#FFFFFF,"(255, 255, 255)",#002868,"(0, 40, 104)"
Uzbekistan,#FFFFFF,"(255, 255, 255)",#0099B5,"(0, 153, 181)"

Here are the group stage matches:
Group,Match Date,Matchup,Time (CDT),City,Status
Group A,June 11,Mexico vs. South Africa,2:00 PM,Mexico City,Scheduled
Group A,June 11,South Korea vs. Czechia,9:00 PM,Guadalajara,Scheduled
Group A,June 16,Mexico vs. South Korea,5:00 PM,Monterrey,Scheduled
Group A,June 16,Czechia vs. South Africa,8:00 PM,Seattle,Scheduled
Group A,June 24,Czechia vs. Mexico,8:00 PM,Mexico City,Scheduled
Group A,June 24,South Africa vs. South Korea,8:00 PM,Monterrey,Scheduled
Group B,June 12,Canada vs. Bosnia & Herz.,2:00 PM,Toronto,Scheduled
Group B,June 13,Qatar vs. Switzerland,2:00 PM,Vancouver,Scheduled
Group B,June 17,Canada vs. Qatar,12:00 PM,Toronto,Scheduled
Group B,June 17,Switzerland vs. Bosnia & Herz.,8:00 PM,Vancouver,Scheduled
Group B,June 24,Switzerland vs. Canada,2:00 PM,Vancouver,Scheduled
Group B,June 24,Bosnia & Herz. vs. Qatar,2:00 PM,Toronto,Scheduled
Group C,June 13,Brazil vs. Morocco,5:00 PM,Miami,Scheduled
Group C,June 13,Haiti vs. Scotland,8:00 PM,New York/New Jersey,Scheduled
Group C,June 18,Brazil vs. Haiti,2:00 PM,Atlanta,Scheduled
Group C,June 18,Scotland vs. Morocco,5:00 PM,Miami,Scheduled
Group C,June 24,Scotland vs. Brazil,11:00 AM,Miami,Scheduled
Group C,June 24,Morocco vs. Haiti,11:00 AM,Atlanta,Scheduled
Group D,June 12,USA vs. Paraguay,8:00 PM,Los Angeles,Scheduled
Group D,June 13,Australia vs. Türkiye,11:00 PM,Seattle,Scheduled
Group D,June 19,USA vs. Australia,8:00 PM,Seattle,Scheduled
Group D,June 19,Türkiye vs. Paraguay,5:00 PM,San Francisco,Scheduled
Group D,June 25,Türkiye vs. USA,8:00 PM,Los Angeles,Scheduled
Group D,June 25,Paraguay vs. Australia,8:00 PM,San Francisco,Scheduled
Group E,June 14,Germany vs. Curaçao,12:00 PM,Kansas City,Scheduled
Group E,June 14,Ivory Coast vs. Ecuador,6:00 PM,Dallas,Scheduled
Group E,June 20,Germany vs. Ivory Coast,2:00 PM,Kansas City,Scheduled
Group E,June 20,Ecuador vs. Curaçao,11:00 AM,Dallas,Scheduled
Group E,June 25,Ecuador vs. Germany,2:00 PM,Dallas,Scheduled
Group E,June 25,Curaçao vs. Ivory Coast,2:00 PM,Kansas City,Scheduled
Group F,June 14,Netherlands vs. Japan,3:00 PM,Houston,Scheduled
Group F,June 14,Sweden vs. Tunisia,9:00 PM,Monterrey,Scheduled
Group F,June 20,Netherlands vs. Sweden,8:00 PM,Houston,Scheduled
Group F,June 20,Tunisia vs. Japan,5:00 PM,Guadalajara,Scheduled
Group F,June 25,Tunisia vs. Netherlands,11:00 AM,Houston,Scheduled
Group F,June 25,Japan vs. Sweden,11:00 AM,Monterrey,Scheduled
Group G,June 15,Belgium vs. Egypt,2:00 PM,Boston,Scheduled
Group G,June 15,Iran vs. New Zealand,8:00 PM,Philadelphia,Scheduled
Group G,June 21,Belgium vs. Iran,11:00 AM,Philadelphia,Scheduled
Group G,June 21,New Zealand vs. Egypt,2:00 PM,Boston,Scheduled
Group G,June 26,New Zealand vs. Belgium,8:00 PM,Boston,Scheduled
Group G,June 26,Egypt vs. Iran,8:00 PM,Philadelphia,Scheduled
Group H,June 15,Spain vs. Cape Verde,11:00 AM,Los Angeles,Scheduled
Group H,June 15,Saudi Arabia vs. Uruguay,5:00 PM,San Francisco,Scheduled
Group H,June 21,Spain vs. Saudi Arabia,8:00 PM,Los Angeles,Scheduled
Group H,June 21,Uruguay vs. Cape Verde,5:00 PM,San Francisco,Scheduled
Group H,June 26,Uruguay vs. Spain,2:00 PM,San Francisco,Scheduled
Group H,June 26,Cape Verde vs. Saudi Arabia,2:00 PM,Los Angeles,Scheduled
Group I,June 16,France vs. Senegal,2:00 PM,New York/New Jersey,Scheduled
Group I,June 16,Iraq vs. Norway,5:00 PM,Boston,Scheduled
Group I,June 22,France vs. Iraq,12:00 PM,New York/New Jersey,Scheduled
Group I,June 22,Norway vs. Senegal,3:00 PM,Boston,Scheduled
Group I,June 26,Norway vs. France,11:00 AM,Boston,Scheduled
Group I,June 26,Senegal vs. Iraq,11:00 AM,New York/New Jersey,Scheduled
Group J,June 16,Argentina vs. Algeria,8:00 PM,Dallas,Scheduled
Group J,June 16,Austria vs. Jordan,11:00 PM,Houston,Scheduled
Group J,June 22,Argentina vs. Austria,8:00 PM,Dallas,Scheduled
Group J,June 22,Jordan vs. Algeria,5:00 PM,Houston,Scheduled
Group J,June 27,Jordan vs. Argentina,8:00 PM,Dallas,Scheduled
Group J,June 27,Algeria vs. Austria,8:00 PM,Houston,Scheduled
Group K,June 17,Portugal vs. DR Congo,12:00 PM,Miami,Scheduled
Group K,June 17,Uzbekistan vs. Colombia,9:00 PM,Atlanta,Scheduled
Group K,June 23,Portugal vs. Uzbekistan,2:00 PM,Atlanta,Scheduled
Group K,June 23,Colombia vs. DR Congo,11:00 AM,Miami,Scheduled
Group K,June 27,Colombia vs. Portugal,2:00 PM,Miami,Scheduled
Group K,June 27,DR Congo vs. Uzbekistan,2:00 PM,Atlanta,Scheduled
Group L,June 17,England vs. Croatia,3:00 PM,Toronto,Scheduled
Group L,June 17,Ghana vs. Panama,6:00 PM,Vancouver,Scheduled
Group L,June 23,England vs. Ghana,8:00 PM,Toronto,Scheduled
Group L,June 23,Panama vs. Croatia,5:00 PM,Vancouver,Scheduled
Group L,June 27,Panama vs. England,11:00 AM,Vancouver,Scheduled
Group L,June 27,Croatia vs. Ghana,11:00 AM,Toronto,Scheduled

City,Stadium,Latitude,Longitude,Country
Mexico City,Estadio Azteca,19.3029,-99.1505,Mexico
Guadalajara,Estadio Akron,20.6811,-103.4628,Mexico
Monterrey,Estadio BBVA,25.6700,-100.2447,Mexico
Toronto,BMO Field,43.6332,-79.4186,Canada
Vancouver,BC Place,49.2768,-123.1120,Canada
Los Angeles,SoFi Stadium,33.9535,-118.3390,USA
New York/New Jersey,MetLife Stadium,40.8128,-74.0742,USA
Miami,Hard Rock Stadium,25.9581,-80.2389,USA
Atlanta,Mercedes-Benz Stadium,33.7553,-84.4006,USA
Seattle,Lumen Field,47.5952,-122.3316,USA
San Francisco,Levi's Stadium,37.4033,-121.9694,USA
Dallas,AT&T Stadium,32.7473,-97.0945,USA
Houston,NRG Stadium,29.6847,-95.4107,USA
Kansas City,Arrowhead Stadium,39.0490,-94.4839,USA
Philadelphia,Lincoln Financial Field,39.9008,-75.1675,USA
Boston,Gillette Stadium,42.0909,-71.2643,USA

Tametsi fan challenge:
If you login, you can set your world cup fan flag in your profile or on any Tametsi world cup page.
You must be logged in and set your country flag to play.
If you are logged in, when you uncover a mine, your country gets a point.  When you solve board, your country gets 20 points.
The total points for each team are displayed on the team page and on a country leaderboard on the main page.

The minesweeper.org/2026worldcup page will have a welcome and how to play at the top.  Then clickable countries organized by groups.
Then the country Tametsi leaderboard.
Then the biggest fans individual leaderboard.
The countries get the points depending on what team you set on that day.  So Bill can set his fan flag as Canada on June 1st and play easy and hard games to earn 400 points for Canada.
Suppose Canada doesn't make it into the knockout phase.  On June 27th Bill changes his fan flag to Mexico.  Each Tametsi game won will need a database field for the fan flag set at time won.
If no flag is set, no points are earned.  Once you set your flag, you should have a notice at the top of every world cup page that says You are a fan of <fan flag>!

---

## Requirements Clarifications (2026-05-10 Q&A)

**Scoring mechanics**
- "Uncover a mine" means *flagging* a mine. Standard Tametsi game-over rules still apply.
- Points are awarded only when a board is **solved** (not on each individual flag), to avoid revealing whether a flag is correct or incorrect during play.
- Easy board (15×9, 20 mines): 1 pt per correctly flagged mine + 20 pts solve bonus = 40 pts max per game.
- Hard board (30×18, 99 mines): 1 pt per correctly flagged mine + 50 pts solve bonus = 149 pts max per game.
- Points are attributed to the fan flag the user had set **at the time of solve**.
- If no fan flag is set, no points are earned.

**Match score updates**
- Real-world match results (scores, status changes from Scheduled → Final) will be updated via an **admin UI** — a developer or admin edits the records manually.

**Board state persistence**
- Board state (which cells are revealed/flagged) is saved **per user per country per difficulty** to the database.
- When a returning user visits a country page, they resume their in-progress board.
- The board's mine layout is stored alongside the state so the same board is always presented to the same user.

**Timezone**
- A new `timezone` column (`VARCHAR(64) NULL`) will be added to `user_profiles`.
- Match times default to CDT (as listed in the schedule) for logged-out or timezone-unset users.
- Logged-in users can set their timezone on the profile page; match times display in that timezone.

**Banner and fan notice scope**
- Both the "You are a fan of X!" banner and the "Set your fan flag" prompt appear **only within `/2026worldcup/*` pages**, not sitewide.
- Three cases on any WC page:
  1. Logged in, fan flag set → "🏆 You are a fan of [flag image] [Country]!"
  2. Logged in, no fan flag → "Set your fan flag to earn points for your team!" (links to profile or inline setter)
  3. Not logged in → "Log in to set your fan flag and compete!"

**Individual leaderboard**
- "Biggest fans" ranked by **total cumulative points** (all correctly flagged mines + solve bonuses) across all WC Tametsi games.

**URL slugs (FIFA-style ASCII)**

| Display name      | URL slug                |
|-------------------|-------------------------|
| Bosnia & Herz.    | bosnia-and-herzegovina  |
| Cape Verde        | cape-verde              |
| Curaçao           | curacao                 |
| Czech Republic    | czech-republic          |
| DR Congo          | dr-congo                |
| Ivory Coast       | ivory-coast             |
| New Zealand       | new-zealand             |
| Saudi Arabia      | saudi-arabia            |
| Scotland          | scotland                |
| South Africa      | south-africa            |
| South Korea       | south-korea             |
| Türkiye           | turkey                  |
| USA               | usa                     |
| England           | england                 |
| All others        | lowercase, hyphens      |

---

## Implementation Plan — F97 Tametsi 2026 World Cup Celebration

### Phase 1 — Static data layer

Create `wc2026_data.py` in the repo root. Contains:

- `WC2026_COUNTRIES` — list of dicts, one per country:
  ```
  { slug, name, flag_code, primary_hex, secondary_hex, group, is_ottawa_signatory }
  ```
  `flag_code` is the flagcdn.com code (e.g. `gb-eng`, `gb-sct`, `us`, `mx`).
- `WC2026_MATCHES` — list of dicts from the schedule:
  ```
  { group, date_iso, team1_slug, team2_slug, time_cdt, city, score1, score2, status }
  ```
  Seeded from the schedule table in this document; `score1`/`score2` start as `None`, `status` starts as `"scheduled"`.
- `WC2026_STADIUMS` — dict keyed by city name with lat/lon/stadium name.
- Helper lookups: `WC2026_BY_SLUG`, `WC2026_BY_GROUP`.

### Phase 2 — Database migrations

New columns and tables (added via `_apply_migrations()` in `database_template.py`):

**`user_profiles` — new column**
- `timezone VARCHAR(64) NULL` — user's preferred IANA timezone string (e.g. `America/Chicago`)

**New table: `wc2026_matches`**
```sql
CREATE TABLE wc2026_matches (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  group_name VARCHAR(8),
  match_date DATE,
  team1_slug VARCHAR(32),
  team2_slug VARCHAR(32),
  time_cdt   VARCHAR(16),
  city       VARCHAR(64),
  score1     TINYINT NULL,
  score2     TINYINT NULL,
  status     VARCHAR(16) DEFAULT 'scheduled'
);
```
Seeded from `wc2026_data.py` on first run if table is empty.

**New table: `wc2026_board_states`**
```sql
CREATE TABLE wc2026_board_states (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  email        VARCHAR(255),
  country_slug VARCHAR(32),
  difficulty   ENUM('easy','hard'),
  mine_layout  TEXT,        -- JSON list of mine positions (indices)
  cell_state   TEXT,        -- JSON list: 'hidden'|'revealed'|'flagged' per cell
  is_solved    TINYINT(1) DEFAULT 0,
  started_at   DATETIME,
  solved_at    DATETIME NULL,
  UNIQUE KEY uq_board (email, country_slug, difficulty)
);
```

**New table: `wc2026_scores`**
```sql
CREATE TABLE wc2026_scores (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  email        VARCHAR(255),
  country_slug VARCHAR(32),
  difficulty   ENUM('easy','hard'),
  fan_flag     VARCHAR(16),   -- fan flag set at time of solve
  flags_correct TINYINT,      -- number of mines correctly flagged
  solve_bonus  TINYINT,       -- 20 (easy) or 50 (hard)
  total_points SMALLINT,
  solved_at    DATETIME
);
```

### Phase 3 — Board generation (server-side)

Create `wc2026_board.py`:

- `generate_no_guess_board(cols, rows, mines, seed)` — generates a mine layout that is solvable without guessing. Adapts the existing Tametsi no-guess generation algorithm (or uses a constraint-satisfaction approach). Returns a list of mine-position indices.
- `seed = f"{country_slug}_{difficulty}_{email}"` — deterministic per user per country so resuming gives the same board.
- `get_or_create_board(db, email, country_slug, difficulty)` — checks `wc2026_board_states`; creates and persists a new board if none exists; returns the board record.

Easy board: 15 cols × 9 rows, 20 mines, top 5 rows = primary color, bottom 4 = secondary. **No-guess required.**
Hard board: 30 cols × 18 rows, 99 mines, top 9 rows = primary, bottom 9 = secondary. **No-guess required.**

### Phase 4 — API endpoints

All under `/api/wc2026/`:

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/wc2026/board/{slug}/{difficulty}` | Return board state for logged-in user |
| `POST` | `/api/wc2026/board/{slug}/{difficulty}/reveal` | Reveal a cell; return updated state |
| `POST` | `/api/wc2026/board/{slug}/{difficulty}/flag` | Toggle flag on a cell; return updated state |
| `POST` | `/api/wc2026/board/{slug}/{difficulty}/solve` | Called when board is solved; award points, write `wc2026_scores` row |
| `GET`  | `/api/wc2026/leaderboard/countries` | Top countries by total fan points |
| `GET`  | `/api/wc2026/leaderboard/individuals` | Top individual players by total points |
| `GET`  | `/api/wc2026/leaderboard/country/{slug}` | Leaderboard for fans of a specific country |

### Phase 5 — Admin interface

Page: `/admin/wc2026-matches` (existing admin auth required).

- Table listing all 48 matches with current score/status.
- Inline editable score fields + status dropdown (scheduled / in_progress / final).
- Submit updates to `wc2026_matches` table.
- No external API dependency — all manual.

### Phase 6 — Templates

**`/2026worldcup` (main page)**
- Top: welcome + how-to-play
- Fan banner (logged-in with flag / set-flag prompt / login prompt)
- 12 group sections, each with country flag cards (flag image + country name + clickable link to country page)
- Country leaderboard: top 20 countries by total fan points (flag + name + points)
- Individual leaderboard: top 20 players by total points (avatar/name + fan flag + points)

**`/2026worldcup/{slug}` (country page)**
- Country header: large flag, country name, group, primary/secondary color swatches
- Ottawa Treaty status (✅ Signatory / ❌ Non-signatory) with Wikipedia link
- Group table: all countries in this group, W/D/L/Pts once matches begin
- Match schedule for this country (upcoming + results), times in user's timezone
- Fan banner (same logic as main page)
- Tametsi board section:
  - Easy/Hard toggle
  - "Log in to play" message if not logged in
  - "Set your fan flag to play" if logged in but no fan flag
  - Live Tametsi board (WC color mode) if eligible to play
  - Fan flag inline setter (dropdown + save) on the page itself
- Country leaderboard: top fans of this country by total points

### Phase 7 — Navigation

- Add "🏆 2026" link to the main nav in `base.html` pointing to `/2026worldcup`.
- The nav item could be hidden after a configurable cutoff date (or left as a permanent archive).

### Phase 8 — Profile page additions

- Add timezone selector to the existing profile settings (IANA timezone list, e.g. via a `<select>` with common zones).
- Save via existing `POST /api/profile/...` pattern or a new `POST /api/profile/timezone` endpoint.
- Store in `user_profiles.timezone`.

### Phase 9 — Tametsi JS (WC mode)

The World Cup boards use a variant of the existing Tametsi renderer. Additions needed in `tametsi.js` or a new `tametsi_wc.js`:

- Cell background colours driven by `primary_hex` / `secondary_hex` based on row index.
- Two additional zone counters displayed above/left of board: unflagged mines in primary zone, unflagged mines in secondary zone, styled in the respective colours.
- Flag icon replaced with the user's fan team flag PNG (`/static/img/country-flags/{fan_flag}.png`) when a flag is placed.
- Board state fetched from and saved to the API endpoints (Phase 4) rather than localStorage.
- On solve: call the `/solve` API endpoint to award points; show a celebratory message with points earned.

### Suggested build order

1. Phase 1 — `wc2026_data.py` (pure Python, no DB dependency, enables all other work)
2. Phase 2 — DB migrations (unblocks board + scoring work)
3. Phase 3 — Board generation (can be unit-tested independently)
4. Phase 4 — API endpoints (depends on 2 + 3)
5. Phase 6 — Templates, main page first (skeleton, no live boards yet)
6. Phase 9 — Tametsi WC JS (depends on 4 + 5 skeleton)
7. Phase 5 — Admin UI (can be done in parallel with 6/9)
8. Phase 7 — Nav link (trivial, do alongside Phase 6)
9. Phase 8 — Timezone (depends on Phase 2 migration)
10. Full integration test: set fan flag → visit country → play board → check leaderboard

---

## Addendum — Guest Play (2026-05-16)

### Motivation

Today, every WC page server-side and template-side blocks non-logged-in users from playing. The current gates are at `main.py:8594-8612` (no boards generated unless `user and fan_ctx["wc_fan"]`), the `if not user: return 401` early-return in every `/api/wc2026/board/*` endpoint, and the `wcc-play-gate` block in `templates/wc2026_country.html:96-99`.

We want guests to be able to play and **contribute to country scores**, with login reserved as the route to appear on the *individual* "biggest fans" leaderboard. This brings WC into line with the project's existing guest-play-then-claim convention used in the main minesweeper game and several other game variants (Score, RushScore, CylinderScore, ToroidScore, TentaizuScore, ReplayScore, ReplayScore, game_replays, nonosweeper_scores, etc.) — the WC feature is the outlier.

### Product decisions (locked)

- **Guests can earn country points.** Their solves write to `wc2026_scores` and roll into the country leaderboard total. The country total is the *combined* sum of guest-keyed and email-keyed rows; we do not split the column.
- **Guests do not appear on the individual "biggest fans" leaderboard.** Logging in is the carrot. The individual leaderboard query filters to `email IS NOT NULL`.
- **Light anti-abuse only.** A small per-IP daily cap on guest-earned WC points and a per-cookie rate limit on `/solve`. Other admin score-review channels already exist; we don't need tournament-grade defenses here.
- **Claim on login.** When a guest logs in, all `wc2026_board_states` and `wc2026_scores` rows carrying their `guest_token` are reassigned to the new account. In-progress boards survive; earned points become "fan" points on the individual leaderboard.

### Schema delta

Two migrations to add via `_apply_migrations()` in `database_template.py`. Naming follows the project's existing `guest_token` convention (already present on `scores`, `rush_scores`, `cylinder_scores`, `toroid_scores`, `tentaizu_scores`, `replay_scores`, `nonosweeper_scores`, `game_replays`).

```
("wc2026_board_states", "guest_token", "VARCHAR(36) NULL")
("wc2026_scores",       "guest_token", "VARCHAR(36) NULL")
```

The existing `email VARCHAR(256) NOT NULL` columns on both tables must become **nullable** so a row can be keyed by `guest_token` instead. This is two additional ALTERs to add to the migrations list (with idempotency check on `IS_NULLABLE`).

Indexes:

- Drop the existing unique index `ix_wc2026_board_states_email_country_diff` (which was `(email, country_slug, difficulty)` with `email NOT NULL`) and replace with two partial-uniqueness expressions. MySQL doesn't support partial indexes, so use one unique index that includes both candidate keys: `UNIQUE KEY (COALESCE(email, guest_token), country_slug, difficulty)` is awkward; instead, enforce uniqueness at the application layer (`get_or_create_board` already does the lookup) and keep two non-unique indexes for query speed:
  - `INDEX ix_wc2026_board_states_email_country_diff (email, country_slug, difficulty)`
  - `INDEX ix_wc2026_board_states_guest_country_diff (guest_token, country_slug, difficulty)`
- Add `INDEX ix_wc2026_scores_guest_token (guest_token)` for the merge-on-login UPDATE.

### Identity model

Define a small helper in `main.py` (next to the existing WC helpers around line 8425):

```python
def _wc_player_identity(request: Request, db: Session):
    """Return (email, guest_token, fan_flag). Exactly one of email/guest_token is non-None."""
    user = get_current_user(request)
    if user:
        profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
        return user["email"], None, (profile.wc2026_fan if profile else None)
    if "guest_token" not in request.session:
        request.session["guest_token"] = str(uuid.uuid4())
    return None, request.session["guest_token"], request.session.get("wc2026_fan")
```

This is the *only* place that needs to know about the identity disambiguation. Every WC endpoint and the page route call it instead of `get_current_user` + `profile.wc2026_fan`.

### Endpoint behaviour changes

All seven WC API endpoints lose their `if not user: return 401` early return. They use `_wc_player_identity` and pass either `email=` or `guest_token=` into board helpers and queries:

- `GET  /api/wc2026/board/{slug}/{difficulty}` — works for guests; returns board keyed by guest_token.
- `POST /api/wc2026/board/{slug}/{difficulty}/reveal` — same identity logic; server-side cell-state validation unchanged.
- `POST /api/wc2026/board/{slug}/{difficulty}/flag` — same.
- `POST /api/wc2026/board/{slug}/{difficulty}/solve` — requires a fan flag (from profile or cookie); writes `wc2026_scores` row with whichever identity. **Apply guest-only anti-abuse here** (see below).
- `POST /api/wc2026/board/{slug}/{difficulty}/reset` — same identity logic.
- `POST /api/wc2026/board/{slug}/{difficulty}/new` — same.
- `POST /api/wc2026/set-fan` — for logged-in users, persist to `UserProfile.wc2026_fan` as today. For guests, persist to `request.session["wc2026_fan"]`. Same response shape.

### Anti-abuse

Two layers, both applied only when the identity is a guest_token:

1. **Per-IP daily cap on guest WC points.** Before awarding points in `/solve`, sum the day's guest-keyed `wc2026_scores.total_points` for the requesting IP and cap at **200 points/day per IP**. Solves still complete; excess points clamp to 0. Visible message to the player so they're not silently grinding for nothing.
2. **Per-cookie rate limit on `/solve`** via the existing `slowapi` `@limiter.limit` decorator: `5/minute` for guest solves is more than enough for any honest player and shuts down trivial scripted abuse.

We deliberately skip stricter measures (cookie-age requirement, solve-time floor, etc.) — the team has existing score-review channels for genuine concerns.

### Leaderboard query changes

- `_country_leaderboard(slug)` already aggregates `wc2026_scores` rows by something display-name-ish. Update it to include both email-keyed and guest_token-keyed rows in the country total. Where it currently renders a player row, keep a single combined "Guest contributions" row at the bottom showing the country's guest-earned total. Detail: this is informational, not ranked among individual players.
- `wc2026_lb_individuals` filters to `email IS NOT NULL`. No change to the rendering template.
- `wc2026_lb_countries` sums both identities (no filter needed since we want everything counted).

### Template changes (`wc2026_country.html`)

Replace the three-state banner at lines 9-29 with a four-state model:

1. Logged in, fan flag set → unchanged.
2. Logged in, no fan flag → unchanged (inline selector).
3. **Guest, fan flag set in cookie** (new) → "🏆 You're playing for [flag] [Country]! Log in to put your name on the biggest fans leaderboard." with a "Change team" link.
4. **Guest, no fan flag** (new) → fan-flag selector inline, *same widget as case 2*; on the country page, default the selector to the current country.

Replace the `wcc-play-gate` block at lines 96-99 with: render the board when fan_flag is set (regardless of identity); when no fan flag, show the selector inline above the board. No more "Log in to play" message.

After a guest solves (in `tametsi_wc.js`), surface a small celebratory toast that mentions both the points earned for the country *and* the "Log in to claim and join the biggest fans leaderboard" CTA.

### Merge-on-login

Extend the existing guest-token claim loop in `/auth/callback` (`main.py:1131-1138`):

```python
guest_token = request.session.pop("guest_token", None)
if guest_token:
    for model in [Score, RushScore, CylinderScore, ToroidScore, TentaizuScore, ReplayScore]:
        db.query(model).filter(
            model.guest_token == guest_token,
            model.user_email.is_(None),
        ).update({"user_email": email}, synchronize_session=False)

    # WC2026 score rows — same pattern, different column name
    db.query(WC2026Score).filter(
        WC2026Score.guest_token == guest_token,
        WC2026Score.email.is_(None),
    ).update({"email": email, "guest_token": None}, synchronize_session=False)

    # WC2026 board states — conflict-aware merge
    # If the logged-in user already has a board for the same (country_slug, difficulty),
    # prefer it and delete the guest's. Otherwise, claim the guest row.
    _claim_wc_boards(db, guest_token, email)

    db.commit()
```

`_claim_wc_boards` selects all guest board rows, then for each: if no existing email-keyed row at `(country_slug, difficulty)`, `UPDATE` to set `email` and null `guest_token`; otherwise `DELETE` the guest row. Implemented per-row because the count is bounded (max 48 countries × 2 difficulties = 96 rows).

Also clear the fan flag from session: if the user has no `UserProfile.wc2026_fan` but their session has `wc2026_fan`, copy it over.

### Out of scope

- Letting guests appear on the individual leaderboard under a custom handle.
- Cross-device guest persistence (cookie is per-browser).
- Captcha / proof-of-work on `/solve`.

### Build order

1. Migrations (guest_token columns + nullable email + new indexes).
2. `wc2026_board.get_or_create_board` accepts `(email=None, guest_token=None)`.
3. `_wc_player_identity` helper + apply across all WC endpoints.
4. Template changes for the four-state banner and removal of the play-gate.
5. Solve-side anti-abuse.
6. Merge-on-login extension.
7. Leaderboard query updates.
8. End-to-end smoke test (anonymous → solve → leaderboard → login → claim → leaderboard).

