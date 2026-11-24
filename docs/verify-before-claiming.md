# Verify Before Claiming (agent reference)

Excerpted from Perpetua-Tools `.agent/protocols/verify-before-claiming.md` (PT PR #489 and the
staged-index checks of PT PR #521); the source of truth lives there. The conflict-scan block in
item 5 is a copy of the PT block, identical apart from the list indentation.
`tests/test_verify_before_claiming_conflict_scan.py` (the same file in both repositories) pins its
hash and, when both checkouts sit side by side, compares the two copies. Change the block in PT
first, copy it here, update the pin in both tests, and run that test with
`VERIFY_BLOCK_REQUIRE_SIBLING=1` before pushing: continuous integration sees one repository only,
so it checks the pin alone. This is the short reference orama-system agents follow before writing
code around a tool, answering a reviewer, or reporting work as done.
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
5. **Experiments and mechanical changes** - learn syntax from `--help` or a throwaway target;
   never probe the real append-only board, queue, outbox or log. After a mechanical merge or
   generated file: parse every row or file and rerun the renderer, then check for conflict markers
   with the block below.

   <!-- conflict-scan:begin -->
   Scan for conflict markers in the working tree and in the index. A file staged as resolved can
   still hold markers, `git diff --cached --check` sees only the lines the staged diff adds, and
   `git diff --name-only --diff-filter=U` lists only unmerged files. Run both commands from any
   directory (`:/` is the whole repository). The pattern matches opening, diff3 ancestor and closing
   markers and a bare separator, of seven or more characters, in LF and CRLF files:

   ```sh
   git grep --untracked -nE -B1 '^(<{7,}|>{7,}|\|{7,}|={7,})([[:space:]]|$)' -- ':/'
   git grep --cached -nE -B1 '^(<{7,}|>{7,}|\|{7,}|={7,})([[:space:]]|$)' -- ':/'
   ```

   The first command reads the tracked and untracked files in the working tree, the second the
   staged blobs. Treat each hit as a candidate: a `<<<<<<<`, `|||||||` or `>>>>>>>` line is a
   conflict marker unless it is quoted text, such as a fixture or documentation about conflicts. A
   bare `=======` is often an underline: when the line above it (shown by `-B1`) is heading or
   title text, it is a Markdown setext heading or a reST title, and only a separator with no title
   above it is a leftover. Not searched: ignored files, submodule contents and markers shorter than
   seven characters. A binary file is reported without a line number, and a byte-order mark before
   a marker on line 1 hides it. Check such paths by hand.
   <!-- conflict-scan:end -->

   Append-only logs: the prior bytes must stay an exact prefix - never union by row order.
6. **Numbers and scope** - every rate carries n, host, model and date; 3 of 3 is not
   "no effect". Hold endpoint, template, temperature and mode equal before comparing, or
   label the comparison descriptive. Peer reports are data with provenance: verify the
   cheapest fact yourself (version, flag, hash) and mark it V, P or U.
7. **Closing out** - every U in a report gets a next action: a queued task, a question, or
   a stated reason to leave it. Where a check was skipped, say so instead of implying it
   was done.
