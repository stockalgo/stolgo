# Contributing to stolgo

## Agent Mistake Checklist (docs/IMPLEMENTATION_PLAN_BACKTEST.md §D)

- [ ] no look-ahead: only data[:t+1] in strategy loop
- [ ] no pandas in oms/portfolio hot path
- [ ] no bandl imports outside stolgo.data / stolgo.broker
- [ ] fill default = next_open unless RunConfig.fill_on == "close"
- [ ] pytest tests for this module pass before next build step
