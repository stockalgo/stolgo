# SENSEX ATM short straddle: Zerodha live MVP readiness plan

Date: 2026-09-13. Status: implementation plan; no deployment or live trading performed.

## 1. Decisions and objective

User decisions:

- Reproduce the audited ATM short straddle on verified expiry sessions, rather than introduce a new 1-DTE OTM strangle.
- Deploy the runtime from `/Users/chiranjeev/Developer/stolgo`; use `/Users/chiranjeev/Developer/bandl` for broker/data integration; execution account is Zerodha.
- Session loss trigger: 5% of capital deployed.

Operational interpretation: `session_capital_inr` is capital explicitly allocated to this strategy and fixed before daily arming. It is not fluctuating broker margin used, option premium collected, or the whole account balance by accident. A ₹180,000 allocation yields a ₹9,000 session loss trigger. Actual allocation remains to be set. Losses can exceed the trigger during gaps, liquidity shortages, or broker failures; a naked straddle has no contractual maximum loss. If a hard maximum loss is required, protective wings create a different strategy that must be tested separately.

MVP success means controlled live execution: correct contracts, quantities, fill accounting, stops, reliable exit/recovery and delivered alerts. It does not mean achieving the selected backtest's monthly return.

Proposed notifications: Telegram for routine activity; PagerDuty mobile push plus phone/SMS for critical incidents. Actual destinations, subscriptions and receipt tests remain launch requirements. Do not send credentials through alerts.

## 2. What exists and what must be built

Observed local Stolgo revision: `7e4766d`, with existing uncommitted work. Implement on an isolated branch/worktree and preserve existing work.

| Capability | Current evidence | Required work |
|---|---|---|
| Backtesting | Stolgo `core/engine.py:31` rejects non-backtest mode | Separate live runtime using shared strategy decisions; do not reuse SimBroker for real executions |
| Live/paper broker | `broker/base.py` interfaces; `broker/paper.py` raises | Implement broker adapter and a real-time simulated-fill adapter |
| Data | Stolgo wraps Bandl historical candles | Streaming quotes, completed-bar builder, freshness checks, instrument snapshots |
| Bandl execution | Regular Zerodha place/modify/cancel, orders/trades/positions available | Harden transport, uncertain outcomes, raw statuses and acknowledgement persistence |
| Streaming | Bandl documentation explicitly says synchronous HTTP only | Add optional streaming surface to Bandl using official KiteTicker, normalized into Stolgo events |
| Margin preview | Bandl account margin exists; order/basket preview absent | Add Kite order/basket margin adapter; account balance alone is insufficient |
| Recovery and audit | No production live journal established | Durable intent/fill ledger, reconciliation, single writer, restart recovery |
| UI | Backtest run viewer | Separate live status/control view; backtest exports must never represent live broker state |

Concrete Bandl launch blockers found in the current code:

1. `core/http.py:136` retries POST on network failures/5xx. `providers/equity/zerodha/trading.py:173` uses it for order placement. A request may reach the broker before its response is lost. Use a dedicated non-retrying mutation transport; retry reads with bounded backoff. An application-level retry setting alone does not solve uncertain submission recovery.
2. The same order method receives an order ID then calls `get_order` before returning. If that read fails, accepted submission becomes an exception without a durable acknowledgement in Stolgo. Persist/return the acknowledgement separately before status enrichment; include known order ID in any subsequent error.
3. Kite's documented encoding is form parameters; current POST/PUT helpers send JSON. Add provider-specific form transport and contract tests against the official request shape before any live order.
4. Normalized statuses collapse TRIGGER PENDING / CANCEL PENDING / MODIFY PENDING into OPEN. Preserve raw status and quantities so the runner can distinguish protected, pending, triggered and uncertain orders.
5. Current instrument_id placement is explicitly rejected for Zerodha. Resolve exact native `tradingsymbol` and `exchange=BFO` from the day's master and test the Bandl roundtrip without synthesizing an options symbol from a canonical label.
6. Current order builder has no market_protection field. MVP uses LIMIT and supported SL orders. Any later MARKET fallback requires explicit protected-order support and broker/segment validation.

