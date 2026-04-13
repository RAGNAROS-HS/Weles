You are starting a work session on the Weles project. Follow these steps exactly, in order.

---

## Step 1 — Status check

Run these in parallel:
- `gh pr list --repo RAGNAROS-HS/Weles --state open` — open PRs (in-progress work)
- `gh issue list --repo RAGNAROS-HS/Weles --state open --limit 50` — open issues

Then check which open issues are **unblocked**: an issue is unblocked when all issues listed in its "Dependencies:" line are closed. To check an issue's dependencies, read its body via `gh issue view {number} --repo RAGNAROS-HS/Weles`.

Present a concise status report:

```
Open PRs (in progress):
  #N  branch-name  "PR title"

Next unblocked issues:
  #N  "Issue title"  [labels]
  #N  "Issue title"  [labels]
  ...

Suggested next issue: #N — "title"
Reason: lowest unblocked issue; all dependencies closed.
```

Pick up the suggested (lowest-numbered unblocked) issue automatically and proceed to Step 2.

---

## Step 2 — Read the issue

1. Run `gh issue view {number} --repo RAGNAROS-HS/Weles` to read the full issue body.
2. Read `CLAUDE.md` for any rules that apply to this issue.
3. If the issue modifies the API, read `docs/api.md`. If it touches core patterns, read `docs/architecture.md`.
4. State back in one short paragraph: what you're about to build, the key constraints, and what tests you'll write. No hand-waving — be specific.

Proceed immediately to Step 3 — do not wait for confirmation.

---

## Step 3 — Implement

1. Create branch: `git checkout -b feat/issue-{N}-{slug}` where slug is 3–5 words from the title, hyphenated.
2. Implement the acceptance criteria from the issue — nothing more. Do not refactor adjacent code.
3. Write the tests listed under "Tests shipped with this issue".
4. Update docs:
   - `CHANGELOG.md` — add entries under `[Unreleased]` in the correct milestone section.
   - `docs/api.md` — if any endpoint was added or changed.
   - `docs/architecture.md` — if any core pattern, module, or invariant changed.
5. Run `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/` for lint, and `uv run pytest tests/ -q` for tests. Fix any failures before continuing. Do not skip or suppress.

---

## Step 4 — Create the PR

1. Stage and commit all changes:
   - Commit message format: `feat: #N {issue title}` (subject ≤72 chars)
   - Body only if the why isn't obvious from the title.
2. Push the branch: `git push -u origin feat/issue-{N}-{slug}`
3. Create the PR:
   - Title: `feat: #N {issue title}`
   - Body: fill out `.github/pull_request_template.md` — acceptance criteria checklist items checked off, docs checkboxes checked, notes on anything non-obvious.
   - Use `gh pr create --repo RAGNAROS-HS/Weles --title "..." --body "..." --base main`
4. Output the PR URL.

---

## Step 5 — Wait for Qodo review

After outputting the PR URL, call `ScheduleWakeup` with `delaySeconds: 600` and `reason: "waiting for Qodo to review PR #{N}"`. Pass the literal sentinel `<<autonomous-loop-dynamic>>` as the `prompt` field so the session resumes automatically.

When the wakeup fires, fetch comments:

```
gh pr view {N} --repo RAGNAROS-HS/Weles --comments
gh api repos/RAGNAROS-HS/Weles/pulls/{N}/comments
```

---

## Step 6 — Address review feedback

For each Qodo comment:

1. **Evaluate** whether the issue is a real bug, false positive, or out of scope for this issue. Dismiss false positives with a brief reason.
2. **Fix** every real bug, correctness issue, or security issue. Do not fix style suggestions or speculative improvements.
3. After all fixes: run lint and tests again (same commands as Step 3 step 5). Fix any new failures.
4. Commit all fixes in a single commit: `fix: address Qodo review issues on PR #{N}`
5. Push: `git push`
