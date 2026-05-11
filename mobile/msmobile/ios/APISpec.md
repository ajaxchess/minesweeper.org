# minesweeper.org API Specification (Mobile App)

Base URL: `https://minesweeper.org`

---

## Authentication & CSRF

The server has no login requirement for score submission — scores can be
submitted anonymously. However, **every POST to `/api/*` must include this
header or the server returns HTTP 403:**

```
X-Requested-With: XMLHttpRequest
```

This is the CSRF guard (see `main.py` `csrf_xhr_check` middleware). It is
not a secret — it just prevents cross-site form submissions. Include it on
every API call.

There is no API key or Bearer token. Session cookies are used for logged-in
users on the web, but the app does not need to manage sessions.

**Client type header** — include on every request so scores are correctly
attributed and exempted from the daily score cleanup:

```
X-Client-Type: ios_app
```

---

## Rate limiting

All POST endpoints are rate-limited to **10 requests per minute** per IP.
The app should not retry on `429 Too Many Requests`.

---

## Score submission

### POST `/api/scores`

Submit a completed classic minesweeper game.

**Request headers:**
```
Content-Type: application/json
X-Requested-With: XMLHttpRequest
X-Client-Type: ios_app
```

**Request body (JSON):**

| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `name` | string | yes | 1–32 printable ASCII chars | Player display name |
| `mode` | string | yes | `"beginner"`, `"intermediate"`, or `"expert"` | |
| `time_secs` | int | yes | 1–999 | Elapsed time in whole seconds |
| `time_ms` | int | no | 1–3,600,000 | Elapsed time in milliseconds (preferred — used for sorting) |
| `rows` | int | yes | 5–30 | |
| `cols` | int | yes | 5–50 | |
| `mines` | int | yes | 1–999, ≤ 85% of cells | |
| `no_guess` | bool | no | default `false` | Set `true` for no-guess mode games |
| `board_hash` | string | no | max 128 chars | See `BoardHashSpec.md` |
| `bbbv` | int | no | 1–9999 | 3BV value — see `NoGuessSolverSpec.md` |
| `left_clicks` | int | no | 0–99999 | |
| `right_clicks` | int | no | 0–99999 | |
| `chord_clicks` | int | no | 0–99999 | |

**Standard board sizes:**

| Mode | rows | cols | mines |
|---|---|---|---|
| Beginner | 9 | 9 | 10 |
| Intermediate | 16 | 16 | 40 |
| Expert | 16 | 30 | 99 |

**Example request:**
```json
POST /api/scores
Content-Type: application/json
X-Requested-With: XMLHttpRequest
X-Client-Type: ios_app

{
  "name": "Alice",
  "mode": "beginner",
  "time_secs": 12,
  "time_ms": 12340,
  "rows": 9,
  "cols": 9,
  "mines": 10,
  "no_guess": false,
  "board_hash": "AQAAAAAAAAAAAAA=",
  "bbbv": 35,
  "left_clicks": 40,
  "right_clicks": 10,
  "chord_clicks": 0
}
```

**Success response — HTTP 201:**
```json
{ "ok": true, "id": 123456 }
```

The `id` is the server-assigned score ID. Store it locally so the app can
deduplicate this score against future leaderboard fetches.

**Error responses:**

| Status | Meaning |
|---|---|
| 403 | Missing `X-Requested-With` header |
| 422 | Validation error (field out of range, invalid mode, too many mines) |
| 429 | Rate limit exceeded (10/minute) |
| 5xx | Server error — treat as offline, store score locally |

---

## Leaderboard fetch

### GET `/api/scores/{mode}`

Fetch the top scores for a given mode and time period.

**Path parameter:**
- `mode`: `beginner`, `intermediate`, or `expert`

**Query parameters:**

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `no_guess` | bool | `false` | `true` to fetch no-guess leaderboard |
| `period` | string | `"daily"` | `"daily"`, `"season"`, or `"alltime"` |
| `date` | string | today | ISO date `YYYY-MM-DD`, only used when `period=daily` |
| `season_num` | int | current | Season number, only used when `period=season` |

**Example:**
```
GET /api/scores/beginner?no_guess=false&period=daily
GET /api/scores/expert?no_guess=true&period=alltime
GET /api/scores/intermediate?period=season&season_num=3
```

**Response — HTTP 200, JSON array (up to 15 entries):**
```json
[
  {
    "id": 123456,
    "name": "Alice",
    "time_secs": 12,
    "time_ms": 12340,
    "rows": 9,
    "cols": 9,
    "mines": 10,
    "no_guess": false,
    "board_hash": "AQAAAAAAAAAAAAA=",
    "bbbv": 35,
    "left_clicks": 40,
    "right_clicks": 10,
    "chord_clicks": 0,
    "client_type": "ios_app",
    "created_at": "2026-03-27T14:23:01"
  }
]
```

Scores are sorted by `time_ms` ascending (fastest first). For season and
alltime periods, only the best score per player is included.

**Caching:** The server sets `Cache-Control: public, max-age=60` on leaderboard
responses. The app may cache locally for up to 60 seconds.

---

## Offline behaviour

When any API call fails (network error, timeout, or 5xx), the app should:

1. Store the score in local storage (see Outline.md for the 20-score cap).
2. Show the local score in the leaderboard immediately.
3. **Do not retry** — the Outline explicitly forbids retry logic.

When back online, show a mix of local and server scores. Deduplicate using
`(mode + time_ms + board_hash)` — if a local score matches a server score on
all three fields, display it once using the server record (which has an `id`).
