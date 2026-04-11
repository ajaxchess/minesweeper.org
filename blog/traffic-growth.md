---
title: "We're Growing — When Will We Hit 100,000 Daily Visitors?"
publisher: "Lady Di's Mines"
image: "/static/img/minesweeper_org_Linear_Fit.png"
author: "Richard Cross"
authorurl: "https://minesweeper.org"
datePublished: 2026-04-11T00:00:00Z
---

# We're Growing — When Will We Hit 100,000 Daily Visitors?

*A traffic analysis of minesweeper.org's first 17 days of data.*

---

Minesweeper.org is growing. We've been tracking daily unique IPs since late March, and the trend is unmistakably upward. With data in hand we decided to fit a model to the numbers and ask the obvious question: **when do we hit 100,000 unique visitors per day?**

The honest answer is: it depends entirely on which growth scenario plays out. Here's what the data actually shows.

---

## The Data: March 25 – April 10, 2026

Over 17 days we logged **15,322 total unique IPs**, averaging **901 per day**. Traffic peaked at **1,156 on April 7** and troughed at **583 on March 28**. That swing of nearly 600 visitors in a single week is not noise — it's structure.

![Unique IPs linear fit with 7-day periodic component](/static/img/minesweeper_org_Linear_Fit.png)

---

## The Model: Linear Growth with a Weekly Heartbeat

The data fits a composite model well:

**y(t) = 18.59 · t + 748.65 + (−95.63) · sin(2π·t/7 − 0.74)**

The two parts tell different stories:

- **Linear trend (slope = 18.59):** The site gains about 18–19 new unique visitors per day on average. This is the underlying growth engine.
- **7-day periodic component (amplitude ≈ 96):** Traffic predictably rises mid-week and dips at weekends — a pattern every web publisher will recognise. The weekly cycle doesn't change the trend; it just oscillates around it.

---

## Three Scenarios for 100,000 Daily Visitors

The 17-day window is too short to know whether we're in linear, exponential, or some other growth regime. Each assumption produces a very different answer.

### Scenario 1 — The Pessimist: Pure Linear Growth (~November 2040)

If the site adds exactly 18.59 new visitors per day, forever, we reach 100,000 around **4 November 2040** — roughly **5,339 days** or **14.6 years** from now. This is mathematically the most conservative reading of the model.

Almost no successful web property grows purely linearly for 14 years. But it's the floor.

### Scenario 2 — The Optimist: Daily Percentage Growth Holds (~October 2026)

The model's slope of 18.59 on a baseline of 748.65 implies a daily growth rate of about **2.5%**. If that *percentage* rate is sustained (compounding daily rather than adding a flat amount), we hit 100,000 in roughly **200 days** — around **10 October 2026**.

That would be remarkable but not impossible for a site in early viral growth. It also assumes nothing slows us down for the next seven months.

### Scenario 3 — The Middle Path: Weekly Compounding (~April 2027)

Week 1 (March 25–31) averaged **826 unique IPs/day**. Week 2 (April 1–7) averaged **900 IPs/day**. That's a **9% week-over-week gain**. If we sustain 9% weekly growth, we cross 100,000 in about **56 weeks** — around **18 April 2027**.

A year of compounding 9% weekly is aggressive but plausible for a site with active development, new features shipping regularly, and growing word-of-mouth. This is our best-guess scenario.

---

## What Could Accelerate Growth?

A few things could push us toward the optimistic end:

- **PvP matchmaking** — competitive multiplayer brings players back daily and drives sharing.
- **New puzzle modes** — jigsaw, 15-puzzle, tentaizu, and globesweeper all give people a reason to return or discover the site for the first time.
- **SEO compounding** — early organic traffic builds backlinks, which drive more organic traffic. This is inherently exponential, not linear.
- **Word of mouth** — a single viral moment (a streamer, a Reddit post, a school) can add thousands of IPs overnight.

---

## What Could Slow It Down?

Equally, several factors could push us toward the linear (pessimistic) end:

- Growth plateaus are natural once initial novelty wears off.
- Competing minesweeper sites have years of SEO lead.
- We're a small team — shipping speed matters.

---

## Our Bet

We're betting on **somewhere between the middle and optimistic scenarios** — meaning a realistic target of **100,000 daily unique IPs by mid-2027**, assuming we keep shipping, keep the site fast, and keep the community growing.

We'll revisit this analysis in 90 days with more data. By then we'll have a much clearer picture of which curve we're actually on.

If you want to help us get there faster: share a puzzle, challenge a friend to a duel, or just come back tomorrow.

*— The Lady Di's Mines Team*