These are implementation requirements, not claims that a live broker test has already passed.

## 3. Frozen strategy specification

Version: `sensex-atm-expiry-straddle-v1` (new honest name; retain old run as audit evidence).

- Underlying: SENSEX. Trading venue: Zerodha BFO.
- Eligibility: the current exchange-confirmed session date equals the selected contract's actual expiry date. Ordinarily Thursday under the current cycle, but never implemented as a weekday-only cron condition. Apply holidays and special-session rules. Skip ambiguity.
- Quantity: one current exchange lot of CE and one equal lot of PE. Resolve lot size/tick size/freeze limit from current contract metadata; do not hardcode 20 indefinitely.
- Strike: same ATM strike for CE and PE, locked using the completed signal bar. Use the closest valid listed strike to the signal spot, deterministic tie rule, and compare with historical selector behavior. Explicit expiry and option type are part of the identity.
- Signal bar: `[09:20:00,09:21:00)` IST. Once complete, select the strike. Never consume the final close of a still-forming bar.
- Entry: first eligible live quote after 09:21:00. Accept an entry window ending 09:21:30; no late catch-up trade. This execution window is an operational deviation from the historical next-bar-open fill and must be measured.
- Sell both legs with bounded marketable limit orders. Keep one lot per leg; no pyramiding, reentry, averaging or automatic size escalation.
- Each short leg has a buy stop trigger at 2 × its actual average entry fill (100% premium increase), rounded conservatively to valid ticks. The surviving leg remains open after a normal individual stop, as in the audit.
- Session risk breach or operational emergency closes all remaining strategy exposure. This 5% overlay is new and needs replay alongside the baseline.
- Time exit starts at 14:30 IST. No overnight intent; all residual exposure is an incident, never an accepted carry.
- Product: prefer supported MIS for the initial supervised pilot, after verifying same-day BFO availability and RMS behavior. Do not silently switch to NRML. Broker auto-square-off is not the exit controller.
- Do not add wings, a new entry filter, combined-premium stop or Wednesday 1-DTE selection under the same performance label.

Fix expiry IDs, initial-equity/timestamp/fee reporting and replay the full available sample with the risk overlay before capital arming. Restore the actual earlier leg-exit timestamps. Preserve all skipped sessions with reason codes, so operational gating does not become hidden selection.

## 4. Market-day schedule

Use UTC timestamps for storage, Asia/Kolkata for the scheduler and UI, monotonic clocks for timeouts. Keep the service supervised continuously; execute an idempotent daily state machine. A reboot must not start another entry.

| IST time | Action | Failure behavior |
|---|---|---|
| 08:30 | Daily preparation; fetch validated calendar and contract master; check clock, disk, DB, network and process version | Stay disarmed; alert |
| 08:40 | Request normal Kite login if today's token is absent/invalid | Login reminder; no credential/TOTP scraping |
| 09:00 | Validate token/account/BFO permissions, registered egress IP configuration, positions and today's orders/trades; select expiry candidates; compute margin budget | No entry with unresolved state |
| 09:05 | Notify readiness, allocation, ₹ loss limit, expiry and one-lot mode; operator arms the pilot session | Arming expires at the entry cutoff; absence means skip |
| 09:10 | Final readiness deadline and external heartbeat check | Warn that session will be skipped if unresolved |
| 09:15 | Subscribe/watch continuous-session live quotes and build minute bars | Stale/incomplete quotes block entry |
| 09:21 | Evaluate completed 09:20 bar; exact contract and risk validation; initiate entry | Reject late, incomplete, wide-spread or insufficient-margin setup |
| 09:21:30 | Entry cutoff | Cancel unfinished entry intentions; protect/close any fills; skip reentry |
| Through 14:30 | Continuous stops, risk and order supervision; periodic REST reconciliation | Pause entries and contain exposure according to incident policy |
| 14:30 | Cancel remaining entry orders; exit remaining short quantity using controlled order state transitions | Track until confirmed flat |
| 14:31 | Residual position or unresolved exit is critical | Immediate phone/push escalation and broker-app runbook |
| 14:35 | Secondary flat verification | Continue incident handling if not flat; never stop the runner because deadline passed |
| Session close + 30 min | Archive broker orders/fills, reconcile fees, generate EOD report | Flat mismatch or incomplete records alert |

