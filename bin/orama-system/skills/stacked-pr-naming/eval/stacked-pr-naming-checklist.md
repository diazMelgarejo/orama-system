# stacked-pr-naming checklist

- [ ] Integration base matches the repo table on the reference card.
- [ ] Branch is `stack/NN-short-topic` (zero-padded `NN`).
- [ ] PR title is `[NN/TT → <integration-base>] <type>: <summary>`.
- [ ] `NN=00` GitHub base is the integration branch; `NN>00` GitHub base is `stack/(NN-1)-…`.
- [ ] Body first lines include Stack / GitHub base / Depends on.
- [ ] No parallel PRs targeting the same unique patch against the integration base.
