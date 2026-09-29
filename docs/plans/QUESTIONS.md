# Open questions (implementers append here. Do not guess)

Format: `- [ ] YYYY-MM-DD · plan section · question · what you did in the meantime`

- [ ] 2026-09-28 · 01 §5.1 G1 · The lot size for SENSEX weekly legacy runs is assumed to be 20 (qty in the files is 20). Confirm with the generator.
- [ ] 2026-09-28 · 01 §3.1 · `DATA_ISSUE_THRESHOLD = 0.05` puts all 99 timing-sweep runs in `data_issues`. Confirm the threshold, or raise it to 0.10 (that would still flag most of them).
- [ ] 2026-09-28 · 02 §1.3 · The runner API (`POST /api/runs`) is out of scope. Confirm this before anyone builds a queue UI.
- [ ] 2026-09-28 · 01 §5 P0 · `tests/test_nse_option_chain.py` imports missing legacy `stolgo.nse_data` and failed collection. Added `pytest_ignore_collect` in `tests/conftest.py` matching existing `pytest_collection_modifyitems` intent.
- [ ] 2026-09-29 · 03 R1 · G1 generator: net_pnl ≠ gross_pnl − commission. Which one is wrong?
