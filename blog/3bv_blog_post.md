---
title: "We've added 3bv values to Lady Di's Mines"
publisher: "Lady Di's Mines"
image: "https://minesweeper.org/static/img/3BV_Example.png" 
author: "William Murray"
authorurl: "https://minesweeper.org/u/wnm"
datePublished: 2026-03-18T00:00:00Z
---
# Lady Di's Mines Now Shows 3BV for Every Board

We're excited to announce that **Lady Di's Mines** now displays the **Bechtel's Board Benchmark Value (3BV)** for every board you play!

![3BV Example Board](https://minesweeper.org/static/img/3BV_Example.png)

---

## What Is 3BV?

3BV — short for **Bechtel's Board Benchmark Value** — is a scoring system invented by [Stephan Bechtel](http://www.stephan-bechtel.de/3bv.htm) (with the name coined by Benny Benjamin) that measures the theoretical minimum number of left-clicks needed to clear a board without flagging. It's the go-to metric in the competitive Minesweeper community for judging just how "fast" a board could be.

The formula is straightforward:

- **+1 for each opening** — an "opening" is a blank (zero) cell that, when clicked, cascades to reveal a connected region of blank and numbered cells.
- **+1 for each isolated number square** — any numbered cell that does not border any opening, meaning it must be clicked individually.

That's it. No flags, no chords — just the minimum raw clicks to clear the board.

---

## Walking Through the Example: A Score of 13

Take a look at the beginner board shown above. The game timer reads **13** — and that's no coincidence, it's also the board's 3BV score. Here's how we get there:

### Openings (the cascade clicks)

Scan the board for groups of blank cells. Each distinct connected blank region counts as a single opening, no matter how large it is — one click reveals the whole thing, automatically uncovering all the blank and bordering number cells around it.

In this board, there are **2 openings** — you can see them marked with blue dots in the image above. One click each is all it takes to cascade through both regions.

That gives us **2 clicks** for the openings.

### Isolated Number Squares

Now look at the numbered cells that sit entirely outside every opening's border. These cells are never automatically revealed by any cascade, so each one requires its own dedicated click.

On this board, there are **11 isolated number squares** — marked with yellow dots — scattered around the mine-heavy areas that no opening touches.

That gives us **11 more clicks** for the isolated numbers.

### Total: 2 + 11 = **13** ✅

The minimum number of clicks to clear this board is 13 — which matches the counter shown in the screenshot perfectly.

---

## Why Does This Matter?

A lower 3BV means fewer required clicks, which generally means a faster possible clear time. Competitive players use 3BV — and the derived stat **3BV/s** (3BV per second) — to compare performance across boards of different difficulties. Two players can clear different boards in the same time, but 3BV/s tells you who was actually solving faster.

It's worth noting, as Stephan himself points out, that a low 3BV isn't a *guaranteed* fast board — mine placement still matters. But it's the best single number we have for board difficulty from a click-efficiency standpoint.

---

## See It In Lady Di's Mines

Starting now, your 3BV score is displayed on every board in **Lady Di's Mines**. After each game, you'll also be able to see your **3BV/s** — so you can track not just whether you won, but how efficiently you played.

Give it a try, and see what score you can pull off!

*— The Lady Di's Mines Team*
