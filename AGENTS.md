# Agent contract

This is a standalone experimental Android/Termux dotfiles repository. Read the
README and bilingual setup documentation before changing installation.

- Native Termux Bash/pkg and chezmoi only. Never apply the desktop Unix repo,
  use root, or silently introduce PRoot. ARM64 is the first runtime target.
- `home/` is the chezmoi source root. Preserve existing shell content and user
  settings, foreign chezmoi sources, SSH keys, and unrelated Boot scripts.
- Target scripts must validate the actual Termux app environment; ordinary
  Linux, Android's adb shell, and PRoot are not native target environments.
  Render executable shebangs with the validated absolute Termux Bash path.
- Explicit setup/packages/upgrade synchronizes the full Termux package set
  before installation (Termux does not support partial upgrades). Normal
  chezmoi apply/update changes configuration only; Git updates are ff-only.
- SSH defaults to enabled, LAN, port 8022, public-key authentication only.
  Boot defaults on; wake-lock defaults off. Missing public key is pending-key.
  Own only the namespaced sshd config/PID and Boot hook; never kill foreign
  sshd processes or silently replace host keys. Private keys stay on the host.
- Host automation is macOS/Linux uv/Python. Select one authorized ADB serial.
  Never type into an arbitrary existing terminal/job. Confirm a new Termux
  shell or provide manual paste fallback. Clean up only owned ADB mappings.
- Downloads use pinned versions, SHA-256 and size checks. Optional Herdr/Codex
  static Linux artifacts are experimental; version output is not runtime proof.
  Never weaken Android or agent sandbox protections to make a probe pass.
- System-wide Android settings, battery exemption, storage permission and
  wake-lock are separate explicit choices, not implicit setup side effects.
- Tests use temporary HOME/PREFIX and fixture-only-v1. Never run target setup
  on a maintainer host or touch live chezmoi configuration in tests.
- New user documentation has English/zh-TW pairs and MkDocs navigation.
  Record verification levels honestly: desktop tests do not prove Android.
- Future work belongs in this repo's TODO.md/backlog; findings in pitfalls.
- Run `just check` and secret checks before public commits. Never commit device
  identities, public/private pairing keys, tokens, or generated runtime state.
- Commit/push this repository before the umbrella records its gitlink. The
  iSH/OpenWrt byte-identical core/lock contract does not include this repo.

<!-- project-knowledge-harness:agent-guidance -->
<!-- Snippet for the project's agent contract file (AGENTS.md / CLAUDE.md /
     similar). The project-knowledge-harness skill's init.sh appends this
     between sentinel markers; safe to re-run. -->

### Long-term backlog → `TODO.md` + `backlog/`

When the user surfaces an idea explicitly **not** being implemented this
session (signals: "maybe later", "nice to have", "if I'm interested",
"工程量太大需要再評估", "先記下來"), add an entry to [`TODO.md`](TODO.md) using
the priority + effort tag schema. Do **not** create new `ROADMAP.md` /
`IDEAS.md` / `BACKLOG.md` files — `TODO.md` is the single index.

> **These helpers (`add-todo.sh`, `sweep-inbox.sh`, `promote-todo.sh`,
> `todo-kanban.sh`) are provided by the `project-knowledge-harness` skill and
> are _not_ copied into this repo.** Invoke them through that skill — it knows
> where its `scripts/` live, and they operate on this repo's `TODO.md` /
> `backlog/`. If the skill isn't available, maintain `TODO.md` by hand using the
> schema below; the format is simple and the validator is optional.

The skill's `todo-kanban.sh` validates the format — run
`todo-kanban.sh --validate-only TODO.md` after editing so syntax drift is
caught immediately.

#### Three ways to add a TODO entry (preferred order)

1. **Structured CLI — `add-todo.sh`** (default):

   ```
   add-todo.sh --priority P3 --effort M \
     --title "Title" --description "Description"
   ```

   Inserts a canonically-formatted line into the right `## P*` lane and
   re-runs the validator. Add `--backlog` to also scaffold
   `backlog/<slug>.md` from the bundled template.

2. **Quick capture — `backlog/inbox.md`** (when priority/effort unclear):

   ```
   echo "- maybe add docs versioning with mike" >> backlog/inbox.md
   ```

   When the user asks "sweep the inbox", run
   `sweep-inbox.sh`. It prompts for the missing fields per loose
   line and calls `add-todo.sh`. Use `--batch` for non-interactive runs
   that only formalize lines with parseable `key=value` pairs.

3. **Direct edit of `TODO.md`** — fine if the format is fresh; run
   `todo-kanban.sh --validate-only` afterwards.

Add a `backlog/<slug>.md` companion doc when the item meets any of:

- carries a `P?` tag (record what was tried so it doesn't need re-investigation)
- captures a paused troubleshooting session that you intend to fix later
  (preserve the error trace + root cause analysis before context evaporates)
- weighs multiple options (record trade-offs, not only the winner)
- is `[L]` or `[XL]` (architectural; needs design before code)

`[S]` items rarely need a backlog doc — a file path in the `TODO.md` line is
usually enough. See [`backlog/README.md`](backlog/README.md) for the full
template and "when to add a doc" rules.

When implementing a `TODO.md` item, in the same commit:

1. Run `promote-todo.sh --title "<substring>" --summary "<what shipped>"`
   to move the entry into `## Done` with the dated syntax and re-validate.
2. Mark the corresponding `backlog/<slug>.md` (if any) `Status: shipped`
   and keep it as a historical record (don't delete — future-you may
   revisit adjacent decisions).

`backlog/` is repo metadata for maintainers, not user-facing config to
deploy. Outside the chezmoi source root (`home/`), so these files are never deployed.

### Past pitfalls → `pitfalls/`

When you spend more than ~15 minutes debugging something that wasn't
googleable and the fix is non-obvious, write a `pitfalls/<slug>.md`
capturing:

1. **Verbatim symptom** — copy-paste error messages exactly, do not
   paraphrase (preserves grep-ability for future-you / future agent)
2. **Root cause** — why this happens (with source / docs / upstream issue link)
3. **Workaround** — copy-pasteable commands or config diff
4. **Prevention** — how to avoid stepping on this again

Title the doc by the **symptom**, not the root cause (you'll search by what
you're seeing, not by what you eventually learned). See
[`pitfalls/README.md`](pitfalls/README.md) for the full template and
when-to-add rules.

**Pitfall vs Hard invariant**: a pitfall *graduates* to a Hard invariant in
this file when it (a) recurs across machines/agents/sessions despite being
documented, (b) silently corrupts state, or (c) the workaround is non-obvious
enough that "remember to do X" isn't safe. When graduating, leave the
`pitfalls/<slug>.md` as historical record and link to it from the new
invariant.

`pitfalls/` is **not** auto-redacted; review for secrets before
committing. Outside the chezmoi source root (`home/`), so these files are never deployed.
<!-- project-knowledge-harness:agent-guidance (end) -->
