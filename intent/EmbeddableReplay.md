# Embeddable Game Replay

**Status:** idea
**Feature ID:** F-EMBED
**Author:** Richard Cross
**Date:** 2026-09-21

---

## Problem / Motivation

A minesweeper game is a performance, and right now it is a performance with no
audience. A player finishes a 38-second Expert with 94% efficiency, and the only way
to show anyone is to describe it, or screenshot a static final board that says
nothing about how they got there. The interesting part of a minesweeper game — the
order of the openings, the hesitation before a 1-2-1, the chord cascade at the end —
lives entirely in the replay, and the replay is currently trapped on our site.

We already have everything needed to fix that. `/game/{id}` renders any stored
replay with a player, summary stats, and a share link. What it cannot do is travel.
Paste that URL into a Reddit thread, a Discourse forum, a personal homepage or a
Discord channel and you get, at best, a blue link.

YouTube solved this problem by making the video the portable unit rather than the
page: an embed anyone can drop into their own site, plus rich cards that unfurl
wherever embedding is not allowed. We should do the same for games. A player should
be able to post a game — not a link to a game — into whatever conversation they are
already having.

This is also a growth loop that costs us nothing per impression. Every embedded
replay carries our branding, and every embedded replay can carry a "play this exact
board" button — the `play_url` we already generate on `/game/{id}` — which turns a
spectator into a player on a board they have just watched someone else solve.

**Relationship to F-MOIMPORT.** This feature is independently useful, but the two
compound. Importing your minesweeper.online history gives you hundreds of games
worth sharing; embeddable replays give you a reason to want them here. A player who
wants to post their best m.o. Expert game on r/Minesweeper currently has no good
option — m.o. offers no embed. "Import it to minesweeper.org, then post it" is a
concrete, self-interested reason to connect an account, and it is a much better
pitch than asking someone to migrate for its own sake.

---

## Success Criteria

- [ ] Any publicly visible game at `/game/{id}` has an embed URL that renders a
      working, self-contained replay player inside a third-party page's `<iframe>`
- [ ] The embed player plays, pauses and scrubs without any minesweeper.org
      navigation, ads, or login state leaking into it
- [ ] `/game/{id}` offers copy-paste embed code alongside the existing share link
- [ ] Pasting a `/game/{id}` URL into an oEmbed-aware platform (Discourse, WordPress,
      Notion) produces an embedded player rather than a bare link
- [ ] Pasting a `/game/{id}` URL into Reddit, Discord or Slack produces a rich card
      with a per-game preview image showing that game's actual final board and stats
- [ ] A player can export any of their games as an animated MP4 or GIF and upload it
      anywhere that accepts media
- [ ] An embed can be shared in "coached" mode, where wasted clicks, missed chords
      and missed openings are marked on the board as they happen and explained in a
      commentary rail synced to playback
- [ ] Commentary is the game owner's choice to publish — a third party cannot switch
      it on for someone else's game
- [ ] Animated exports can burn the commentary in, so a coached replay survives being
      uploaded to a platform that takes no iframe
- [ ] Every embed and export carries minesweeper.org branding and a link back
- [ ] Embeds respect the owner's visibility settings — a private game is not
      embeddable, and revoking visibility breaks existing embeds

---

## Scope

**In this feature:**

- `/embed/game/{id}` — minimal, self-contained, iframe-safe replay player
- Embed code generator in the share row on `/game/{id}`
- oEmbed provider endpoint and discovery links
- Per-game Open Graph / Twitter card image, generated and cached
- Animated replay export (MP4 primary, GIF secondary) with a render queue
- "Play this board" call-to-action inside the embed
- Wasted-click commentary overlay ("coached mode"), reusing the existing annotation
  engine in `phase4_routes`
- Embed-specific security posture: CSP, no cookies, no auth, rate limiting
- A short public `/embed` documentation page with parameters and examples

**Out of scope (future):**

- Embedding anything other than a single standard-minesweeper replay — no Tentaizu,
  Mosaic, Tametsi, hexsweeper, PvP or duel embeds in v1 (the model generalizes; the
  work does not)