The session close is loaded from current exchange/broker schedules, not assumed permanently to be 15:30. Special shortened sessions are skipped unless explicitly supported. On non-eligible days perform health/auth checks as configured, record quotes for engineering diagnostics if desired, and send one clear no-trade reason; do not place the weekly strategy on other days for convenience.

Kite tokens normally expire at 06:00 the following day and may be invalidated earlier. Daily normal login remains part of the operating routine; the plan does not promise unattended authentication.

## 5. Risk controls

A separate risk task produces mandatory decisions; only the order gateway can send mutations. Strategy callbacks cannot bypass risk.

| Control | MVP rule |
|---|---|
| Allocation | Fixed `session_capital_inr`, persisted with user arming/config version |
| Daily loss trigger | Realized P&L + conservative unrealized P&L − estimated total costs <= −5% allocation |
| Loss warning | At 70% of the loss budget consumed, warn (3.5% capital); at 100%, latch exit-only |
| Marks | Use fresh ask for buying back shorts, actual fill ledger for realized P&L; no relying on last traded price or mixed day/net books |
| Exposure | At most one complete two-leg lot; distinguish pending quantity and filled quantity |
| Account isolation | Dedicated strategy use during pilot; no manual trades in the same contracts. Unexpected exposure blocks entry and triggers investigation |
| Margin | Query order/basket margin INCLUDING interim one-leg exposure; require allocation and free broker funds to cover worst-stage margin + risk reserve + exit buffer |
| Planned risk | Aggregate nominal stop loss + modeled costs/slippage must fit the session budget. If one lot cannot fit, skip; never use fractional lot sizes |
| Data freshness | Proposed quote-age limit 2 seconds and cross-leg timestamp skew 1 second; validate on replay/shadow; stale marks are UNKNOWN, never zero P&L |
| Liquidity | Valid non-crossed bid/ask, positive depth covering order size, configurable max spread and entry slippage; calibrate before launch |
| Rate limit | Account-wide mutation queue capped at 2/sec for MVP, below broker limit, with emergency exit priority and bounded retries |
| New entry latch | One entry attempt per session; kill/incident states persist across reboot |
| Stop coverage | Every filled short unit must have confirmed protective coverage or an actively managed emergency close; never label protected merely because request returned |
| Authentication failure | No new risk; preserve existing exchange stops, page operator, recover token/reconcile before any new writes |

Numerical data thresholds and fill deadlines are initial engineering targets, not proven safety guarantees. Risk checks must remain responsive if a historical-data request is slow; use separate clients/workers and bounded queues.

The 5% limit is an exit trigger, not guaranteed maximum loss. A margin increase can require action even if P&L is above the loss limit. Allocation should be determined by current live margin and loss tolerance, not the old backtest's ₹180,000 constant.

## 6. Order lifecycle and failure handling

Persistent session states:

`DISARMED -> PREFLIGHT -> READY -> ARMED -> ENTERING -> OPEN -> EXITING -> FLAT -> RECONCILED`

Exceptional states: `SKIPPED`, `PAUSED`, `UNKNOWN_ORDER`, `RECOVERY`, `HALTED`. HALTED means new risk prohibited; it does not mean stop supervising an open position.

For each command:

