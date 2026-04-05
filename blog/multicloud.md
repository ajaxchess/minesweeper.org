---
title: "Minesweeper.org Goes Multicloud"
publisher: "Lady Di's Mines"
image: "/static/img/toby-learned-pig-c6c4ff-small.webp"
author: "Richard Cross"
authorurl: "https://minesweeper.org"
datePublished: 2026-04-05T00:00:00Z
---

# Minesweeper.org Goes Multicloud

*In support of the native Pig Latin speakers of Iowa.*

---

The Lady Di's Mines team is proud to announce that minesweeper.org is now running on **two cloud providers simultaneously** — AWS and Google Cloud Platform.

## Why?

Iowa's native Pig Latin speaking community has long deserved a dedicated minesweeper experience. Starting today, [pgl.minesweeper.org](https://pgl.minesweeper.org) is a GCP-hosted instance of the site with **Pig Latin set as the default language**. All the same games, daily puzzles, and leaderboards — yfay omhay.

If you prefer to play in another language, you can switch at any time using the language selector. We don't judge.

## How It's Built

The GCP infrastructure was provisioned using Terraform. The `.tf` files live in the `terraform/` folder of the [minesweeper.org repo](https://github.com/ajaxchess/minesweeper.org) if you want to see how it's put together.

Both environments run the same codebase and are kept in sync automatically. Every commit to `main` is validated by a staging smoke test before being promoted to production — on both clouds.

## Resilience

The two-cloud setup means that if AWS is having a bad day, Pig Latin players (and anyone else) can head to [pgl.minesweeper.org](https://pgl.minesweeper.org) and keep playing. Conversely, if GCP is the one misbehaving, [minesweeper.org](https://minesweeper.org) on AWS remains unaffected.

If you try both [minesweeper.org](https://minesweeper.org) and [pgl.minesweeper.org](https://pgl.minesweeper.org) and neither responds, it means both AWS and GCP are down simultaneously. At that point, please get to a safe place or shelter in place depending on what your local authorities recommend — assuming there are still any local authorities left.

---

*Minesweeper.org is built and maintained by Regis Consulting. New puzzles and features are added regularly.*