- Live/in-progress game embedding or spectating
- Playable embeds — the embedded board is a replay, not an interactive game
- Embedding a leaderboard, profile or bootcamp progress
- Being listed as an official Reddit or X media provider (we can apply; we cannot
  scope their decision)

---

## Key Design Decisions

### Decision 1 — One URL, three delivery mechanisms

There is no single embed technique that works everywhere, and pretending otherwise
is how this feature ships and then disappoints. Three mechanisms are needed, and
they layer:

1. **iframe embed** (`/embed/game/{id}`) — the actual player. Works anywhere the
   author controls the HTML: personal sites, blogs, self-hosted forums, Notion,
   Confluence, documentation.
2. **oEmbed** (`/oembed?url=...`) — lets a platform turn a pasted `/game/{id}` URL
   into mechanism 1 automatically. This is what makes "just paste the link" work on
   Discourse, WordPress and similar.
3. **Rich card + media file** — OG/Twitter meta with a per-game image, plus a
   downloadable MP4/GIF. This is the fallback for every platform that refuses
   third-party iframes, which includes the biggest one we care about.

### Decision 2 — Reddit will not take an iframe, and that shapes priorities

This deserves to be stated plainly at the top of the spec rather than discovered in
week five. **Reddit does not render arbitrary third-party iframes.** Inline media
embedding on Reddit comes from a managed provider allowlist; anyone not on it gets a
link card at best. The same is broadly true of X, Facebook and most large social
platforms.

So for the destination Richard named specifically — posting a game in a Reddit
discussion — the iframe is the *wrong* deliverable. What works on Reddit is a rich
link card with a compelling per-game preview image, and, better, an animated
MP4/GIF the player uploads directly to the post. Reddit renders uploaded video
inline and loops it; that is a played-back minesweeper game in someone's feed.

Honest expectation matrix:

| Destination | iframe | oEmbed | Rich card | Animated file |
|---|---|---|---|---|
| Personal homepage / blog (raw HTML) | ✅ | — | — | ✅ |
| Discourse forum | admin-allowlisted | ✅ | ✅ | ✅ |
| WordPress (self-hosted) | ✅ | ✅ | ✅ | ✅ |
| Notion / Confluence / Obsidian | ✅ | ✅ | ✅ | ✅ |
| **Reddit** | ❌ | only via provider allowlist | ✅ | ✅ (upload) |
| Discord | ❌ | — | ✅ | ✅ (inline playback) |
| Slack | ❌ | — | ✅ | ✅ |
| X / Twitter | ❌ | player card needs approval | ✅ | ✅ |
| GitHub README / markdown | ❌ | — | — | ✅ (GIF only) |

**Consequence for sequencing: if we build only one thing, build the animated
export.** It is the only mechanism that works on every destination in the table,
and it is the one that unlocks the use case that prompted this spec. The iframe is
still worth building — it is strictly better where it works, and "their own
homepage" was the other named destination — but it should not be mistaken for the
Reddit answer.

Worth pursuing in parallel: registration as an oEmbed provider with the embed
brokers (Embedly, Iframely) that several platforms including Reddit use. Approval is
neither fast nor guaranteed, but it is cheap to apply for and it is the only path to
true inline embedding on the large platforms. Apply early so the latency runs in the
background.

### Decision 3 — The embed player is a stripped build, not the page in an iframe

`/game/{id}` extends `base.html`, which brings navigation, translations, the skin
system, analytics, ad slots and a large amount of markup that has no business inside
someone else's page. `/embed/game/{id}` gets its own minimal template that shares
only the replay rendering logic.

Requirements specific to the embed:

- **Self-contained and small.** Inline critical CSS, no ad slots, no analytics that
  sets cookies, no fonts beyond what the board needs. Target under 100KB for the
  initial payload.
- **Responsive to its container.** The host chooses the iframe size; the board
  scales to fit. An Expert board at 30×16 in a 400px-wide sidebar must still be
  legible or must degrade gracefully to a scrollable/zoomed view.