1. Persist a unique intent before sending: strategy version, session, contract, leg, purpose, attempt, desired quantity and risk snapshot. Use a database uniqueness constraint.
2. Add a compact <=20-character broker tag and retain its collision-free mapping locally. A tag is correlation metadata, not broker-enforced idempotency.
3. Send once through the gateway. Persist broker order ID as soon as acknowledged. An acknowledgement is not a fill.
4. Consume WebSocket order updates; deduplicate by broker trade/order identifiers and reconcile against REST orders/trades/positions. Store actual fills, not requested quantities, as economic truth.
5. If submission times out, enter UNKNOWN_ORDER. Query the full day's orders and fills (including immediately completed/rejected orders, not only open orders), match tag/contract/time/quantity, and persist findings. Never blindly replay. Absence from one snapshot is not proof of rejection. Unresolvable ambiguity halts new risk and pages the operator.

Entry sequence for one lot:

- Verify both legs and worst-stage margin first. Use a deterministic first-leg rule validated in shadow, not an improvised discretionary choice.
- Place first short using a limit at the current bid, within a precomputed minimum acceptable sell price. Monitor partials and cancellations. Reprice only inside the entry budget.
- On fill, establish/confirm buy SL protection promptly; proposed unprotected interval target under 2 seconds, incident threshold 3 seconds. A rejected/uncertain stop blocks the second entry and starts emergency containment.
- Enter and protect the second leg. Proposed maximum one-leg imbalance interval 10 seconds. If that deadline is exceeded or the first leg stops before entry completes: cancel remaining entries, reconcile fills, close residuals, end the session attempt.
- Non-atomic entry and stop placement is unavoidable with separate regular orders; the runner must model every intermediate state and late fill.

Protective stops:

- Use supported exchange-held SL buy orders with trigger and limit, DAY validity; verify BFO order support in readiness testing. Limit price is above trigger within an approved buffer/tick/price-band rule.
- SL-M availability must not be inferred from other segments. MVP does not depend on an unprotected market order.
- An SL order can trigger and remain unfilled after a price jump. Track raw trigger status, pending quantity and book prices. Reprice an existing exit when permitted and safe; alert immediately on failed execution.
- Per-leg stops survive a worker/network outage only while valid broker/exchange orders; the application-wide 5% trigger does not.

Time exit / kill:

- Serialize all writes for each contract; freeze entry and reconcile fills first.
- Prefer modifying the existing protective order to an executable exit only if the adapter/broker supports and tests that transition. Otherwise cancel it, wait for a terminal acknowledgement, re-read fills and outstanding short quantity, then close exactly the remaining quantity.
- A cancel timeout or stop fill during cancellation is an uncertain state, not permission to place a duplicate buy. Avoid orphaned stops creating accidental long positions after flattening. No assumption of native reduce-only or OCO support.
- Use fresh ask-priced marketable limits with bounded repricing. Entry price caps must not blindly govern emergency exits. Exhausted execution protection, price bands or market closure result in critical escalation; no claim of guaranteed flattening.
- Declare FLAT only when broker net quantities are zero and no strategy order remains capable of opening exposure. Archive the evidence.

## 7. Alerts that reach the user even if the runner dies

Three paths:

1. Runner events -> durable notification outbox -> Telegram (routine) and PagerDuty (critical).
2. Cloud infrastructure alarms -> PagerDuty independently of the Python process.
3. External dead-man monitor -> PagerDuty if strategy-progress heartbeats disappear. This service lives outside the trading host/cloud failure domain and does not need the runner to send its own failure message.

Heartbeat: every 15 seconds during the supervised trading window; external detection target 60–90 seconds subject to provider-supported granularity. Include session state, advancing event-loop sequence, data age and latest reconciliation status. A healthy unrelated sidecar must not conceal a frozen trading loop. Also monitor missed READY and FLAT deadlines independently, including cases where a heartbeat never started. Calendar-aware expected schedules must be registered ahead of the session.

