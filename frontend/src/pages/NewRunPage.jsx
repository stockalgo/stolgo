import React, { useState, useEffect, useMemo } from "react";
import { listRuns } from "../api/endpoints.js";
import { useToast } from "../context/ToastContext.jsx";

const DEFAULT_FORM = {
  strategyFile: "examples/trend_breakout_backtest.py",
  strategyClass: "TrendBreakout",
  dataCsv: "data/NIFTY_15m.csv",
  runId: "nifty-trend-breakout-15m",
  startingCash: "180000",
  commission: "0.0003",
};

export function NewRunPage() {
  const { showToast } = useToast();
  const [form, setForm] = useState(DEFAULT_FORM);
  const [existingRunIds, setExistingRunIds] = useState(new Set());

  useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((data) => {
        if (!cancelled && data?.items) {
          setExistingRunIds(new Set(data.items.map((r) => r.id)));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleReset = () => {
    setForm(DEFAULT_FORM);
  };

  // Field validations
  const errors = useMemo(() => {
    const errs = {};

    // 1. Strategy file
    if (!form.strategyFile.trim()) {
      errs.strategyFile = "Strategy file is required";
    } else if (!form.strategyFile.trim().endsWith(".py")) {
      errs.strategyFile = "Must be a Python file ending with .py";
    }

    // 2. Strategy class
    if (!form.strategyClass.trim()) {
      errs.strategyClass = "Strategy class is required";
    } else if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(form.strategyClass.trim())) {
      errs.strategyClass = "Must be a valid Python class identifier";
    }

    // 3. Data CSV
    if (!form.dataCsv.trim()) {
      errs.dataCsv = "Data file is required";
    } else if (
      !form.dataCsv.trim().endsWith(".csv") &&
      !form.dataCsv.trim().endsWith(".parquet")
    ) {
      errs.dataCsv = "Must end with .csv or .parquet";
    }

    // 4. Run ID
    if (!form.runId.trim()) {
      errs.runId = "Run ID is required";
    } else if (!/^[a-z0-9][a-z0-9-]{2,80}$/.test(form.runId.trim())) {
      errs.runId =
        "Must be 3-80 characters, lowercase letters, digits, and dashes only";
    }

    // 5. Starting Cash
    const cashNum = parseFloat(form.startingCash);
    if (!form.startingCash.trim() || isNaN(cashNum) || cashNum <= 0) {
      errs.startingCash = "Starting cash must be greater than 0";
    }

    // 6. Commission
    const commNum = parseFloat(form.commission);
    if (
      !form.commission.trim() ||
      isNaN(commNum) ||
      commNum < 0 ||
      commNum >= 0.05
    ) {
      errs.commission = "Commission must be between 0 and 0.05";
    }

    return errs;
  }, [form]);

  const runIdExists = useMemo(() => {
    return existingRunIds.has(form.runId.trim());
  }, [existingRunIds, form.runId]);

  const isValid = Object.keys(errors).length === 0;

  // Generated CLI command
  const command = useMemo(() => {
    return `stolgo ${form.strategyFile.trim() || "strategy.py"} \\
  --class ${form.strategyClass.trim() || "Strategy"} \\
  --data ${form.dataCsv.trim() || "data.csv"} \\
  --cash ${form.startingCash.trim() || "100000"} \\
  --commission ${form.commission.trim() || "0.0003"} \\
  --output runs/${form.runId.trim() || "new-run"}`;
  }, [form]);

  const handleCopy = () => {
    navigator.clipboard.writeText(command);
    showToast("Copied");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Header */}
      <section>
        <div className="eyebrow">New run</div>
        <h1 style={{ margin: "4px 0 0", fontSize: 28, fontWeight: 600 }}>
          Build a backtest command
        </h1>
        <div className="muted" style={{ maxWidth: 760 }}>
          The UI cannot start runs yet. Fill the form, copy the command, run it
          in a terminal, then refresh the Library. Only the flags the{" "}
          <span className="mono">stolgo</span> CLI supports today are shown.
        </div>
      </section>

      {/* Main Grid */}
      <div
        className="grid"
        style={{ gridTemplateColumns: "minmax(0, 1fr) 420px", gap: "var(--gap)" }}
      >
        {/* Form Panel */}
        <section className="panel">
          <div className="panel__head">
            <span className="panel__title">Parameters</span>
          </div>

          <div
            className="grid"
            style={{
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: 16,
            }}
          >
            {/* Field 1: Strategy file */}
            <label className="field">
              Strategy file (.py)
              <input
                className="input mono"
                value={form.strategyFile}
                onChange={(e) => handleChange("strategyFile", e.target.value)}
              />
              {errors.strategyFile && (
                <span className="neg" style={{ fontSize: 11 }}>
                  {errors.strategyFile}
                </span>
              )}
            </label>

            {/* Field 2: Strategy class */}
            <label className="field">
              Strategy class
              <input
                className="input mono"
                value={form.strategyClass}
                onChange={(e) => handleChange("strategyClass", e.target.value)}
              />
              {errors.strategyClass && (
                <span className="neg" style={{ fontSize: 11 }}>
                  {errors.strategyClass}
                </span>
              )}
            </label>

            {/* Field 3: Data CSV */}
            <label className="field">
              Data CSV (OHLCV)
              <input
                className="input mono"
                value={form.dataCsv}
                onChange={(e) => handleChange("dataCsv", e.target.value)}
              />
              {errors.dataCsv && (
                <span className="neg" style={{ fontSize: 11 }}>
                  {errors.dataCsv}
                </span>
              )}
            </label>

            {/* Field 4: Run ID */}
            <label className="field">
              Run id (folder name under runs/)
              <input
                className="input mono"
                value={form.runId}
                onChange={(e) => handleChange("runId", e.target.value)}
              />
              <span className="faint">
                Lowercase, digits and dashes only. Must not already exist.
              </span>
              {errors.runId && (
                <span className="neg" style={{ fontSize: 11 }}>
                  {errors.runId}
                </span>
              )}
              {!errors.runId && runIdExists && (
                <span className="accent" style={{ fontSize: 11 }}>
                  ⚠ Warning: A run with this ID already exists.
                </span>
              )}
            </label>

            {/* Field 5: Starting cash */}
            <label className="field">
              Starting cash (₹)
              <input
                type="number"
                className="input mono"
                value={form.startingCash}
                onChange={(e) => handleChange("startingCash", e.target.value)}
              />
              {errors.startingCash && (
                <span className="neg" style={{ fontSize: 11 }}>
                  {errors.startingCash}
                </span>
              )}
            </label>

            {/* Field 6: Commission */}
            <label className="field">
              Commission (fraction per fill)
              <input
                type="number"
                step="0.0001"
                className="input mono"
                value={form.commission}
                onChange={(e) => handleChange("commission", e.target.value)}
              />
              <span className="faint">
                0.0003 = 3 bps. Statutory F&amp;O charges are not modelled by
                this CLI.
              </span>
              {errors.commission && (
                <span className="neg" style={{ fontSize: 11 }}>
                  {errors.commission}
                </span>
              )}
            </label>
          </div>

          {/* Command preview */}
          <div className="eyebrow" style={{ margin: "18px 0 8px" }}>
            Command
          </div>
          <div className="code" style={{ whiteSpace: "pre-wrap" }}>
            {command}
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleCopy}
              disabled={!isValid}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <rect x="9" y="9" width="11" height="11" rx="2" />
                <path d="M5 15V5a1 1 0 0 1 1-1h10" />
              </svg>
              Copy command
            </button>
            <button type="button" className="btn" onClick={handleReset}>
              Reset
            </button>
          </div>
        </section>

        {/* Aside Panels */}
        <aside className="grid" style={{ alignContent: "start", gap: "var(--gap)" }}>
          <section className="panel">
            <div className="panel__head">
              <span className="panel__title">After it finishes</span>
            </div>
            <ol
              style={{
                margin: 0,
                paddingLeft: 18,
                color: "var(--text-2)",
                lineHeight: 1.8,
              }}
            >
              <li>
                The run folder appears in <span className="mono">runs/</span>{" "}
                with a v2 manifest.
              </li>
              <li>The server re-indexes on the next Library load.</li>
              <li>
                Open it from the Library. It is sorted by creation time when you
                choose “Newest”.
              </li>
            </ol>
          </section>

          <section className="panel">
            <div className="panel__head">
              <span className="panel__title">Options research runs</span>
            </div>
            <div style={{ color: "var(--text-2)", fontSize: 13 }}>
              Options replays (strangles, iron condors, timing sweeps) come from
              the research generators. They must call{" "}
              <span className="mono">export_run_v2()</span> to appear here with
              full diagnostics.
            </div>
            <div className="callout" style={{ marginTop: 10 }}>
              Runner API (queue from UI) is <b>not built</b>. This page will gain
              a “Run” button when <span className="mono">POST /api/runs</span>{" "}
              exists.
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