- **Chrome:** board, play/pause, scrub bar, elapsed time, and a compact stat strip
  (time, 3BV, 3BV/s, efficiency). Player name links to their profile. A
  minesweeper.org wordmark links to `/game/{id}`.
- **"Play this board"** — a button using the existing `play_url` construction from
  `game_view_page()`, opening `/variants/replay/` in a new tab on the same board.
  This is the growth loop; it should be visually prominent without competing with
  the replay.
- **URL parameters:** `?autoplay=0|1`, `?speed=1|2|4`, `?theme=dark|light|classic`,
  `?controls=0|1`, `?stats=0|1`, `?start=<ms>`. Defaults: no autoplay (autoplay in
  an embed is hostile), controls on, stats on, site default theme.
- **No authentication, ever.** The embed must never read or write a session cookie.
  It renders public data only. This keeps it out of CSRF and clickjacking territory
  entirely and means we can serve it from cache.

### Decision 4 — Per-game preview image and animated export

**Static preview image** (`/embed/game/{id}/preview.png`, referenced from
`og:image` and `twitter:image`): the final board state rendered at card dimensions
(1200×630), with an overlay strip carrying player name, difficulty, time, 3BV/s and
efficiency, and the minesweeper.org wordmark. This replaces the generic
`og-default.png` that `/game/{id}` currently inherits from `base.html`, and it is
the single highest-leverage change in the whole feature: it is what makes a pasted
link in any chat or thread stop looking like a bare URL.

**Animated export** (`/embed/game/{id}/replay.mp4`, `.gif`): the replay rendered as
video. Design notes:

- **MP4 is primary**, GIF secondary. A 30×16 Expert board over 100 seconds is
  enormous as a GIF and modest as an MP4. GIF is retained only because GitHub
  markdown and a few older forums accept nothing else, and it should be generated
  at reduced dimensions and frame rate with an explicit size cap.
- **Speed control matters more than it sounds.** Nobody watches 100 seconds of
  someone else's Expert game. Default the export to 2× with a selectable 1×/2×/4×,
  and cap total output duration; a game longer than the cap is exported at whatever
  speed fits.
- **Rendering approach:** server-side frame generation from `log_json` (replay the
  move log, draw board states) piped to `ffmpeg`, rather than headless-browser
  screen capture. It is faster, deterministic, cheaper, and reuses the board
  rendering logic we would otherwise duplicate. Headless capture is the fallback if
  visual fidelity with the live player proves hard to match.
- **Queue and cache.** Rendering is CPU-heavy and must not run inline in a request.
  Generate on demand, queue it, cache the result keyed by
  `(game_id, format, speed, theme)`, and serve subsequent requests from cache/CDN.
  Preview PNGs are cheap enough to generate on first request and cache; videos need
  a job and a progress state.
- **Abuse bounds:** rate limit per IP and per account; refuse export for games above
  a board-size or duration threshold; expire cached videos that nobody fetches.

### Decision 5 — Visibility, permanence and deletion

The embed inherits the game's visibility; it never widens it.

- `/game/{id}` already 404s when the owner's games are not public. `/embed/game/{id}`,
  the preview image and the exports must apply **the same check, server-side, on
  every request** — including cached media. A cached preview PNG for a game that has
  since been made private must not keep being served.
- Under F-MOIMPORT this check becomes two flags (`games_public_native` /
  `games_public_imported`). The embed must consult the flag matching the game's
  `source`. An imported game from a user who has kept imported games private is not
  embeddable, even though it is visible to them.
- **Revocation breaks embeds, by design.** If a user turns visibility off, every
  existing embed of their games goes dark. The embed should render a small neutral
  "this replay is no longer public" state rather than a broken frame, and the
  settings UI should say plainly that this will happen — a user who has posted a
  game on a forum deserves to know that flipping a switch will blank it.
- **Anonymous and guest games.** `GameReplay` allows `user_email = NULL` with a
  `guest_token`. Guest games have no profile and therefore no visibility flag.
  Recommend: guest games are embeddable (they have no owner to protect and sharing
  is the only thing a guest can do with a game), attributed to "Anonymous", with a
  prompt to sign up to claim it.
