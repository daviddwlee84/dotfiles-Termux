# Backlog Research

Long-form research, design notes, and paused troubleshooting for items listed in
[`../TODO.md`](../TODO.md). One file per topic, named with a slug that matches
the TODO entry.

## Why this exists

`TODO.md` is the **index** — short titles grouped by priority section with
effort tags. This folder
is the **knowledge base** — the actual investigation, options considered,
benchmarks, error messages, and decisions that informed the TODO entry. The goal
is **resume-friendliness**: when you (or an agent) come back to an item three
months later, the doc here lets you pick up in 5 minutes instead of re-running
30 minutes of investigation.

This folder is repo metadata for maintainers, not user-facing config to
deploy. Outside the chezmoi source root (`home/`), so these files are never deployed.

## When to add a doc here

Add a `backlog/<slug>.md` file when **any** of these apply:

- The TODO item carries a `P?` tag (it requires evaluation; record what was tried)
- You did meaningful troubleshooting but didn't ship a fix (capture the trace
  before it evaporates)
- Multiple options were considered (record the trade-offs, not just the winner)
- An external blocker exists (waiting on upstream release, host availability)
- The implementation is `[L]` or `[XL]` (architectural; needs design before code)

`[S]` items rarely need a doc unless there's surprising context.

## When NOT to add a doc here

- Item is `[S]` and obvious — just put the file path in the TODO entry
- Already covered by an existing doc page (cross-link instead — that's
  user-facing reference, this is maintainer-facing speculation)
- Speculation only ("would be cool to...") with no investigation — keep it as a
  one-liner in `TODO.md` first; promote to a doc when you actually look into it

## File template

The vendored helpers use [the local template](.backlog-doc.md.template).
Run `bash scripts/add-todo.sh --backlog ...` from the repository root.

## Index

Add new entries here as you create them. Keep alphabetical.

| Slug | Status | TODO entry |
|---|---|---|
| [android-runtime-matrix](android-runtime-matrix.md) | P1 | Validate Android runtime matrix |
| [native-agent-compatibility](native-agent-compatibility.md) | P? | Expand native agent compatibility |
| [windows-host-helpers](windows-host-helpers.md) | P2 | Add native Windows host helpers |
