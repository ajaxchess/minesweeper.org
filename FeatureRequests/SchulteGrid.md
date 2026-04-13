# F52 — Schulte Grid — /other/schulte

## Overview
A cognitive training game where players tap numbers in ascending order (1→N²) as fast as
possible on a randomly scrambled grid. Originally used as a psychological assessment tool,
now played for fun and to improve peripheral vision and attention span.

Reference site: https://schultetable.org/

## Value Proposition / Target Audience
- **Elderly users**: proven positive cognitive impact — regular Schulte practice helps
  maintain attention, processing speed, and working memory. Widely used for cognitive
  maintenance and neuroplasticity in seniors.
- **Athletes**: improves peripheral vision and spatial awareness — used in professional
  selection for pilots, drivers, and athletes to test attention, speed, and mental stability.
- **ADHD support**: helps improve sustained attention and reduce distractibility by providing
  structured, immediate-feedback tasks.
- **Anxiety reduction**: structured, immediate-feedback tasks can interrupt negative thinking
  patterns — acts as a "calm your mind" exercise.
- **General public**: genuinely fun and satisfying; competitive high scores list drives
  repeat engagement. Daily practice of 5–10 minutes can improve reading speed by 20–30%.
- Having our own implementation with persistent high scores gives players a home base to
  track improvement over time, rather than playing anonymously elsewhere.

### Key Health Benefits (for page copy / SEO)
- Enhanced cognitive abilities: strengthens working memory, attention, and task-switching
- Improved visual scanning: trains the brain to see more without moving the eyes
- Expanded functional visual field
- Neuroplasticity: regular use increases brain activity in attention networks

## Route
`/other/schulte` — lives under `/other/`, not `/variants/` (not a Minesweeper variant).

## Objective
A grid of N×N cells is filled with randomly scrambled numbers 1–N². The player taps/clicks
them in order (1, then 2, then 3…) as quickly as possible. The timer stops when the final
number is tapped. Score is elapsed time in seconds (lower = better).

## Wrong-tap behaviour
No penalty. No negative feedback. Focus on positive reinforcement — highlight or animate the
correct next tap on success, ignore incorrect taps silently.

## Board Sizes
3×3, 4×4, 5×5, 6×6, 7×7, 8×8, 9×9, 10×10
(8 sizes available in every mode)

## Game Modes (6 total)

| Mode         | On correct tap                                              | Numbers reposition? |
|--------------|-------------------------------------------------------------|---------------------|
| Normal       | Nothing changes — tile and number stay visible              | No                  |
| Easy         | Cell background vanishes; number stays floating in space    | No                  |
| Blind(Normal)| Number disappears; empty tile background stays visible      | No                  |
| Blind(Easy)  | Both cell background and number vanish — empty space left   | No                  |
| Easy Mix     | Cell background vanishes; remaining numbers reposition      | Yes (on each tap)   |
| Mix          | Tile stays; remaining numbers shuffle to new positions      | Yes (on each tap)   |

## Leaderboard
- **Metric**: elapsed time in seconds (to 2 decimal places).
- **Scope**: separate leaderboard per mode × board size = 48 leaderboards.
- **Anonymous play**: allowed. Score is shown to the player at session end.
- **Persistence**:
  - Daily leaderboard: both anonymous and signed-in scores recorded; resets at midnight UTC.
  - All-time / seasonal leaderboard: signed-in (Google) users only.
- **At end of day**: anonymous scores are not carried forward; only signed-in scores persist
  to all-time records.

## Visual Design
Use the existing minesweeper.org dark theme and CSS component system. No distinct look needed.

## Pages Required
1. `/other/schulte` — mode & size selector, leaderboard summary (today's top scores per mode/size)
2. `/other/schulte/play?mode=<mode>&size=<n>` — game board
3. `/other/schulte/leaderboard?mode=<mode>&size=<n>` — full leaderboard for a mode/size combo

## Implementation Notes
- Grid: CSS Grid, responsive. Tile size scales to fit viewport.
- Timer: starts on first tap (not on page load), stops on final correct tap.
- 48 leaderboard combinations — use a single DB table with `(mode, board_size)` columns rather
  than 48 separate tables.
- Modes with repositioning ("Easy Mix", "Mix"): shuffle only the *remaining* (untapped) numbers
  after each correct tap. Already-cleared positions stay cleared.
- Sitemap: add `/other/schulte` at priority 0.7.
- Add to `/other` index page and footer if one exists.