- **Deletion.** If a game is deleted, embeds, preview images and cached exports must
  all 404. A cache purge path is required, not optional.

### Decision 6 — Security posture for third-party framing

Being embeddable means deliberately allowing what we otherwise forbid, and the
scope of that permission must be narrow.

- `/embed/*` sends `Content-Security-Policy: frame-ancestors *` and **no**
  `X-Frame-Options`. Every other route on the site keeps its existing framing
  restrictions — this is a per-route exception, not a site-wide relaxation.
- The embed sets no cookies and reads no session. If `base.html`'s analytics or
  consent machinery would set anything, it must not be included in this template.
- Embed responses are cacheable and CDN-friendly; the visibility check must happen
  in a way that is compatible with that (short TTL plus purge-on-revoke, rather than
  a long TTL).
- Rate limiting on the embed and media endpoints, separate from the main site's
  limits, since a popular embed is legitimately high-traffic from many origins.
- `noindex` on `/embed/*` — the canonical, indexable page is `/game/{id}`, and we do
  not want the stripped embed competing with it in search results.

### Decision 7 — Coached mode: wasted-click commentary on the overlay

This is the feature that makes our embed categorically different from anything
minesweeper.online could put in a forum post. Their replay shows you *what*
happened. Ours can show you *what went wrong* — and a shared game that teaches is a
far better advertisement for the bootcamp than any amount of copy on a landing page.

**Most of this already exists and must not be rebuilt.**
`_build_move_log_with_annotations()` in `phase4_routes/routes.py` already walks a
move log against a `GameAnalysis` row and emits per-move badges, human-readable
detail strings, severity levels, tutorial citations and drill links. It handles six
event classes:

| Badge | Meaning | Example commentary (existing) |
|---|---|---|
| `wasted` | Click that revealed nothing | "safety chord — zero new cells revealed" |
| `shortcut` | Flag-then-chord redundancy | "Flag-then-chord redundancy" |
| `opening` | An opening that was available and not taken | "Missed 1-2-1 opening at (7, 12)" |
| `fish` | A missed fishing opportunity | "Missed reduction opportunity" |
| `flagval` | A flag that earned nothing | "Low-value flag — used in 0 future chord(s)" |
| `hierarchy` | Took a lower-priority action than was available | "Chose guess (P4) when deduction (P1) was available" |

It already suppresses the positive cases — openings and fishes the player *did*
take, and high-value flags — so the annotation stream is mistakes only. It already
numbers annotations sequentially and carries citation URLs into the relevant
timestamps of a tutorial video. The embed work is surfacing this, not deriving it.
`replay_analysis_mockup.html` in the analysis project folder is the design starting
point.

**What the embed adds:**

- **On-board markers.** Each annotated move gets a numbered badge on its cell,
  appearing at that move's timestamp during playback and persisting afterwards, so
  the board accumulates a visible record of the mistakes as the game unfolds.
  Colour-coded by severity using the existing `severity` field.
- **A commentary rail** beside or beneath the board, scrolling in sync with
  playback: annotation number, badge, and the existing detail string. Clicking an
  entry scrubs playback to that move — which is the behaviour that makes the embed
  something people actually study rather than watch once.
- **Timeline markers** on the scrub bar at each annotated move, so a viewer can see
  at a glance where the game went wrong before pressing play.
- **A summary line** — "8 wasted clicks · 3 missed chords · 1 missed opening" —
  visible before playback starts. This is what makes the *card* compelling too, and
  it should appear on the preview image from Phase 1.
- **Drill links** are already emitted per annotation (`drill_id`, `drill_label`).
  In an embed these become the call to action: "Practise this pattern" →
  `phase7_drills`. This is the bootcamp funnel, arriving via a forum post.

**Decision: commentary is the owner's choice, and defaults off for third parties.**

This needs care, because the social dynamics are not symmetrical. A player sharing
their own game with commentary on is showing their work — often the point. But a
stranger embedding someone else's proudest Expert run with an automatic overlay
saying "8 wasted clicks, 3 missed chords" is publishing a critique the player never
asked for, on their best game, in front of an audience. That is a good way to make
people stop sharing.

