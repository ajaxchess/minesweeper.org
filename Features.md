List of active features

F61 No-Guess Nonosweeper POTD

  Guarantee that every Puzzle of the Day (POTD) can be solved from
  the nonogram clues alone — no cell requires a blind guess.

  The current POTD generator places mines with a seeded RNG and has no
  solvability check. Some boards are ambiguous, requiring the player to
  guess a cell and risk an instant loss. This feature eliminates that.

  Approach
  ──────────────────────────────────────────────────────────────────────
  Add `isNonosweeperSolvable(rows, cols, mineSet)` to nonosweeper.js.
  The solver runs entirely in JavaScript, client-side, with no API
  changes required.

  The solver works in two stages:

  Stage 1 — Iterative line-solving (fast):
    Apply the "overlap" technique to every row and column.
    For each line, find the leftmost and rightmost valid placements of
    all runs given currently-known cells, then mark cells as definitely
    mine or definitely safe where the placements agree.
    Repeat until no progress. This resolves most well-designed puzzles.

  Stage 2 — Backtracking (completeness):
    If unknown cells remain after Stage 1, pick the first unknown cell.
    Branch: try it as a mine, then try it as safe.
    Recurse in each branch with full Stage 1 propagation.
    Count consistent solutions. Return true iff exactly one solution
    exists. Cap recursion depth at 30 to bound worst-case time.

  POTD generation
  ──────────────────────────────────────────────────────────────────────
  `generatePuzzle(seedStr, difficulty)` currently uses seedStr directly.
  Modify it to try seeds `seedStr + ':' + difficulty + ':0'` through
  `':49'` (50 candidates), returning the first board that passes
  `isNonosweeperSolvable`. If none pass (extremely rare), fall back to
  `':0'` (no change to observable puzzle for players who already played
  it before the feature launched, since that was the previous seed).

  The seed suffix approach ensures:
  - All existing solves remain valid (archive puzzle hashes don't change)
  - The fallback still produces a deterministic daily puzzle

  Random puzzles (non-POTD) do not require the guarantee — keep as-is.

  Performance target
  ──────────────────────────────────────────────────────────────────────
  Stage 1 only: < 5 ms per board on modern hardware
  With backtracking: < 50 ms per board (capped at depth 30)
  50 candidates × 50 ms = 2.5 s worst case (run async via setTimeout)

  See docs/NonosweeperNoGuessSolverSpec.md for the full algorithm spec.

F60 Android App

  Build the Minesweeper.org Android app using the existing React Native + Expo
  managed workflow project at mobile/app/ (shared with iOS).

  All game logic, screens, hooks, and services are already implemented as part
  of F58. Android-specific work covers:

  A1 — Platform-aware X-Client-Type header
    Update apiService.js to send android_app (vs ios_app) using Platform.OS.
    Update APISpec.md and main.py to accept and attribute android_app scores.

  A2 — Adaptive icon and Play Store assets
    Produce production-quality adaptive icon layers (foreground 1024×1024,
    background 1024×1024, monochrome 1024×1024) respecting the safe-zone
    rule (content in center 66% only).
    Produce feature graphic 1024×500 px (required by Play Store).

  A3 — Google Play Console setup
    Create app record, complete store listing (short/full description,
    icon, feature graphic, screenshots), content rating questionnaire,
    privacy policy URL (https://minesweeper.org/privacy).

  A4 — EAS service account
    Create Google Play service account with Release Manager role.
    Download JSON key to mobile/app/google-play-service-account.json
    (gitignored — never commit).

  A5 — EAS build and Play Store submission
    eas build --platform android --profile production → AAB
    eas submit --platform android --profile production --latest
    Internal track testing → promote to production.

  A6 — Android UX verification
    Hardware back button, edge-to-edge insets (SDK 55 default on Android 15+),
    keyboard behavior on Settings screen, tablet layout (10").

  See mobile/android/BuildPlan.md for full task list and risk items.

F59 Serve up Resume

F58 Basic iOS version

F57 PvP Beta — Hidden /pvpbeta route for live user testing
  A copy of the PvP matchmaking system at /pvpbeta (not linked from the main site).
  Uses separate matchmaking queues so beta players are isolated from the main /pvp pool.
  Game results are not saved to the leaderboard or ELO rankings.
  Includes standard, quick, and vs-bot sub-modes mirroring /pvp.

F56 Nonosweeper — Minesweeper meets Nonogram

  Overview
  ──────────────────────────────────────────────────────────────────────────────
  Nonosweeper is a hybrid daily puzzle that fuses Minesweeper with Nonogram
  (Picross) logic.  Instead of revealing numbers that count adjacent mines,
  the player is given row and column clues — nonogram-style — showing the
  sizes of consecutive mine groups in each line.  The goal is to deduce every
  mine's location from those clues, then left-click every safe cell without
  ever hitting a mine.  A new puzzle is generated for each difficulty level
  every day; the seed is deterministic so every player gets the same board.
  See: https://minesweeper.fandom.com/wiki/Nonosweeper

  Rules
  ──────────────────────────────────────────────────────────────────────────────
  Left-click   — Reveal a cell.
                  • If the cell is a mine → GAME OVER (💥).  All mines are
                    uncovered and wrongly-flagged safe cells are marked ❌.
                  • If the cell is safe → revealed (✓).
                  Clicking a revealed cell does nothing.

  Right-click  — Cycle the cell state:
                    hidden → flagged (💣) → uncertain (?) → hidden
                  Flagging does NOT reveal the cell.  It is cosmetic only
                  (helps the player track deduced mines).

  Win          — All non-mine cells have been revealed.  Remaining unflagged
                  mines are auto-flagged.  The win overlay shows elapsed time
                  and (on POTD) a score-submit form.

  Loss         — Any mine is left-clicked.  That cell shows 💥.  All other
                  mines are revealed; incorrectly flagged safe cells show ❌.
                  The player may retry the same board.

  No safe-first-click guarantee — use the nonogram clues to deduce safe
  cells before clicking.  Guessing is penalised only by a loss.

  Clue format  — Each row/column clue is a list of positive integers, e.g.
                  [3, 1, 2].  Each integer is a consecutive run of mines in
                  reading order (left→right for rows, top→bottom for cols).
                  Runs are separated by ≥1 safe cell.  A clue of [0] (no
                  mines in that line) is rendered as "—".

  Difficulty levels
  ──────────────────────────────────────────────────────────────────────────────
  Beginner:     8 × 8  grid,  16 mines  (~25 %)
  Intermediate: 10×10  grid,  35 mines  (~35 %)
  Expert:       15×15  grid,  75 mines  (~33 %)

  Puzzle generation
  ──────────────────────────────────────────────────────────────────────────────
  Algorithm: seeded Fisher-Yates shuffle, same RNG as Tentaizu.
  RNG:    mulberry32 (identical implementation to tentaizu.js).
  Seed:   strSeed(dateISO + ':' + difficulty)
            e.g. strSeed("2026-03-27:beginner")
  The seed string is hashed to a 32-bit unsigned integer via FNV-1a, then
  fed to mulberry32.  The first `mines` indices from the shuffled index
  array [0 … rows*cols-1] are the mine positions.
  Row and column clues are computed from the mine positions after generation.

  Scoring & leaderboard
  ──────────────────────────────────────────────────────────────────────────────
  • Time-based (lower is better), measured in whole seconds from first click
    to win.
  • Leaderboard is per-difficulty per-date (POTD only).  Random puzzles are
    not scored.
  • Top 20 scores are returned by the API; top 3 receive medal icons.
  • Logged-in users submit under their display name; guests submit a custom
    name stored in localStorage.  Each guest session is identified by a UUID
    cookie (guest_token).

  Database table: nonosweeper_scores
  ──────────────────────────────────────────────────────────────────────────────
  Column       Type           Notes
  id           INTEGER PK     auto-increment
  name         VARCHAR(32)    display name, NOT NULL
  user_email   VARCHAR(256)   NULL for guests, indexed
  puzzle_date  VARCHAR(10)    YYYY-MM-DD, NOT NULL
  difficulty   VARCHAR(16)    beginner|intermediate|expert, NOT NULL
  time_secs    INTEGER        elapsed seconds, NOT NULL
  guest_token  VARCHAR(36)    UUID, NULL for registered users, indexed
  created_at   DATETIME       UTC, default now()

  Composite index: (puzzle_date, difficulty, time_secs) for leaderboard
  queries.

  Routes
  ──────────────────────────────────────────────────────────────────────────────
  GET  /nonosweeper
       Renders today's POTD.  Optional ?date=YYYY-MM-DD query param to view
       a past puzzle (leaderboard shown but score submission disabled).

  GET  /nonosweeper/{YYYY-MM-DD}
       Permalink for a specific date's puzzle.  Redirects to /nonosweeper if
       the date format is invalid.

  POST /api/nonosweeper-scores          (rate-limited 10/min)
       Body: { name, puzzle_date, difficulty, time_secs }
       Saves a completed puzzle score.  Returns { ok: true, id }.

  GET  /api/nonosweeper-scores/{date}?difficulty=beginner
       Returns top-20 scores for the given date+difficulty as JSON array.

  Frontend files
  ──────────────────────────────────────────────────────────────────────────────
  templates/nonosweeper.html   — Jinja2 page template (extends base.html)
  static/js/nonosweeper.js     — All game logic, rendering, leaderboard

  Board rendering
  ──────────────────────────────────────────────────────────────────────────────
  CSS Grid layout:
    • Column 0:          row-clue cells (right-aligned numbers)
    • Columns 1…cols:    game cells
    • Row 0:             col-clue cells (bottom-aligned numbers) + corner spacer
    • Rows 1…rows:       one row-clue cell + cols game cells
  Grid gap: 2 px.  Cell size: 34 px (CSS variable --nn-cell-size).
  Column clues stack vertically; row clues stack horizontally.
  A "—" is rendered for zero-mine rows/columns.

  Navigation
  ──────────────────────────────────────────────────────────────────────────────
  Add a Nonosweeper mega-card to the Puzzles mega-menu in base.html, after
  the existing Mosaic cards.  Icon: 🔢.  Active state: mode=='nonosweeper'.

F55 Globesweeper — Minesweeper on a Goldberg Polyhedron

  Overview
  ──────────────────────────────────────────────────────────────────────────────
  Minesweeper played on the faces of a Goldberg polyhedron — a 3D globe-shaped
  solid with exactly 12 pentagonal faces and a variable number of hexagonal faces.
  The player rotates the globe with the mouse (or touch) to see all sides and
  clicks faces to reveal or flag them.  See:
    https://en.wikipedia.org/wiki/Goldberg_polyhedron

  Mathematics — Goldberg polyhedra
  ──────────────────────────────────────────────────────────────────────────────
  A Goldberg polyhedron GP(a, b) is characterised by the Goldberg-Coxeter
  parameter T = a² + ab + b², where a ≥ 1, b ≥ 0.

    Total faces  F = 10T + 2
    Pentagon faces  = 12  (always — at the 12 icosahedron vertices)
    Hexagon  faces  = F − 12 = 10T − 10

  Enumeration of small valid T values (a ≥ 1, b ≥ 0):

    T  1  → F  12  (dodecahedron — all pentagons, GP(1,0))
    T  3  → F  32  (truncated icosahedron / soccer ball, GP(1,1))
    T  4  → F  42  GP(2,0)
    T  7  → F  72  GP(2,1)
    T  9  → F  92  GP(3,0)
    T 12  → F 122  GP(2,2)
    T 13  → F 132  GP(3,1)
    T 16  → F 162  GP(4,0)
    T 19  → F 192  GP(3,2)
    T 21  → F 212  GP(4,1)
    T 25  → F 252  GP(5,0)
    T 27  → F 272  GP(3,3)
    T 28  → F 282  GP(4,2)
    T 31  → F 312  GP(5,1)
    T 36  → F 362  GP(6,0)
    T 37  → F 372  GP(4,3)
    T 39  → F 392  GP(5,2)
    T 43  → F 432  GP(6,1)
    T 48  → F 482  GP(4,4)
    T 49  → F 492  GP(7,0)
    T 52  → F 522  GP(5,3) [note: T=52 is NOT a valid Goldberg T; listed for completeness — always validate]
    T 57  → F 572  GP(6,2)
    T 61  → F 612  GP(7,1)
    T 63  → F 632  GP(5,4) [validate]
    T 75  → F 752  GP(5,5)

  Not every integer is a valid T. T is valid iff it can be expressed as a²+ab+b²
  for integers a ≥ 1, b ≥ 0.  The custom page must validate this and offer only
  valid T values (enumerate via brute force over a ∈ [1,10], b ∈ [0,a]).

  Board sizes
  ──────────────────────────────────────────────────────────────────────────────
  Beginner:     GP(1,1)  T=3   F=32   mines=4   (~12.5 %)
  Intermediate: GP(2,1)  T=7   F=72   mines=8   (~11.1 %)
  Expert:       GP(5,0)  T=25  F=252  mines=50  (~19.8 %)
  Custom:       any valid T ∈ {1,3,4,7,9,12,13,16,19,21,25,27,28,31,36,37,39,
                                43,48,49,57,61,75} (up to T=75 = F=752); user
                selects T from a dropdown and enters a mine count.

  Geometry generation — goldberg.js
  ──────────────────────────────────────────────────────────────────────────────
  Algorithm: dual of a geodesic sphere (Class I for b=0, Class II for b=a,
  Class III otherwise).

  Step 1 — Subdivide the icosahedron.
    Start with the 20 triangular faces of a regular icosahedron.
    For each triangular face with vertices P0, P1, P2, subdivide it into T
    smaller triangles using the Goldberg-Coxeter (a,b) lattice:
      for i in 0..a:
        for j in 0..(a-i):
          place vertex at barycentric coords (1−u−v, u, v) where
          u = (i*b + j*a)/(a*a + a*b + b*b) style coords (use the
          standard class-I/II/III subdivision pattern for the (a,b) pair)
    After placing all subdivision vertices, project each onto the unit sphere
    (normalise to radius 1).
    Merge vertices that are within ε = 1e-9 of each other (shared icosahedron
    edges produce duplicate vertices before merging).

  Step 2 — Build the dual polyhedron (= the Goldberg polyhedron).
    For each unique vertex V of the subdivided + projected geodesic sphere:
      Collect all triangular faces that contain V (the "fan" around V).
      The valence of V is 5 (for the 12 original icosahedron vertices) or 6
      (for all others) — giving pentagonal and hexagonal Goldberg faces.
      Sort the fan faces in angular order around V to get an ordered face polygon.
      The centroid of each fan triangle (projected to unit sphere) becomes a
      vertex of the Goldberg face.
    Each Goldberg face is stored as an ordered list of unit-sphere vertex coords.

  Step 3 — Compute adjacency.
    Two Goldberg faces share an edge iff their vertex lists share exactly 2
    consecutive vertices (modulo cyclic order).  Build adjacency list:
      faceAdj[i] = [j, k, l, ...]   // indices of neighbouring Goldberg faces
    Pentagons have 5 neighbours; hexagons have 6.

  Step 4 — Canonical face index for hashing.
    Sort all F face centroids lexicographically by (x, y, z) rounded to 6 dp.
    Assign 0-based indices in that order.  This gives a deterministic,
    orientation-independent canonical ordering.

  Step 5 — Export.
    goldberg(a, b) returns:
      { faces, adj, T, F, pentagons }
    where:
      faces     — Array[F] of { verts: [{x,y,z}], centroid: {x,y,z}, isPentagon }
      adj       — Array[F] of number[]   (neighbour indices)
      T         — Goldberg parameter
      F         — face count (= 10T+2)
      pentagons — Set of 12 face indices that are pentagons

  Rendering — globesweeper.js + Three.js
  ──────────────────────────────────────────────────────────────────────────────
  Library: Three.js r165 (loaded from CDN or bundled in static/js/vendor/).

  Scene setup:
    - WebGLRenderer, antialiased, transparent background — fills #globe-canvas
      (a <canvas> element); resized to container on window resize
    - PerspectiveCamera, FOV 45°, near 0.1, far 100
    - Camera positioned at (0, 0, 3.5) looking at origin
    - AmbientLight (0xffffff, 0.6) + DirectionalLight (0xffffff, 0.8) at (5,5,5)
    - Globe sits at origin; faces are at radius ~1.0

  Globe mesh:
    Each Goldberg face is rendered as a flat filled polygon (fan triangulation
    from centroid) scaled to radius 0.98 (slightly inside the unit sphere to
    leave visible gaps between faces acting as cell borders).
    Each face is a separate THREE.Mesh with its own MeshLambertMaterial so its
    colour can be updated independently on state change.
    Face polygon vertices:
      verts projected to unit sphere, then scaled to 0.98 before triangulation.
      Fan triangulate: centroid_at_0.98 → vert[0] → vert[1], vert[1] → vert[2], …
    Border lines: each face edge rendered as a THREE.Line at radius 1.001
      (slightly outside) in the border colour.

  Rotation / interaction:
    - THREE.OrbitControls (or a manual quaternion-based drag implementation if
      OrbitControls is not bundled) attached to the renderer's domElement.
    - Zoom disabled (fixed camera distance); auto-rotation disabled.
    - On pointerdown + pointermove: rotate the globe group.
    - Distinguish click vs drag: if total pointer travel < 6 px, treat as a click.

  Face picking (raycasting):
    - THREE.Raycaster with mouse coordinates normalised to [-1,1].
    - Cast against all face meshes; take the nearest intersection.
    - Left-click (or tap): reveal the face.
    - Right-click / long-press (500 ms): cycle flag → question → clear.

  Face visual states (colours from CSS variables read at JS init time):
    hidden      — --glob-hidden   (default: same family as --cell-hidden)
    revealed    — --glob-rev      (depends on mine count — see number colours)
    flagged     — --glob-hidden with 🚩 / 🌷 text overlay
    question    — --glob-hidden with ? overlay
    mine        — --glob-mine
    detonated   — --glob-detonated
  Number overlays on revealed faces:
    Three.js Sprite with a Canvas2D texture (draw digit + colour); re-used from
    a small sprite pool; same NUM_COLORS_* palettes as minesweeper.js.
    Blank revealed faces (0 mines adjacent) show no sprite.
  Mine/flag emoji overlay: same Sprite approach; uses getMineEmoji() /
    getFlagEmoji() values from minesweeper.js.

  Animation:
    requestAnimationFrame loop calls renderer.render(); OrbitControls.update().
    On first win/loss: brief camera "pulse" scale 1→1.05→1 over 0.3 s.

  Game logic — globesweeper.js
  ──────────────────────────────────────────────────────────────────────────────
  State per face: HIDDEN | REVEALED | FLAGGED | QUESTION | MINE | DETONATED
  mineSet: Set of face indices containing mines.
  adjCount[i]: number of mine-containing neighbours of face i (pre-computed).

  generateMines(faces, adj, count, safeIdx):
    Randomly sample `count` faces from all faces except safeIdx (first click).
    Regenerate if safeIdx would be a mine (guarantee safe first click).
    Returns Set of mine indices.

  revealFace(idx):
    If HIDDEN: mark REVEALED.
    If adjCount[idx] === 0: BFS flood-fill — reveal all reachable zero-count
      HIDDEN faces and their HIDDEN non-mine neighbours.
    If mine: mark DETONATED; reveal all mines; game over.

  boardToHash(mineSet, F):
    Build bit-array of length F; bit i = 1 iff face i is a mine.
    Base64url-encode the byte array → hash string.

  hashToBoard(hash, F):
    Decode base64url → bytes → bit-array → Set of mine indices.

  Key exported functions:
    initGlobe(a, b, mineCount, canvasId)   — build geometry + start render loop
    revealFace(idx), flagFace(idx)          — game actions
    boardToHash, hashToBoard
    getMineEmoji, getFlagEmoji             — imported from minesweeper.js

  Routes
  ──────────────────────────────────────────────────────────────────────────────
    GET /globesweeper               → beginner (T=3, 32 faces, 4 mines)
    GET /globesweeper/intermediate  → intermediate (T=7, 72 faces, 8 mines)
    GET /globesweeper/expert        → expert (T=25, 252 faces, 50 mines)
    GET /globesweeper/custom        → custom (select T + mine count)
    GET /globesweeper/leaderboard   → best times per mode

  Templates
  ──────────────────────────────────────────────────────────────────────────────
    templates/globesweeper.html              — shared base template (parameterised)
    templates/globesweeper_intermediate.html
    templates/globesweeper_expert.html
    templates/globesweeper_custom.html
    templates/globesweeper_leaderboard.html

  Template structure (globesweeper.html):
    - data-a="{{ a }}" data-b="{{ b }}" data-mines="{{ mines }}" on <body>
      (or passed as JS constants in a <script> block)
    - <div id="globe-wrap"> containing <canvas id="globe-canvas">
      styled to fill a fixed-height container (min 420 px, max 700 px on desktop)
    - Game info bar above canvas: mine counter, timer, reset button (same .stat
      layout as classic minesweeper)
    - Controls hint below canvas: "Drag to rotate · Left-click to reveal ·
      Right-click to flag"
    - Win/loss overlay (same .game-over-overlay pattern as other variants)
    - Score submission form (same pattern as cylinder/toroid)

  Custom page (globesweeper_custom.html):
    - <select id="t-select"> populated from VALID_T list (JS constant):
        T=1 (12 faces), T=3 (32 faces), T=4 (42 faces), T=7 (72 faces), …
      Label format: "T=3 — 32 faces (truncated icosahedron)"
      Special names: T=1 "dodecahedron", T=3 "truncated icosahedron"
    - Face count display updates on change: "This board has F faces (12 pentagons,
      F-12 hexagons)."
    - Mine count <input type="number"> min=1 max=F-1; default = floor(F*0.15).
    - "Play" button generates new game and renders globe.
    - URL after starting: /globesweeper/custom?t=7&mines=12 (pushState, no reload)

  JavaScript files
  ──────────────────────────────────────────────────────────────────────────────
  static/js/vendor/three.min.js      — Three.js r165 (copy to avoid CDN dependency)
  static/js/goldberg.js              — Goldberg polyhedron geometry generator
                                        exports: goldberg(a, b)
  static/js/globesweeper.js          — game logic + Three.js scene
                                        depends on: three.min.js, minesweeper.js
                                          (for getMineEmoji/getFlagEmoji/getNumColors)

  Database
  ──────────────────────────────────────────────────────────────────────────────
  New table: globesweeper_scores
    id           INT AUTO_INCREMENT PRIMARY KEY
    mode         VARCHAR(20)    -- 'beginner' | 'intermediate' | 'expert' | 'custom'
    t_param      INT            -- Goldberg T value (e.g. 3, 7, 25)
    face_count   INT            -- 10*T+2 (denormalised for query convenience)
    board_hash   VARCHAR(128)   -- base64url mine bitfield; NULL for random boards
    user_email   VARCHAR(255)
    display_name VARCHAR(64)
    time_ms      INT
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP

  API
  ──────────────────────────────────────────────────────────────────────────────
    POST /api/globesweeper-scores
         Body: { time_ms, mode, t_param, face_count, board_hash, display_name }
         Auth: logged-in user (email from session); guests submit with display_name
    GET  /api/globesweeper-scores/{mode}
         Returns top 20 for that mode (today + all-time), ordered by time_ms ASC

  Nav / sitemap
  ──────────────────────────────────────────────────────────────────────────────
  Add Globesweeper to the Variants group in the mega menu:
    icon 🌍, title "Globesweeper", desc "Minesweeper on a rotating 3D globe"
  Add to sitemap.xml:
    /globesweeper, /globesweeper/intermediate, /globesweeper/expert,
    /globesweeper/custom, /globesweeper/leaderboard

  Skin support
  ──────────────────────────────────────────────────────────────────────────────
  CSS variables for Three.js colours (read by globesweeper.js at scene init via
  getComputedStyle(document.documentElement)):
    --glob-hidden         hidden face fill colour
    --glob-hidden-border  edge line colour
    --glob-rev            revealed face fill (blank)
    --glob-mine           mine face fill
    --glob-detonated      detonated face fill
  Each skin block in style.css gets a glob-specific override section.
  Default (dark skin) values:
    --glob-hidden:         #2a3a5c
    --glob-hidden-border:  #3a5278
    --glob-rev:            #111b2a
    --glob-mine:           #7a0000
    --glob-detonated:      #c00000
  Number colours re-use NUM_COLORS_* from minesweeper.js (passed as JS array).
  getMineEmoji() / getFlagEmoji() from minesweeper.js drive face overlays.

  No-guess mode
  ──────────────────────────────────────────────────────────────────────────────
  Deferred to a follow-on feature.  No-guess generation on a graph of irregular
  pentagon/hexagon face valences is non-trivial.

  Performance notes
  ──────────────────────────────────────────────────────────────────────────────
  - For T≤25 (F≤252) geometry generation runs in < 5 ms in a modern browser.
  - For T=75 (F=752) generation takes ~20–40 ms; acceptable for custom play.
  - Cache the generated geometry object by (a,b) key in a module-level Map so
    resetting the board does not recompute geometry.
  - Each face mesh is a separate THREE.Mesh; for T=75 that is 752 meshes —
    within WebGL draw-call budgets for desktop.  Consider merging into a single
    BufferGeometry with per-face vertex colours for mobile optimisation (future).

F54 Admin Web Traffic Dashboard

  Purpose
  ──────────────────────────────────────────────────────────────────────────────
  Give admins a daily view of web traffic parsed directly from Apache access
  logs — request counts by HTTP status code, unique visitor IPs, plus the
  existing hourly network bandwidth and HTTP-request charts from the operations
  page, all in one place.

  Data collection
  ──────────────────────────────────────────────────────────────────────────────
  - APScheduler job `collect_web_traffic_stats` runs at 1 AM UTC daily
  - Parses both log files with glob: /var/log/apache2/minesweeper.org-ssl-access.log*
    (covers current log and .1 rotation in case log rotates mid-day)
  - Filters lines to the previous calendar day (UTC)
  - Counts requests per tracked HTTP status code:
      2xx: 200, 201, 206   |  1xx: 101
      3xx: 302, 304, 307   |  4xx: 403, 404, 405, 422   |  5xx: 500, 503
  - Counts unique client IPs (unique visitors proxy)
  - Upserts one row per day into web_traffic_stats table

  Backfill
  ──────────────────────────────────────────────────────────────────────────────
  - On startup, a daemon thread calls `_backfill_web_traffic()` which processes
    all days from 2026-03-25 to yesterday that are not yet in the DB
  - Idempotent: skips days already present

  Database model: WebTrafficStats
  ──────────────────────────────────────────────────────────────────────────────
  Table: web_traffic_stats
  Fields: id, stat_date (unique Date), total_requests, unique_ips,
          http_200/201/206/101/302/304/307/403/404/405/422/500/503, recorded_at

  Admin page: /admin/web_traffic
  ──────────────────────────────────────────────────────────────────────────────
  - Linked from the main /admin nav bar as "🌐 Web Traffic"
  - Chart 1 (full-width line): Total Requests + Unique IPs per day
  - Chart 2 (stacked bar): 2xx success codes + 101 per day
  - Chart 3 (stacked bar): 3xx redirect codes per day
  - Chart 4 (full-width stacked bar): 4xx + 5xx error codes per day
  - Chart 5 (line): Hourly network bandwidth (from ServerStats, last 48 h)
  - Chart 6 (line): Hourly HTTP requests (from ServerStats, last 48 h)
  - Data table: all days newest-first with comma-formatted numbers

  Template: templates/admin_web_traffic.html
  Route:    GET /admin/web_traffic (admin-only, 403 otherwise)

F53 Daily Archive Leaderboard Pages

  Purpose
  ──────────────────────────────────────────────────────────────────────────────
  Provide permanently-addressable, fully server-rendered (no JS required) daily
  high-score pages for Beginner, Intermediate, and Expert minesweeper.  These
  pages are spider-friendly and serve as a historical record of top scores by
  authenticated users for each calendar day.

  URL scheme
  ──────────────────────────────────────────────────────────────────────────────
  /beginner/<YYYY-MM-DD>/guess          — Beginner, standard (guess allowed)
  /beginner/<YYYY-MM-DD>/no_guess       — Beginner, no-guess mode
  /intermediate/<YYYY-MM-DD>/guess
  /intermediate/<YYYY-MM-DD>/no_guess
  /expert/<YYYY-MM-DD>/guess
  /expert/<YYYY-MM-DD>/no_guess

  Index / date-picker page
  ──────────────────────────────────────────────────────────────────────────────
  /archive                              — Archive index page
    - Date input (defaults to today) + a "Go" button
    - Mode tabs: Beginner / Intermediate / Expert
    - Guess toggle: Standard / No-Guess
    - On submit: navigates to /<mode>/<date>/<guess|no_guess>
    - Lists the most recent 30 days that have at least one score as links
      (one list per mode, but driven by a single combined query for speed)

  Score selection rules
  ──────────────────────────────────────────────────────────────────────────────
  - Authenticated users only: WHERE user_email IS NOT NULL
    (end-of-day cron already removes guest rows, but the query enforces it)
  - One row per player: best time_ms (or time_secs * 1000 if time_ms is NULL)
  - Date window: created_at >= <date> 00:00:00 UTC
                 created_at <  <date+1> 00:00:00 UTC
  - mode = <beginner|intermediate|expert>
  - no_guess = <True for no_guess path, False for guess path>
  - ORDER BY effective_ms ASC
  - LIMIT 100

  Page content (server-rendered HTML, no JS required)
  ──────────────────────────────────────────────────────────────────────────────
  1. h1: "Beginner Scores — 2026-03-25" (mode + date)
  2. Mode tabs: Beginner | Intermediate | Expert (links, not JS tabs)
  3. Guess toggle: Standard | No-Guess (links)
  4. Score table columns:
       # | Name | Time | Board | Mines | 3BV | 3BV/s | Eff | Board Hash
     - # → rank (1-based)
     - Name → display name (user_email masked)
     - Time → time_ms/1000 formatted to 3 dp (e.g. 12.345s), fallback time_secs
     - Board → rows×cols (e.g. 9×9)
     - Mines → mines count
     - 3BV → bbbv (or — if null)
     - 3BV/s → bbbv / (time_ms/1000), 2 dp (or —)
     - Eff → bbbv / (left_clicks + chord_clicks) * 100%, 0 dp (or —)
     - Board Hash → link to /variants/replay?hash=...&rows=...&cols=...&mines=...
       if board_hash is not null, otherwise —
  5. Play buttons below table:
       ← Play Beginner | Play Intermediate | Play Expert
  6. Explanation paragraph (rendered from translation key):
       "These are the best times posted by registered players on <date>.
        Guest scores are not included. Each player appears once — their
        personal best for the day."

  404 handling
  ──────────────────────────────────────────────────────────────────────────────
  - Invalid date string → 404
  - Valid date but no scores → render page with empty table and a
    "No scores recorded for this day." message (not a 404)

  SEO
  ──────────────────────────────────────────────────────────────────────────────
  - <title>: "Beginner Daily Scores — 2026-03-25 | minesweeper.org"
  - <meta description>: "Top Beginner minesweeper times for 2026-03-25.
      Server-rendered leaderboard of registered players."
  - <link rel="canonical"> pointing to the canonical URL
  - <link rel="prev"/"next"> for date pagination (previous/next day with scores)
  - robots: index, follow (public pages)
  - /archive: index page, robots: index, follow
  - Add all 6 daily-archive URL patterns to sitemap.xml with
    lastmod = today and priority = 0.6

  Routes (main.py)
  ──────────────────────────────────────────────────────────────────────────────
  GET /archive
      → render templates/archive_index.html
      Query: for each mode, fetch last 30 distinct dates with ≥1 auth score

  GET /{mode}/{date}/{guess_mode}
      where mode ∈ {beginner, intermediate, expert}
      and   date matches r"\d{4}-\d{2}-\d{2}"
      and   guess_mode ∈ {guess, no_guess}
      → render templates/archive_day.html
      Validates date; returns 404 on invalid date string.

  Template files
  ──────────────────────────────────────────────────────────────────────────────
  templates/archive_index.html  — date picker + recent days list
  templates/archive_day.html    — static score table for one day

  Translation keys needed (add to all 17 languages)
  ──────────────────────────────────────────────────────────────────────────────
  archive_title          "Daily Archive"
  archive_desc           "Browse daily high-score leaderboards for each difficulty."
  archive_go             "Go"
  archive_recent         "Recent days"
  archive_no_scores      "No scores recorded for this day."
  archive_explanation    "These are the best times posted by registered players
                          on {date}. Guest scores are not included. Each player
                          appears once — their personal best for the day."
  archive_standard       "Standard"
  archive_no_guess       "No-Guess"

  Notes
  ──────────────────────────────────────────────────────────────────────────────
  - Do NOT add hexsweeper or other variants to this feature; keep it to the
    core three difficulties (beginner / intermediate / expert).
  - The /archive index page is the entry point linked from the leaderboard page.
  - Mode tabs use <a href="..."> links so they work without JavaScript.
  - The score table uses existing .lb-table CSS class for visual consistency.

F52 Hexsweeper — Hexagonal Minesweeper Variant
  Minesweeper played on a hexagonal-shaped board of pointy-top hexagonal tiles.
  Each cell has 6 neighbours instead of 8, which changes strategy significantly.

  ── Board sizes (hexagonal boards — axial radius R, diameter = 2R-1) ──────────
    Beginner:     R=5  → diameter 9,  61 cells, ~8 mines  (13% — matches beginner ratio)
    Intermediate: R=7  → diameter 13, 127 cells, ~20 mines (16% — matches intermediate ratio)
    Expert:       R=10 → diameter 19, 271 cells, ~56 mines (21% — matches expert ratio)
  All mine counts are tunable via HEXSWEEPER_MINES dict in settings.py.
  A hexagonal board of radius R contains 3R²-3R+1 cells.
  Cell set: all axial coords (q, r) where max(|q|, |r|, |q+r|) ≤ R-1.

  ── Coordinate system ────────────────────────────────────────────────────────
  Use axial coordinates (q, r); the third cube coordinate s = -q-r is implicit.
  Six neighbours of (q, r): (q+1,r), (q-1,r), (q,r+1), (q,r-1), (q+1,r-1), (q-1,r+1)
  Canonical cell index for hashing: sort cells by (r, q) then assign 0-based index.

  ── Rendering ────────────────────────────────────────────────────────────────
  Render using SVG (inline in a <div id="hex-board">).
  Use pointy-top hexagons with hex size S px (default S=28 for beginner, scaled for larger).
  Pixel center of axial cell (q, r):
    x = S * √3 * (q + r/2)
    y = S * 3/2 * r
  SVG origin offset so board is centred in the viewport.
  Each cell is a <polygon points="…"> with 6 vertices.
  Cell states via CSS class: .hx-hidden, .hx-revealed, .hx-flagged,
    .hx-question, .hx-mine, .hx-mine-detonated, .hx-n1…hx-n6
  Left-click: reveal; Right-click / long-press: cycle flag → question → clear.
  First click is always safe (regenerate board if needed).

  ── Hash / board encoding ─────────────────────────────────────────────────────
  Same approach as existing board-generator:
    Sort cells by canonical index (r asc, q asc).
    Build a bit-array: bit i = 1 if cell i is a mine.
    Base64url-encode the byte array → board hash string.
  Decode: same process in reverse.
  Hash is shown as a permalink after the first reveal, same as /variants/replay/.

  ── Routes ───────────────────────────────────────────────────────────────────
    GET /hexsweeper               → beginner (R=5, 8 mines)
    GET /hexsweeper/intermediate  → intermediate (R=7, 20 mines)
    GET /hexsweeper/expert        → expert (R=10, 56 mines)
    GET /hexsweeper/custom        → custom (form: radius 3–15, mine count)
    GET /hexsweeper/generator     → hex board generator (click cells to place mines,
                                    shows hash + mine count, generates replay link)
    GET /hexsweeper/leaderboard   → best times per mode

  ── Templates ────────────────────────────────────────────────────────────────
    templates/hexsweeper.html          — shared base template (parameterised)
    templates/hexsweeper_intermediate.html
    templates/hexsweeper_expert.html
    templates/hexsweeper_custom.html
    templates/hexsweeper_generator.html
    templates/hexsweeper_leaderboard.html

  ── JS ───────────────────────────────────────────────────────────────────────
  static/js/hexsweeper.js — single JS file for all hex game pages.
  Key functions:
    generateHexCells(R)            → sorted array of {q,r} objects (canonical order)
    hexCenter(q, r, S)             → {x, y} pixel center
    hexPolygonPoints(cx, cy, S)    → SVG points string for pointy-top hex
    buildSVGBoard(cells, S)        → creates <polygon> elements, wires click/rightclick
    generateMines(cells, count, safeIdx)  → Set of mine indices (avoids safeIdx)
    countNeighbourMines(idx, mineSet, cells, cellIndex) → integer 0–6
    revealCell(idx)                → flood-fill BFS for zero-count cells
    boardToHash(mineSet, cells)    → base64url string
    hashToBoard(hash, cells)       → Set of mine indices
    renderCell(idx)                → updates <polygon> class + <text> child
    getMineEmoji() / getFlagEmoji() → respects active skin (🌸/🌷 for flower, etc.)

  ── Database ─────────────────────────────────────────────────────────────────
  New table: hexsweeper_scores
    id          INT AUTO_INCREMENT PRIMARY KEY
    mode        VARCHAR(20)   -- 'beginner' | 'intermediate' | 'expert' | 'custom'
    board_hash  VARCHAR(128)  -- NULL for daily/random; set for hash-based boards
    user_email  VARCHAR(255)
    display_name VARCHAR(64)
    time_ms     INT
    no_guess    TINYINT DEFAULT 0
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP

  ── API ──────────────────────────────────────────────────────────────────────
    POST /api/hexsweeper-scores          → submit score (time_ms, mode, board_hash, display_name)
    GET  /api/hexsweeper-scores/{mode}   → leaderboard for mode (top 20, today + all-time)

  ── Nav / sitemap ────────────────────────────────────────────────────────────
  Add Hexsweeper to the Variants group in the mega menu (non-classic nav).
  Add /hexsweeper, /hexsweeper/intermediate, /hexsweeper/expert,
      /hexsweeper/custom, /hexsweeper/leaderboard to sitemap.xml.

  ── Skin support ─────────────────────────────────────────────────────────────
  SVG cells styled via CSS variable overrides: --hex-hidden, --hex-revealed,
  --hex-mine, --hex-border, --hex-text. Each existing skin (dark, light,
  tentaizu, flower/flower-light, classic) gets a hex-specific colour block
  in style.css. getMineEmoji() / getFlagEmoji() from minesweeper.js apply.

  ── No-guess mode ────────────────────────────────────────────────────────────
  Deferred to a follow-on feature — hex no-guess generation is non-trivial.
  Board generator will note whether a board is logically solvable.

F51 Blog post announcing the Flower Garden theme
  - Write a blog entry at /blog/flower-garden-theme announcing the new 🌸 skin
  - Cover: what it is (night garden / day garden), how to activate (theme picker
    in the More menu or ?theme=flower URL param), what changed (mines = 🌸,
    flags = 🌷, deep plum night palette / sage green day palette)
  - Include a screenshot showing the day and night variants side by side
  - Target audience: returning players who might not notice the new theme
  - Assign to Bill

F50 Flower Garden Theme (dark night-garden + light day-garden)
  - New skin pair: `flower` (night) and `flower-light` (day), following the
    dark/light auto-switch pattern in resolveDefaultSkin (base.html)
  - Auto-switches flower-light during 06:00–20:00 local time; flower at night
  - User can pin either variant via the theme selector (localStorage key "skin")
  - Mine icon: 🌸 (cherry blossom) replaces 💣 in all game JS files
      getMineEmoji() already checks data-skin for tentaizu (⭐) — add flower check
      Files: minesweeper.js, cylinder.js, toroid.js, rush.js, duel.js,
             spectate.js, replay.js (and any inline assignments)
  - Flag icon: 🌷 (tulip on stem) replaces 🚩 in all game JS files
      Same files as mine icon — replace el.textContent = '🚩' with getFlagEmoji()
      helper that returns '🌷' for flower/flower-light, '🚩' otherwise
  - CSS — `flower` (dark night-garden palette):
      Background: deep plum / midnight green (#1a0d2e, #0d1f0d)
      Cells hidden: mossy dark green; revealed: soft dark cream
      Numbers: warm botanical colors replacing the standard blue/green/red set
      Mine cell background: deep burgundy (consistent with current dark skin)
      Detonated cell: dark rose
  - CSS — `flower-light` (day-garden palette):
      Background: soft sage / pale petal (#f0f5e8, #fdf6f0)
      Cells hidden: light sage green; revealed: warm white
      Numbers: rich botanical greens/pinks/purples
      Mine cell background: rose pink
      Detonated cell: vivid coral
  - Mega menu: add "🌸 Flower Garden" to the skin switcher (non-classic nav)
  - base.html resolveDefaultSkin: extend to respect flower/flower-light pair
    when stored skin is one of the flower variants
  - Skin name mapping: "flower" → "flower-light" for daytime auto-switch
    (mirror the "dark" → "light" mapping already in place)

F49 Purpose-built og:image for Rush (1200×630)
  - Replace static/img/og-rush.png with a purpose-built 1200×630 image
  - Image should clearly represent Minesweeper Rush: the cascading row mechanic,
    timer/score display, dark theme consistent with the Rush skin
  - Used as og:image and twitter:image on all 3 Rush pages:
    /rush, /rush/how-to-play, /rush/leaderboard
  - Current placeholder: RushOGFirstAttempt.png (cropped from 1443×700 screenshot)

F48 Purpose-built og:image for Mosaic (1200×630)
  - Replace static/img/og-mosaic.png with a purpose-built 1200×630 image
  - Image should clearly represent the Mosaic game: filled black/white grid
    with number clues, showing a partially or fully solved puzzle
  - Used as og:image and twitter:image on all 5 Mosaic pages:
    /mosaic, /mosaic/standard, /mosaic/custom, /mosaic/how-to-play,
    /mosaic/replay
  - Current placeholder: MosaicExample.png (small, square — not ideal)

F47 Purpose-built og:image for Tentaizu (1200×630)
  - Replace static/img/og-tentaizu.png with a purpose-built 1200×630 image
  - Image should clearly represent the Tentaizu game: 7×7 star-placement grid,
    number clues, dark/space theme consistent with the Tentaizu skin
  - Used as og:image and twitter:image on all 5 Tentaizu pages:
    /tentaizu, /tentaizu/easy-5x5-6, /tentaizu/how-to-play,
    /tentaizu/strategy, /tentaizu/archive
  - Current placeholder: screenshot crop from TentaizuPuzzle20260320Equinox.png

F46 OpenTelemetry Instrumentation for AWS Bedrock Observability
  - telemetry.py: setup_telemetry(app, db_engine) initialises OTLP tracing; no-op when
    OTEL_EXPORTER_OTLP_ENDPOINT is unset so dev environments need no extra infrastructure
  - Instruments FastAPI (every HTTP request → span) via opentelemetry-instrumentation-fastapi
  - Instruments SQLAlchemy (every DB query → child span) via opentelemetry-instrumentation-sqlalchemy
  - Exports via OTLP HTTP to the AWS Distro for OpenTelemetry (ADOT) Collector,
    which forwards traces to X-Ray and metrics to CloudWatch for Bedrock to consume
  - Resource attributes: service.name, service.version, deployment.environment
  - Optional auth headers via OTEL_EXPORTER_OTLP_HEADERS (comma-separated key=value)
  - New .env vars: OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_HEADERS
  - Packages: opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi,
    opentelemetry-instrumentation-sqlalchemy, opentelemetry-exporter-otlp-proto-http

F45 Automated Test Suite
  - pytest-based test suite in tests/ covering all score submission and retrieval APIs
  - tests/conftest.py bootstraps an in-memory SQLite database so tests run without MySQL
  - Overrides FastAPI's get_db dependency; patches _apply_migrations() (MySQL-specific) to no-op
  - Sets dummy env vars for Google OAuth so auth.py can be imported in CI without credentials
  - Test modules:
      test_health.py     — /health, /robots.txt, /sitemap.xml, homepage, 404 handler
      test_csrf.py       — CSRF middleware (X-Requested-With guard) on all POST /api/* routes
      test_scores.py     — Classic game score submission (all modes) and leaderboard ordering
      test_mosaic.py     — Mosaic daily, easy, and custom-board (F44) leaderboard
      test_tentaizu.py   — Tentaizu daily and easy scores
      test_variants.py   — Cylinder, Toroid, and Replay score APIs
      test_validation.py — Pydantic validation: 422 returned for all invalid payloads
  - Run with: pytest (configured in pytest.ini; testpaths=tests)

F44 Custom Mosaic Board Leaderboard
  - When a Mosaic board is loaded via hash+mask params (/mosaic/custom/?hash=...&mask=...),
    show a per-board leaderboard keyed by (hash, mask) — similar to the Replay page's per-hash leaderboard
  - Logged-in users' times are saved automatically on win; guests get a name-entry form
  - The board ID is derived from the hash+mask pair (e.g. SHA-256 or concatenation)
  - DB table: mosaic_custom_scores (board_id, name, time_secs, solved_at)
  - API: POST /api/mosaic-custom-scores  GET /api/mosaic-custom-scores/<board_id>
  - The custom board template sets data-score-api to the new endpoint when hash+mask are present
  - Random/generated custom boards (no hash param) remain leaderboard-free

F43 XYZZY Cheat Code (Replay mode only)
  - Classic Windows 98/2000/XP Minesweeper easter egg faithfully recreated
  - Activation sequence: type "xyzzy", press Shift+Enter, then press Shift
  - A 1×1 pixel appears at top-left corner: black = mine under cursor, white = safe
  - Available on /variants/replay/ only (not standard, competitive, or daily games)
  - Requires login — guests see a toast with a Google login link instead
  - Games completed with cheat active are excluded from the replay leaderboard
  - Documented in /how-to-play#cheatcode with history of the XYZZY origin
    (Colossal Cave Adventure, 1975)

F42 Mosaic how-to-play page and expanded mega menu
  - New page at /mosaic/how-to-play (templates/mosaic_howto.html) with rules, controls,
    solving patterns, and strategy — parallel structure to /tentaizu/how-to-play
  - Subnav cards added to /mosaic/standard and /mosaic (easy) linking to each other
    and to /mosaic/how-to-play
  - Mega menu Puzzles group expanded: Mosaic Daily (9×9), Mosaic Easy (5×5),
    How to Play Mosaic — replacing the single Mosaic card

F41 SEO structured data and page differentiation
  - Self-referencing JSON-LD url on variant and tool pages (cylinder, toroid, board-generator, replay)
    Previously all inherited the homepage url from base.html; each page now declares its own canonical url in JSON-LD
  - board-generator and replay use WebApplication schema type (more accurate than VideoGame for interactive tools)
  - /pvp differentiated from /duel: distinct title, meta description, canonical, keywords, og:*, and JSON-LD
    /pvp now targets "competitive minesweeper / minesweeper ranked / minesweeper elo" keyword cluster
    /duel retains its "challenge a friend / 1v1" positioning

F40 Server Health Checks and Deploy Gate
  - GET /iamatestfile.txt returns plain text "healthy" for uptime monitors and load balancer probes
  - GET /health returns service status; restricted to localhost only (403 for external requests)
  - Staging deploy script runs smoke tests (/, /pvp, /duel, /tentaizu) after every deploy:
      Pass → writes SHA to /home/ubuntu/deploy_state/last_good_commit
      Fail → writes SHA to blocked_commit, reverts staging to last known good commit
  - Staging cron skips any commit listed in blocked_commit; clears block when a new commit arrives
  - Production deploy script only promotes commits present in last_good_commit (staging-blessed)
  - State files live at /home/ubuntu/deploy_state/ (runtime, not in git)

F39 Use light theme during daylight hours based on client browser local time, defaulting to dark otherwise

F38 Light theme

F36 Mega menu navigation for dark / light / tentaizu skins
  - Replaces the old flat nav with a 5-group drop-down mega menu on non-classic skins
  - Groups: Play (Beginner/Intermediate/Expert/Custom/Rush/Leaderboard), PvP, Puzzles, Variants, More
  - Classic (Diana) skin retains its existing sidebar nav unchanged
  - Each group opens a full-width panel of icon+title+description cards on click
  - CSS scoped to html:not([data-skin="classic"]); JS toggleMega() opens/closes panels

F31 Archive anonymous PvP results nightly
   Daily cron job moves PvP results with no registered winner to anonymous_pvp_results backup table.

F30 PvP rankings sortable columns
   Wins and Elo columns in win rankings table are clickable to toggle ascending/descending sort.

F29 PvP bot opponent
   Constraint-based Minesweeper AI in bots/minesweeper_bot.py (easy/medium/hard).
   Bot lobby at /pvp/bot; game at /pvp/bot/play?m=standard&d=medium.
   "🤖 vs Bot" tab added to the PvP mode switcher.

F28 Blog comments
  Logged-in users can comment on blog posts
  Comments require admin approval before appearing
  Admin moderation page at /admin/blog

F27 Tentaizu game improvements

F26 Mosaic game mode

F24 Add Kanban board to admin section of the site and create a link

F23 PVP/Duel improvements
    View opponent's board beside your board for PVP
      Do we want a delay before we see you opponent's latest move?
        * i.e. Suppose you have been playing for 20 seconds, opponent board
          shows their state as of 15 seconds.
          What is the right amount of delay?  0 could be the right answer
    Implement a first click clear for both you and opponent
    Implement changes in behavoir when you click a mine
    Implement rating system similar to Chess Elo
      Display rating on profile
      Match making based on rating
    Replay feature and game board hash?
    Implement same features for Duel
    Implement bots

F22 Google SEO improvements

F20 Tentaizu theme

F19 Secret admin mode that displays site statistics

F16 Add a blog

F15 Website Analytics on local admin page at /admin and subpages

F14 Website Analytics Google Analytics

F13 Quests

F9 SEO improvements
   For general SEO improvements.  If the improvement is for a specific platform, use Bing SEO improvements or Google SEO improvements

F8 Improved Mobile Browser Support

-- Addressed --

F56 Replay — show authenticated user's first board clear as a benchmark
  - GET /api/replay-scores/my-first?board_hash=&variant= returns the user's
    earliest win, querying both replay_scores and scores tables
  - "Your First Clear" section rendered below Board High Scores (green tint)
  - Only shown for logged-in users; uses data-username on #board element
  - Works for all variants: standard, no-guess, cylinder, toroid
  - examplescreenshots/Replay_BHS-S_Example

F56 URL Traffic Ranking on Admin Web Traffic Page
  - On /admin/web_traffic, show a "Top URLs — <date>" table ranked by hit count for the previous day
  - Parses Apache access logs live at page load (no additional DB table required)
  - Strips query strings so URL paths are grouped (e.g. /game counts all /game?... requests together)
  - Columns: rank (#), full URL (https://minesweeper.org + path, clickable), hit count
  - Uses _LOG_RE_URL regex to extract path from each log line
  - get_url_traffic_stats(target_date) helper function handles the parsing
  - Displayed between Network Statistics and Daily Apache Log Breakdown sections

F37 Links Page at /links
  - Static curated links page at /links
  - Link sections are maintained in FeatureRequests/links-page.md; rebuild the page when new links are added
  - Sections (in order):
      Landmines        — Halo Trust and organizations removing landmines
      Princess Di      — Pages about Diana and her landmine-clearing work
      Minesweeper Theory — 3BV wiki, strategy videos, general theory
      Play Minesweeper — Sites to play (include Google Minesweeper)
      Tentaizu         — puzzle-minesweeper.com and related
      Mosaic           — puzzle-minesweeper.com + how-to-play video
      Minesweeper Rush — Steam store page
      Minesweeper Variants — Variants advent calendar and related
      Vibe Coding      — Vibe coding resources
      Git Repos        — minesweeper.org, Tentaizu generator, Mosaic
  - Route: GET /links → templates/links.html
  - No dynamic data; pure Jinja2 template with info-page styling
  - Add nav link where appropriate

F35 Mosaic Custom Board
  - /mosaic/custom/ — configurable custom Mosaic board page
  - Without params: form to select rows (3–20), cols (3–20), and difficulty (easy/standard/hard)
  - With ?hash=...&rows=...&cols=... params: loads a specific board from the board generator
  - "Hide Numbers" button in win overlay — toggles hint number visibility on the solved board
  - "Hide Numbers" button also available on /mosaic and /mosaic/easy after solving

F34 Board Generator
  - Interactive grid at /variants/board-generator where you click cells to place mines
  - Shows board hash (base64 bit-array encoding), mine count, and 3BV for Standard/Cylinder/Toroid topologies
  - Generates shareable links: /variants/replay/ (play the board) and /mosaic/custom/ (solve as Mosaic)
  - Board hash format: bit i of byte i>>3 is set if cell index i is a mine

F33 Continuous Integration
  - Environment variable ENVIRONMENT identifies the running environment (dev, staging, prod)
  - GitHub repo and local development use ENVIRONMENT=dev
  - Future environments (staging, prod) will be added as the pipeline is built out
  - URL mapping:
      dev     → localhost
      staging → dev.minesweeper.org
      prod    → minesweeper.org

F32 Add chat support to the website
  - Global lobby chat visible to all logged-in users
  - In-game chat during PvP duels (between the two players)
  - WebSocket-based (reuse existing WS infrastructure)
  - Messages stored in DB for moderation; auto-expire after 24h
  - Admin moderation: delete messages from /admin

F25 Add timed banner support for special days

F21 Bing SEO improvements

F18 Theme selection in url

F17 Add linkedin link

F12 Cylinder variant

F11 Implement Tentaizu on a sub-page https:/minesweeper.org/tentaizu
    The puzzle of the day starts with 10 mines on a 7x7 board.  Some of the tiles that do not contain mines are revealed with the number of mines near them also shows.  The puzzle of the day should be solvable with the revealed numbers.
    See https://puzzle-minesweeper.com
    If your flag or blank contradicts a number, that number should highlight letting you know that you made a mistake
    You should be able to toggle between flag, blank, and unknown
    See also https://github.com/hellpig/minesweeper-puzzle-generator

F10 Multiple skin support (Default for minesweeper.org will be called Dark)

F7 Allow chording as an optional feature: https://minesweeper.fandom.com/wiki/Chording

F6 Support Minesweeper Rush mode

F5 Multilanguage support
  Languages: EN, EO, DE, ES, TH, PGL, UK, FR, KO, JA, ZH, ZH-HANT, PL, TL (Tagalog)

F4 Implement run off git repo and restart on successful commit

F3 Implement No Guessing mode

F2 Multiplayer game mode
  Implement Websockets
  Modify game to make it easier to find matches
  Save game history to database

F1 User Profile
  Login with Google
  Save user info in a database

-- Documentation --

D3 Outline the site structure and approach

D2 Add feature request code to the beginning of the commit message
   If the commit has to do with the Tentaizu theme, the commit message should be
   of the form:
   F20 <Description of update>

D1 Document the environment
  Development is done on a Mac, Linux desktop, or Windows desktop and
  pushed to an Ubuntu server on AWS