| Severity | Examples | Notify/action |
|---|---|---|
| Informational | Ready, armed, skipped, both legs protected, normal stop, exit, EOD P&L | Telegram, deduplicated |
| Warning | 70% loss budget, brief feed degradation, near margin floor, login not complete | Telegram + push; clear required action |
| Critical | Missing/rejected protection, unknown order, naked leg timeout, 5% trigger, runner heartbeat missing, prolonged feed outage while exposed, failed time exit | Immediate push + Telegram; phone after 30 seconds without acknowledgement; repeat/escalate at 2 minutes, subject to configured provider capabilities |

Critical payload example:

`LIVE / SENSEX ATM straddle / CE short 1 lot / protection UNKNOWN / last broker sync 09:21:04 IST / new entries blocked / action: open Kite, verify CE position and stop / incident ID ...`

Include timestamps, actual position, stop coverage, automation action, retry state and specific manual action. Redact account identifiers and credentials. Acknowledgement silences escalation but does not clear the trading latch or resume entry. Recovery notification follows verified recovery. Do not resolve an incident merely because a process restarted.

Before arming: verify receipt on the user's actual phone, background notification permissions, India voice/SMS support, escalation timing and a missing-heartbeat test with the host disconnected. If an alert path fails before entry, skip. If all notification paths fail while exposed, enter exit-only and attempt orderly flattening through a healthy broker connection.

## 8. Infrastructure recommendation

For a low-frequency, one-lot MVP, use one active trading host with durable state and independent monitoring. Professional-grade reliability comes primarily from reconciliation, explicit failure states and recoverable order handling, not a large cluster.

Recommended stack:

- AWS Mumbai region; one on-demand Linux EC2 instance, initially 2 vCPU/4–8 GB RAM, measured before sizing up. No Spot instance for the trading writer.
- Dedicated Elastic IP for broker-facing IPv4 egress, registered in the Kite developer account. Verify actual egress from inside the container; prevent unintended IPv6/dynamic egress for mutations.
- Versioned Docker image supervised by host service management; pinned Stolgo/Bandl versions; no market-hours unattended deploy or dependency upgrade.
- Private managed PostgreSQL (RDS Multi-AZ for the reliability-first setup), durable intents/fills/session latch and transactional outbox. Separate storage of raw event archives in encrypted object storage. Point-in-time backups and tested restoration.
- Secrets Manager/instance role for secrets; no tokens in git, browser storage, logs or container image. Restrict API callback scope; normal authenticated login over HTTPS.
- Private dashboard via VPN or authenticated access; no public trading controls. Operator controls: arm today, pause entries, exit strategy, inspect reconciliation. Require authenticated audited commands, not free-text chat trading commands.
- CloudWatch host/process/log alarms plus externally hosted dead-man monitoring and phone escalation. No dependency on the dashboard for risk supervision.
- Warm standby in another availability zone prepared with compatible image/state access, but DISARMED. No automated dual-active failover for MVP.

Failure and recovery:

- Single order gateway is the only writer. A database lease assists coordination, but the broker does not enforce our fencing token.
- Before standby promotion, stop/fence the old process or revoke its order egress at infrastructure level, verify fencing, then move the registered EIP or use a pre-registered secondary IP under broker rules. Never assume a lease timeout alone prevents a partitioned old process from trading.
- New process starts RECOVERY, loads ledger, obtains the current day's orders/fills/positions, verifies protective orders, and defaults to exit-only if it finds exposure. It does not resume a missed entry. Compare local state to broker reality before writes.
- If the database fails: reject new risk. Retain exchange stops; risk worker uses last verified in-memory state and emergency local append-only journal to manage only reconciled residual exits if broker reads are healthy. Any uncertainty pages the operator. Test DB-loss behavior explicitly.
- Host failure target: detection under 90 seconds; operator recovery/fenced promotion within 5 minutes as an operational target, not an SLA. Existing protection is the first line during that window. Full broker outage requires manual broker-channel escalation; another EC2 host cannot fix it.