So:

- Two share modes, chosen by the game's owner: **showcase** (no commentary, the
  default) and **coached** (commentary on).
- `?commentary=1` is honoured only when the owner has enabled coached sharing for
  that game; otherwise it is ignored. A third party cannot turn it on.
- The owner sees their own analysis in full on `/game/{id}` and in the replay
  browser regardless — this governs *publication*, not access.
- Guest games have no owner, so commentary defaults off and cannot be enabled.

**Degradation when there is no analysis.** Commentary requires a `game_analyses` row
joined to the replay. Older games and freshly imported ones may not have one. The
embed must render cleanly in showcase mode when analysis is absent rather than
erroring or showing an empty rail, and requesting coached mode for an unanalyzed
game should enqueue analysis and fall back to showcase until it completes.

**Burn commentary into the animated export.** This is the piece that matters most
for Reddit, since no iframe will ever load there: an MP4 where each mistake flashes
its marker and a caption strip names it as it happens. That is a self-contained
teaching artifact that survives being uploaded anywhere — and it is the single most
shareable thing this project can produce. The export cache key gains `commentary` as
a dimension.

### Data model

Very little is needed. `GameReplay` already carries everything the player needs.
Additions are only for the rendering cache:

```
replay_exports
  id, game_replay_id, format ('mp4'|'gif'|'png'), speed, theme,
  status (pending|rendering|ready|failed), file_path, bytes,
  created_at, last_served_at, error

  UNIQUE (game_replay_id, format, speed, theme)
  INDEX (status), INDEX (last_served_at)
```

`last_served_at` drives eviction of exports nobody is watching. The export cache key
gains `commentary` as a dimension, since a coached and an uncoached render of the
same game are different artifacts.

Coached-share permission is a per-game owner setting:

```
game_replays   + share_commentary   BOOLEAN NOT NULL DEFAULT 0
```

Per-game rather than per-account, because the choice is game-specific — a player may
well want commentary on the game they are asking for help with and off on the one
they are proud of.

Optionally, a counter on embed impressions — useful for showing a player that their
game was watched 400 times, which is its own engagement hook. Cheap to add, and
easier to add now than to backfill.

### Routes

```
GET /embed/game/{id}                → iframe player (noindex, frame-ancestors *)
                                      ?commentary=0|1 (honoured only if the owner
                                      enabled coached sharing for this game)
GET /embed/game/{id}/preview.png    → OG/Twitter card image (cached)
GET /embed/game/{id}/replay.mp4     → animated export (queued, cached)
GET /embed/game/{id}/replay.gif     → animated export (queued, cached)
GET /oembed?url=...&format=json     → oEmbed provider endpoint
GET /embed                          → public documentation + live example
```

Plus, on `/game/{id}`:

- `<link rel="alternate" type="application/json+oembed" href="...">` for discovery
- `og:image` / `twitter:image` pointed at the per-game preview
- `og:video` / `twitter:player` where the MP4 exists — this is what gets inline
  playback in Discord
- An embed-code box in the existing `gv-share-row`, with a size/theme picker

---

## Effort Sizing

One developer, calendar weeks.

| Phase | Work | Size | Est. |
|---|---|---|---|
| **1** | **Per-game preview image.** Server-side board rendering from `log_json` final state, stat overlay, card dimensions, cache, wire to `og:image`/`twitter:image` on `/game/{id}`. Immediately improves every link already being shared. | M | **1 wk** |
| **2** | **Animated export.** Frame generation from the move log, `ffmpeg` encode, MP4 + GIF, speed options, render queue, cache table, eviction, rate limits, download UI on `/game/{id}`. The Reddit/Discord answer. | L | **2 wks** |
| **3** | **iframe embed player.** Minimal template, responsive board scaling, controls, stat strip, "play this board" CTA, URL parameters, CSP/framing policy, embed-code generator in the share row, `/embed` docs page. | L | **1.5 wks** |
| **4** | **oEmbed provider.** Endpoint, discovery links, response shapes, testing against Discourse and WordPress, plus applications to Embedly/Iframely and any platform allowlists. Build is small; external approval latency is not ours to control. | S | **0.5 wk** |
| **5** | **Visibility, revocation and abuse.** Server-side visibility on every embed/media route including cached assets, cache purge on revoke/delete, "no longer public" state, guest-game handling, per-route rate limits, impression counting. | M | **1 wk** |
| **6** | **Coached mode.** Surface the existing `phase4_routes` annotation engine in the embed: on-board numbered markers, synced commentary rail, timeline markers, summary line, drill CTAs. Owner-controlled share mode with the `share_commentary` flag and share UI. Graceful degradation when no `game_analyses` row exists. Burn-in support for the animated export. | L | **1.5 wks** |

