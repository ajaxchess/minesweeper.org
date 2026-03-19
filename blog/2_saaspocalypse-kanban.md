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

Last week I wrote about how Claude Code replaced WordPress in an afternoon. Today's installment is a quick dispatch from the front lines of the SaaSpocalypse. This one's about Jira — and about a workflow called **GitAgile**.

## The Jira Question

Jira is the default answer to "how does your team track work?" It has been for twenty years. It's powerful, flexible, and deeply integrated into countless workflows. It also costs money every month per seat, requires admin time to configure, and lives *outside* your codebase — a separate system, a separate login, a separate context switch every time you want to know what's happening.

I needed a way to track what was being worked on for minesweeper.org — who's building what, what's in the backlog, what's in review, what's done. The old answer would have been: sign up for Jira, or Linear, or Shortcut. I didn't.

## GitAgile: Managing Your Workflow Inside the Repo

What we're implementing is **GitAgile** — an approach to agile project management that lives entirely inside the git repository, alongside the code. Instead of a separate SaaS tool, your workflow artifacts are plain files: tracked, versioned, and visible to everyone on the team — including your AI coding assistant.

For minesweeper.org, the implementation looks like this:

**`Features.md`** is a numbered registry of every feature, documentation item, and bug. Each entry gets an ID: `F20` for the Tentaizu theme, `F24` for the Kanban board itself, `B1` for a bug fix. This file is the single source of truth for what exists.

**`KANBAN.md`** organizes those IDs into four columns: Backlog, In Progress, Review, and Done. Assignees are noted with a simple `@name`. Editing the board is as simple as moving a line from one section to another.

**Commit messages reference the IDs.** Every commit starts with its feature or bug ID. `F24 Add Kanban board to admin section`. `F20 Add tentaizu theme`. The git log becomes the sprint history, the audit trail, and the changelog all at once.

**The board renders itself** at `/admin/kanban` — a route that reads `KANBAN.md` at request time, parses it into columns, and renders a visual kanban board with color-coded ID badges, descriptions, and assignees.

![The GitAgile Kanban board on minesweeper.org — built from a markdown file, rendered in the admin panel](/static/img/kanban-gitagile.png)

## Trunk-Based Development

GitAgile pairs naturally with **trunk-based development** — a practice where the entire team commits directly to `main` rather than working on long-lived feature branches. Every change is small, integrated continuously, and visible immediately.

For minesweeper.org, this means:

- There's one branch: `main`.
- Every commit goes straight to production via a cron-based auto-deploy that runs `git pull` every five minutes.
- There are no merge conflicts, no stale branches, no pull request queues.
- The kanban board reflects the actual state of the code — not the state of some branch that may or may not have been merged.

When you combine trunk-based development with a file-based kanban in the repo, something interesting happens: **the workflow and the code become the same thing.** Moving a card from "In Progress" to "Done" in `KANBAN.md` is a commit. That commit deploys. The feature is live. The board updates. There's no gap between what the tool says and what the code does.

## Collaborating With a Distributed Team — and With Claude Code

This is where the GitAgile approach really shines for us. Our team is distributed, working asynchronously across time zones. We also collaborate heavily with Claude Code — which means our "team member" is an AI that has no memory between sessions by default.

With everything in the repo, Claude Code can always answer "what are we working on?" by reading `KANBAN.md`. It knows to prefix commit messages with the feature ID because `Features.md` and `D2` tell it to. When a new session starts, the context isn't lost — it's in the files.

A traditional SaaS project management tool would be invisible to Claude Code. It lives behind a login, in a UI, disconnected from the codebase. GitAgile keeps the workflow where the AI can see it, read it, and act on it.

This changes what collaboration with an AI assistant looks like. Claude Code isn't just writing code — it's participating in the workflow. It knows what feature it's implementing, can reference the ID in its commit, and can update `KANBAN.md` when a feature moves to Done.

## What We Built

The whole implementation — `KANBAN.md`, the `/admin/kanban` route, the Jinja template, the CSS — took one conversation with Claude Code. The parser is about thirty lines of Python: a regex split on `##` headings, line-by-line parsing for IDs and `@assignees`, and a pass to the template. Cards show color-coded badges (blue for features, red for bugs, green for documentation), descriptions, and assignees. In-progress items get a yellow left border. Done items are dimmed.

The board is fast because it reads a file. It's always accurate because the file is the source of truth. It requires no subscription, no API key, no webhook, and no Tuesday morning plugin updates.

## The Pattern

This is the SaaSpocalypse pattern I keep seeing:

1. **Identify the SaaS** — some tool we'd normally subscribe to.
2. **Ask what it actually does** — strip away the UI, the onboarding, the ecosystem.
3. **Build just that** — the minimum version that fits the actual use case.
4. **Keep it in the repo** — versioned, auditable, visible to everyone including your AI collaborator.

We did it with the blog (no WordPress). We did it with analytics (no third-party dashboard — just `/admin`). We did it with the kanban board (no Jira). With GitAgile and trunk-based development, the workflow itself lives in the repo — and the whole team, human and AI alike, is always looking at the same thing.

---

*The site — including this blog, the GitAgile kanban board, the admin dashboard, and the game itself — is open source at [github.com/ajaxchess/minesweeper.org](https://github.com/ajaxchess/minesweeper.org). Part three coming soon.*
