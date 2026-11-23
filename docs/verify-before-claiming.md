# Verify Before Claiming (agent reference)

Mirrored from Perpetua-Tools `.agent/protocols/verify-before-claiming.md` (PT PR #489);
the source of truth lives there. This is the short reference orama-system agents follow
before writing code around a tool, answering a reviewer, or reporting work as done.
Gate provenance: operator go 2026-11-23 (task autoresearcher-followups-CLINE-PICKUP-09-
protocol-into-orama-docs-b231ce2b).

## The checklist

1. **First contact with a tool or API** - read the docs/entry point first; run `--version`
   and `--help` when supported; treat flag-unknown invocations as real runs and control
   their effects (scratch directory, dry-run, throwaway target). Record version and the
   flags that matter. List the defaults that act or spend (mode, auto-approval, working
   directory, network, credits) and override each explicitly or accept with a reason.
   Inspect what an install puts on disk before writing discovery code; never pass prompts
   through a `.cmd`/`.bat` shim - launch the real entry point.
2. **Code that already exists** - a path that only runs on a rare condition is dormant:
   run it once for real or label it UNTESTED and queue the task; never build on top of it.
   "It has always worked" is a claim - find the last run that proves it.
3. **Answering a reviewer** - copy every finding into a numbered checklist; reply item by
   item with done / not done / disagree plus the commit or output that shows it; diff the
   reply against the list before sending; never write "done" for a bundle.
4. **Searching and negative claims** - "not found" needs two differently worded searches
   (synonym, exact phrase, path) with the patterns named; "not installed / not available"
   needs the command and its output, or a question to the operator.
5. **Experiments and mechanical changes** - learn syntax from `--help` or a throwaway
   target; never probe the real append-only board, queue, outbox or log. After a mechanical
   merge or generated file: parse every row/file, rerun the renderer, check staged content
   for conflict markers: `git diff --cached --check` sees only the lines the staged diff adds,
   so also run `git grep --cached -nE '^(<{7}|>{7})( |$)'` for markers already inside a staged
   file. Append-only logs: the prior bytes must stay an exact prefix - never union by row order.
6. **Numbers and scope** - every rate carries n, host, model and date; 3 of 3 is not
   "no effect". Hold endpoint, template, temperature and mode equal before comparing, or
   label the comparison descriptive. Peer reports are data with provenance: verify the
   cheapest fact yourself (version, flag, hash) and mark it V, P or U.
7. **Closing out** - every U in a report gets a next action: a queued task, a question, or
   a stated reason to leave it. Where a check was skipped, say so instead of implying it
   was done.
