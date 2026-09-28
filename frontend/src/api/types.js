/**
 * JSDoc type definitions matching API v2 contract (§4.1-4.6).
 */

/** @typedef {"ok"|"low_sample"|"short_window"|"data_issues"|"superseded"|"empty"} RunStatus */

/**
 * @typedef {Object} RunSummary
 * @property {string} id
 * @property {string} name
 * @property {RunStatus} status
 * @property {string[]} status_reasons
 * @property {string[]} markets
 * @property {string} structure
 * @property {number[]} dte
 * @property {{id: string|null, label: string|null, axes: Object}} group
 * @property {{start: string, end: string, sessions: number}} window
 * @property {number} capital
 * @property {Object<string, number|null>} metrics
 * @property {{p_net_positive: number|null, net_without_top5: number|null}} robustness
 * @property {{trades_with_missing_data: number, trades_total: number}} data_quality
 * @property {{ohlcv: boolean, legs: boolean, intraday_equity: boolean, audit: boolean}} has
 * @property {string} created_at
 */

/**
 * @typedef {RunSummary & {
 *   instrument: Object,
 *   config: Object,
 *   diagnostics: Object,
 *   metric_defs: MetricDef[]
 * }} RunDetail
 */

/**
 * @typedef {Object} MetricDef
 * @property {string} key
 * @property {string} label
 * @property {"inr"|"fraction"|"ratio"|"count"|"sessions"|"r"} unit
 * @property {number} decimals
 * @property {"higher"|"lower"|"none"} better
 * @property {string} help
 */
