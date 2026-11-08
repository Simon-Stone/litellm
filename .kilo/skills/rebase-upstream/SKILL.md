---
name: rebase-upstream
description: Rebase this Dartmouth fork onto a newer upstream LiteLLM release, re-deciding every fork patch instead of replaying them blindly. Use when asked to rebase, sync, or move main onto an upstream tag.
---

# Rebase the fork onto upstream

`main` is an upstream release tag plus a stack of fork patches. A rebase is a re-decision of each patch, recorded in the **ledger**, [`FORK_CHECKLIST.md`](../../../FORK_CHECKLIST.md). Each patch ends with one **disposition**:

- **fork-maintained**: still needed, carried forward
- **upstream-closed**: upstream now guarantees the same behavior; drop the patch
- **upstream-closed (evolved)**: upstream covers it differently; drop, and record what the fork loses
- **dropped**: no longer wanted (user decision)

Two failure modes drive every step:

- **False closure**: a patch is dropped because upstream "seems to fix it", and the bug returns. The ledger records one (`a58e1a4fa5`): the verdict came from running _upstream's_ suite, which never contained the fork's regression tests.
- **Silent revert**: the rebase succeeds, tests pass, and upstream behavior is back. Typical causes: the patch auto-merged into code upstream no longer calls, or upstream added a new call site that the patch never covered.

Some patches are **divergences**: deliberate policy that differs from upstream (e.g. end-user budgets on virtual keys). Upstream will never close these; it can only route around them. Treat any change to a divergence as the user's decision.

## 1. Prepare

1. Clean tree, `git pull`, `git fetch upstream --tags`.
2. Old base: `git describe --tags --abbrev=0 --exclude='*hotfix*' main`. Tags matching `*-hotfix-*` are the fork's own release tags, never a base.
3. Target: the tag the user named, otherwise the newest upstream `vX.Y.Z` with no `-dev`/`-rc` suffix. Confirm it with the user before continuing.
4. Read the ledger's "Rebase Hygiene Notes" now; they cover uv, rust, stray venvs and gate bases.

Done when old base and target are both confirmed.

## 2. Inventory

List the patch stack with `git cherry -v <target> main`. `+` lines are candidates, `-` lines are already in the target. Commits by upstream authors on main are backports from an upstream stable branch: confirm each is in the target (`-` in `git cherry`, or its PR number in `git log <target> --grep`) and leave them out.

Reconcile against the ledger. For every `+` commit, write down:

- its ledger row, or "missing from ledger" (add a row later)
- the **invariant** it guarantees, one sentence of observable behavior
- divergence or fix
- its regression tests, by name

A patch with no regression test cannot be judged. Write the test on current `main` first: it must pass on `main` and fail on the old base. Doc, CI, Docker and dependency patches use a concrete check instead (a grep, the pinned version in the target's `uv.lock` / Dockerfile, the advisory's fixed version).

Done when every `+` commit has an invariant and a test or check.

## 3. Run the oracle

The **oracle** is the fork's own regression tests run against a clean target. Upstream's tests are never evidence for a fork patch.

1. `git worktree add ../litellm-oracle <target>` and give it its own environment (`uv sync --frozen`).
2. Copy only the fork's test files into it (`git -C ../litellm-oracle checkout main -- <test paths>`), mapping to the target's test layout if upstream moved directories.
3. Run each patch's tests.
   - **Red**: the invariant is broken upstream. Disposition: fork-maintained.
   - **Green**: closure _candidate_. Read upstream's code for the path the invariant lives on and name the upstream function or PR that now guarantees it. Green tests that mock the path upstream changed prove nothing; port them until they exercise it.
   - **Doesn't import** (the test references a fork-only helper): neither red nor green. Port the test to reach the behavior through upstream's public entry point, then rerun.
4. For every fork-maintained patch, hunt for new sites: grep the target for the concept the patch guards (every budget check, every spend writer, every place the field is cached) and diff that list against the sites the patch touches. A new site the patch misses is a silent revert in waiting; extend the patch and its test to cover it.

Done when every patch has an oracle result plus, for each closure candidate, a named upstream mechanism.

## 4. Decide with the user

Present one table: patch, invariant, oracle result, proposed disposition, evidence. Ask the user (AskUserQuestion) to confirm every proposed drop, every evolved closure (state what behavior the fork loses), and every change to a divergence. Fork-maintained fixes with a red oracle need no question.

Done when every patch has a confirmed disposition.

## 5. Replay

1. Keep a recovery point: `git branch litellm_main_before_<target> main`.
2. `git switch -c litellm_rebase_<target> <target>`, then `git cherry-pick` the fork-maintained patches in their original order. Leave out ledger-only doc commits; step 7 writes a fresh one.
3. Resolve every conflict toward the patch's invariant, not toward either side's text. When upstream refactored the area, re-implement the invariant in upstream's new shape rather than restoring the old code.
4. Treat clean cherry-picks with the same suspicion: re-read each hunk's landing site and check it is still on the live path.
5. Dependency patches: take the target's `uv.lock` and re-run the bump (`uv lock --upgrade-package <pkg>`) instead of hand-merging markers.
6. Search the tree for `<<<<<<<` / `>>>>>>>`. Only the unmodified upstream fixtures the ledger lists may match.

Done when every fork-maintained patch is on the branch and the marker search is clean.

## 6. Verify

1. Every patch's regression tests pass on the branch. Together with step 3 this gives each fork-maintained patch the pair that proves it: red on the clean target, green on the branch.
2. Run the ledger's Quick Validation Commands, with every budget gate on `--base <target>`. Classify each failure by rerunning it in the oracle worktree: failing there too means pre-existing upstream, failing only here means the replay broke something.
3. Run the ledger's end-to-end scenarios for the fork-maintained rows against a live proxy hitting real providers. When that is impossible (no database, no keys), report it as not run.

Done when every failure is classified and every fork-maintained invariant has passing evidence.

## 7. Update the ledger

Rewrite `FORK_CHECKLIST.md` for the new base: header with target, date and the new patch SHAs in order; one row per patch carrying the old SHA, new SHA, disposition and its evidence (oracle result, upstream function or PR, conflict notes); verification results with counts; new hygiene notes for anything that cost time. Rows for dropped patches stay, so the next rebase sees the history. Commit it as `doc: update fork verification checklist for the <target> rebase` on top of the branch.

## 8. Land

Push `litellm_rebase_<target>` and remove the oracle worktree. Replacing `main` is a force-push of shared history: show the user `git log --oneline <target>..litellm_rebase_<target>`, then on their go-ahead run `git push --force-with-lease origin litellm_rebase_<target>:main`. Ask whether to cut a `<target>-hotfix-1` release tag.
