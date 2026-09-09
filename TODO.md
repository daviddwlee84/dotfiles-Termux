# TODO

Long-term backlog for dotfiles-Termux. See AGENTS.md
for the maintenance workflow that agents should follow.

> **For agents**: when the user surfaces an idea explicitly **not** being
> implemented this session (signals: "maybe later", "nice to have",
> "工程量太大需要再評估", "先記下來"), add it here with priority + effort tags.
> Do not create new `ROADMAP.md` / `IDEAS.md` / `BACKLOG.md` files —
> `TODO.md` is the single backlog index. Long-form research goes in
> [`backlog/<slug>.md`](backlog/).

<!-- Use the exact section order: P1, P2, P3, P?, Done.
     The project-knowledge-harness skill's todo-kanban.sh validator only
     inspects top-level `- [ ]` and `- ✅` items inside these sections. Prose
     paragraphs, blockquotes, indented sub-bullets, HTML comments, and `---`
     rules are ignored — feel free to add inline guidance like this without
     breaking machine readability. -->

## P1

Likely next batch — items you'd reach for if you sat down to work today.
- [ ] **[M] Validate Android runtime matrix** — Finish physical/network-disruption recovery, background/reboot/Boot and agent authentication after the partial ARM64 run; preserve the failed Codex sandbox gate. → [research](backlog/android-runtime-matrix.md)


## P2

Worth doing, no rush.
- [ ] **[M] Add native Windows host helpers** — Implement and validate PowerShell ADB provisioning with the same device selection, APK trust and SSH pairing semantics. → [research](backlog/windows-host-helpers.md)


## P3

Someday / nice-to-have.


## P?

Needs a spike before committing to a real priority. Tag as `[?/Effort]`.
- [ ] **[?/L] Expand native agent compatibility** — Resolve observed Herdr/Codex gaps and evaluate Claude, Gemini, OpenCode and OMP without replacing the native baseline or relaxing protections. → [research](backlog/native-agent-compatibility.md)


## Done

Recently shipped. When implementing an active item, in the same commit run the
`project-knowledge-harness` skill's `promote-todo.sh` (it operates on this
`TODO.md`):

```
promote-todo.sh --title "<substring>" --summary "<one-line shipped summary>"
```

This moves the entry here using the dated `Done` syntax and re-validates.


<!-- Prune older entries into CHANGELOG.md once prior-year items appear here
     or this section grows past ~20 entries. -->