MVP alternatives: a reputable fixed-IP VPS can run the same software, but replacing managed DB, monitoring and recovery responsibilities with one VPS increases operational burden. A laptop is suitable for development or read-only shadow experiments, not the planned order writer. Kubernetes, Kafka, colocated HFT infrastructure and automatic cross-region writers are unnecessary for this pilot.

## 9. Code organization

Stolgo proposed modules:

- `strategy/builtins/sensex_atm_straddle.py`: pure versioned decisions and configuration.
- `live/runner.py`, `live/session.py`, `live/calendar.py`: scheduler/state machine/calendar validation.
- `data/live_bandl_source.py`: normalized stream consumption and bar closure logic.
- `broker/bandl.py`: Bandl order adapter; no strategy-owned direct broker calls.
- `live/order_gateway.py`, `live/reconcile.py`: serialized mutations, uncertain outcomes, per-leg recovery.
- `live/risk.py`: independent mandatory risk supervision.
- `live/journal.py`: durable ledger, migrations, session lock and outbox.
- `live/alerts.py`, `live/health.py`: incidents and progress monitoring.
- `live/paper.py`: live-quote fill model with spread/depth, latency and fault injection; no write credentials.
- CLI commands: planned `live preflight`, `live shadow`, `live run`, `live status`, `live pause`, `live flatten`; implement and document before presenting as runnable commands.
- `deploy/`: image build, infrastructure-as-code, service settings, dashboards/alarms and operator runbooks.

Bandl proposed additions:

- Mutation-safe form transport and first-class submit acknowledgements.
- Exact BFO instrument mapping and round-trip validation.
- Optional Kite streaming integration with native timestamp/depth/order-state preservation.
- REST live quote and order/basket margin preview facets with capability flags.
- Full-day order reconciliation access, raw status and cumulative-filled quantities.

Keep Bandl imports inside Stolgo data/broker integration boundaries. Update Stolgo HLD to describe multi-leg live execution and lifecycle persistence; the existing single-symbol historical engine cannot be made live by toggling a mode flag.

## 10. Delivery sequence and acceptance gates

Engineering estimate: approximately 10–15 focused working days for a first implementation, depending on missing broker/data integration behavior. This is an estimate, not a scheduled commitment. Eligible expiry sessions are weekly: validation sessions take calendar time separately.

| Phase | Deliverable | Gate |
|---|---|---|
| A: strategy/transport foundation | Freeze spec and 5% overlay; fix calendar/reporting; Bandl safe mutations, exact contracts and margin/stream interfaces | Deterministic fixtures; no blind mutation retries; raw acknowledgements survive follow-up read failure |
| B: runtime | Runner, ledger, risk, per-leg states, paper fills, recovery, alerts | Fault suite passes; loss/kill latches survive restart; no duplicate orders or orphan exits |
| C: infra/read-only rehearsal | Fixed-IP host, secrets, DB, external monitoring, live quotes and broker read reconciliation | Real phone alert received when host is killed; restore/fencing demonstrated; current calendar/master verified |
| D: shadow | At least 3 eligible expiry sessions with the actual frozen strategy, plus daily non-trading engineering drills | All intents/fills/decisions recorded, flat at end, no unexplained state, quote quality and execution budgets reviewed |
| E: supervised live canary | One lot, manual daily arm, user available with Kite open, 5% trigger and current margin verified | First entry/protect/exit cycle inspected; any critical defect returns to shadow |
| F: pilot | At least 5 eligible live sessions at one lot | Reconciled charges, slippage and MTM risk; no size increase from a short winning streak |

Shadow and live gates validate operations, not statistical alpha. Compare signal price vs executable bid/ask vs actual fill; record fee/slippage drift and emergency exits. Any change to strategy economics requires a new version and separate comparison.

