# JSMinesweeper Probability Analysis Integration

**Status:** idea  
**Feature ID:** F-  
**Author:** Richard Cross  
**Date:** 2026-09-27

---

## Problem / Motivation

Players making uncertain moves — especially in endgame positions where no cell is provably safe — have
no guidance about which guess carries the lowest risk. David N. Hill's open-source JSMinesweeper
library (https://github.com/DavidNHill/JSMinesweeper) solves this: given any board state, it computes
a mine probability for every hidden cell using constraint propagation and combinatorial analysis.
Surfacing these probabilities inside minesweeper.org would let players make informed guesses instead
of random ones, and would teach probability-based reasoning as a skill.

---

## Success Criteria

- [ ] Players can see per-cell mine probability percentages on a real board position (exact UI TBD)
- [ ] The probabilities are accurate (match JSMinesweeper's analysis, or equivalent)
- [ ] The feature does not slow down normal gameplay for players who don't want it
- [ ] The integration is clearly explained so players understand what they're seeing

---

## Scope

**In this feature:**
- Embed or integrate JSMinesweeper's solver logic
- Display mine probabilities for hidden cells (e.g., "23% mine" overlay)
- Identify which cells are provably safe (0%) or provably mine (100%)

**Out of scope (future):**
- Solver-assisted auto-play
- Full game replay with probability overlay
- Custom probability model (use JSMinesweeper's existing solver)

---

## Open Questions (requires further analysis)

1. **Where does it surface?**
   - During live gameplay (togglable overlay)?
   - In a dedicated "analysis mode" after a game ends?
   - In bootcamp / drill boards as a teaching aid?
   - As a standalone solver page?
   Each location has different implementation complexity and player-experience implications.

2. **How is it triggered?**
   - Always-on toggle in settings?
   - On-demand button ("Show probabilities")?
   - Automatically when the board has no safe deductions left?

3. **License and bundling:**
   - JSMinesweeper is MIT-licensed — bundling is permitted.
   - How large is the solver payload? Is it acceptable to include in the page bundle?
   - Can it run in a Web Worker to avoid blocking the main thread?

4. **Board state serialization:**
   - JSMinesweeper takes a board state as input.
   - How do we serialize the minesweeper.org board state into JSMinesweeper's expected format?
   - Does it need the full mine layout (known server-side) or just the revealed/flagged state?

5. **Mobile performance:**
   - Constraint solving on large boards (30×16) can be expensive. Is it fast enough on mobile?

---

## Key Design Decisions

*Leave blank until analysis is complete. Decision on integration point (live vs post-game vs drill)
is the most important design choice — it determines all other implementation details.*

---

## Implementation Notes

*Filled in when work completes.*
