---
title: "No Jira Required: The $0 Kanban Board That Lives in Your Repo"
publisher: "Lady Di's Mines"
image: "https://minesweeper.org/static/img/saaspocalypse.png"
author: "Richard Cross"
authorurl: "https://minesweeper.org/u/ajaxchess"
datePublished: 2026-03-19T12:00:00Z
---

*Part two of an ongoing series. [Read part one here.](/blog/saaspocalypse)*

---

Last week I wrote about how Claude Code replaced WordPress in an afternoon. Today's installment is shorter — a quick dispatch from the front lines of the SaaSpocalypse. This one's about Jira.

## The Jira Question

Jira is the default answer to "how does your team track work?" It has been for twenty years. It's powerful, it's flexible, it's deeply integrated into countless workflows. It also costs money every month per seat, requires admin time to configure, and introduces a whole layer of process that lives *outside* your codebase.

I needed a way to track what was being worked on for minesweeper.org — who's building what, what's in the backlog, what's in review, what's done. The old answer would have been: sign up for Jira, or Linear, or Shortcut, or any of the other excellent project management SaaS products that exist precisely to solve this problem.

I didn't.

## What We Built Instead

Instead of subscribing to anything, I asked Claude Code to build a kanban board directly into the site's admin section. Here's how it works:

**The data lives in the repo.** There are two plain text files checked into the repository: `Features.md` and `KANBAN.md`. `Features.md` is a numbered list of every feature, documentation item, and bug — each with an ID (`F20`, `D2`, `B1`). `KANBAN.md` organizes those IDs into four columns: Backlog, In Progress, Review, and Done. Assignees are noted with a simple `@name` at the end of each line.

**The board reads the files at request time.** The `/admin/kanban` route in the app parses `KANBAN.md` with about thirty lines of Python — a regex split on `##` headings, a line-by-line parse for IDs and assignees — and passes the result to a Jinja template. The kanban board renders as a styled horizontal column layout. Cards show color-coded ID badges, descriptions, and assignees. In-progress items get a yellow left border. Done items are dimmed.

**Commits reference the IDs.** Every commit message starts with the feature or bug ID it relates to. `F24 Add Kanban board to admin section`. `F20 Add tentaizu theme`. The git log becomes the audit trail.

The whole thing — `KANBAN.md`, the route, the template, the CSS — took one conversation with Claude Code.

## Why This Works

The reason this is possible at all is that the hard part of project management software isn't the kanban board. The hard part is:

1. Giving non-technical people a UI to update tickets without touching code.
2. Integrating with everything else — Slack, GitHub, CI/CD pipelines, calendars, time tracking.
3. Providing reporting, filtering, and search at scale across large teams.

For a small team building a project where everyone is already in the codebase? None of that matters. We're already in the repo. Editing a markdown file is not a friction point. And the board renders itself from that markdown — so there's nothing to sync, nothing to import, no webhook to configure.

The SaaSpocalypse doesn't mean every SaaS dies. It means that the software built to abstract away complexity is most vulnerable when the underlying complexity disappears. For a team that's already in the terminal, a `KANBAN.md` file and thirty lines of Python is a perfectly good project management system.

## The Pattern

This is the pattern I keep seeing:

1. **Identify the SaaS** — some tool we'd normally subscribe to.
2. **Ask what it actually does** — strip away the UI, the onboarding, the ecosystem. What's the core function?
3. **Build just that** — the minimum version that fits the actual use case.
4. **Keep it in the repo** — so it's versioned, auditable, and doesn't require a separate login.

We did it with the blog (no WordPress). We did it with analytics (no Google Analytics dashboard — just an `/admin` page). We did it with the kanban board (no Jira). Each time, the answer is a few hours of conversation with Claude Code and a few hundred lines of code that we own entirely.

## The Real Cost of SaaS

Here's the thing that doesn't show up in the per-seat pricing: every SaaS tool you adopt is a context switch. It's a new login, a new tab, a new mental model, a new place for information to live that isn't your codebase. For a large team, that's often worth it — the collaboration features, the integrations, the polish. For a small team building fast, it's often just overhead.

The kanban board for minesweeper.org is visible at `/admin/kanban`. It's fast because it's just reading a file. It's always up to date because the file *is* the source of truth. It requires no subscription, no API key, no webhook. It will never send me an email asking me to upgrade to the Business plan to unlock the timeline view.

---

*The SaaSpocalypse continues. The site — including this blog, the kanban board, the admin dashboard, and the game itself — is all open source at [github.com/ajaxchess/minesweeper.org](https://github.com/ajaxchess/minesweeper.org). Part three coming soon.*