Required fault tests:

- Broker accepts entry but HTTP response is lost; acknowledgement followed by failed status read.
- Partial first leg, second leg rejection, late fill after cancel, stop rejection.
- Stop triggers during time-exit cancellation; repeated/late/out-of-order WebSocket events.
- Triggered SL remains unfilled; gaps exceed limit; price bands reject modification.
- Process restart after submit but before persisting response; host network split; standby fencing.
- Stale feed, live feed reconnect, historical data stall, missing completed bar.
- Broker token expiry, static-IP rejection, rate limit, DB outage, disk full.
- User manually closes a leg; accidental unrelated position; broker/internal position mismatch.
- Holiday-shifted expiry, shortened session, changed lot size, no contract match.
- Telegram failure, PagerDuty failure, host disappears before first heartbeat, dead trading loop with healthy sidecar.
- 5% MTM breach while loss is not realized; no reentry after daily latch.

No production orders are used for fault injection. Offline broker fakes and live-data shadow mode test failures; the supervised live canary validates normal real execution with actual risk capital.

## 11. Professional operating model

A small professional setup separates research from execution, versions rules/config/data, keeps broker positions as reconciliation authority, accounts from actual fills, limits who can send orders, and maintains an on-call owner. It uses tested stop/exit handling, replayable event journals and controlled changes. Risk staff or independent controls can halt strategy risk; the strategy cannot overrule them. Deployment proceeds through simulation, shadow and limited-capital canaries.

For this MVP, implement those practices in a small service: one writer, one durable ledger, mandatory risk supervision, external alerts and a human with a tested broker-app recovery procedure. No infrastructure can ensure a naked options position exits during an exchange/broker outage.

## 12. Launch inputs still required

- Actual fixed capital allocation; 5% rupee threshold derives from it.
- Notification destination(s), phone escalation provider and tested contact details.
- Zerodha BFO/API/data access enabled, normal daily login and static-IP registration completed by account owner.
- Current margin/fees/order-type validation; sufficient free capital and one-lot risk budget.
- Cloud account/region access and spend approval when actual provisioning is requested.
- Named on-call operator available throughout the initial session; recorded readiness/arm action.

The implementation must refuse live arming when these settings are absent. Planning does not enable the account or place an order.

## Sources verified for this plan

- Kite authentication and next-day 06:00 token expiry: https://kite.trade/docs/connect/v3/user/
- Kite order lifecycle and parameters: https://kite.trade/docs/connect/v3/orders/
- Kite request encoding: https://www.kite.trade/docs/connect/v3/
- Kite WebSocket market depth and order updates: https://kite.trade/docs/connect/v3/websocket/
- Individual-developer order updates: https://kite.trade/docs/connect/v3/postbacks/
- Order/basket margin estimation: https://kite.trade/docs/connect/v3/margins/
- Zerodha static-IP requirement effective April 1, 2026: https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/static-ip
- Zerodha operational API changes including order rate/market protection: https://kite.trade/forum/discussion/15912/preparing-to-comply-with-sebis-retail-algo-rules-static-ip-ratelimits-order-types
- Stop-limit execution limitations: https://support.zerodha.com/category/trading-and-markets/charts-and-orders/order/articles/how-to-use-sl-l-order-like-a-sl-m-order
- BSE expiry-cycle notice: https://nsearchives.nseindia.com/corporate/BSE1_17062025160524_NSEintimation.pdf
- AWS Elastic IP: https://docs.aws.amazon.com/us_en/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html
- External missing-heartbeat detection: https://healthchecks.io/docs/
- PagerDuty escalation/notification rules: https://support.pagerduty.com/main/docs/notification-rules

Re-check broker/exchange policies, supported BFO order types and current market-session schedule immediately before deployment. Vendor documentation is evidence of interface behavior, not a guarantee of availability or execution.