**Total: ~7.5 weeks of single-developer effort**, or roughly **4 calendar weeks**
across the team — phases 1/2 and 3/4 are independent, phase 5 touches both, and
phase 6 depends on 3 for the rail and on 2 for burn-in.

Phase 6 is cheap relative to its value precisely because the hard part is done: the
analyzer, the event classification, the commentary strings, the severity model, the
citations and the drill links all already exist and are already exposed through
`GET /replays/{game_replay_id}`. This phase is presentation and policy, not
analysis.

**Recommended first commitment: Phase 1 alone — one week.** A per-game preview image
is a single self-contained change that makes every minesweeper.org game link already
being pasted anywhere look dramatically better, and it requires no decisions about
embedding policy. It is also the prerequisite asset for Phases 2 and 3, so nothing
is wasted if the rest is deferred.

### Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Expectation that this "works on Reddit" like YouTube | Feature judged a failure despite working as built | Decision 2 states the matrix up front; sequence the animated export first |
| Video rendering CPU cost on a shared EC2 host | Degrades the live site under load | Queue with concurrency limit, off-peak scheduling, size/duration caps, aggressive caching |
| Cached media outliving a visibility revocation | Privacy breach — a game the user made private stays visible | Purge-on-revoke path built in Phase 5, short CDN TTL, treat as a correctness requirement not a cleanup task |
| `frame-ancestors *` on an under-scoped route set | Clickjacking surface | Exception applies only to `/embed/*`; no cookies, no session, no state-changing actions in that template |
| Embed abuse (hotlinking a popular game at scale) | Bandwidth cost | Per-route rate limits, CDN in front of media, impression accounting |
| Auto-critique of a shared game reads as insulting | Players stop sharing; the growth loop inverts | Commentary is owner-controlled and defaults off; third parties cannot enable it; wording stays diagnostic, never judgemental |
| Coached mode requested for a game with no `game_analyses` row | Empty rail or error in someone else's page | Fall back to showcase mode, enqueue analysis, never render a broken state |
| Board legibility at small embed sizes | Embeds look bad in narrow columns | Responsive scaling with a minimum cell size and a documented minimum width per difficulty |

---

## Open Questions

1. **Should coached mode be the default for games the owner explicitly shares for
   help?** An "ask for a review" share flow that defaults commentary on, distinct
   from a "show off" share flow that defaults it off, may be clearer than a single
   toggle. Cheap to shape now, awkward later.
2. **Impression counting and creator feedback.** "Your game has been watched 1,240
   times" is a real engagement hook. Worth building in Phase 5 or deferring?
3. **Should exports be watermarked?** A minesweeper.org wordmark burned into the
   MP4 survives re-uploads and screenshots, which is the entire attribution value.
   Slight aesthetic cost. Recommend yes, bottom corner, subtle.
4. **Do we embed anything besides standard minesweeper?** Tentaizu and Mosaic have
   their own replay templates already (`tametsi_replay.html`, `mosaic_replay.html`).
   Generalizing later is cheaper if the route shape is designed for it now.
5. **Guest games.** Confirm the recommendation in Decision 5 — embeddable,
   attributed to Anonymous, with a claim prompt.
6. **Does an embedded replay need its own short URL?** `minesweeper.org/g/{id}` is
   friendlier in a forum post than `/game/{id}` and cheap to add, but it is another
   URL to keep canonical-correct.

---

## Implementation Notes

_To be filled in after shipping._
