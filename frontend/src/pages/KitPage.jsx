import React, { useState, useEffect } from "react";
import { Button } from "../components/ui/Button.jsx";
import { Seg } from "../components/ui/Seg.jsx";
import { Tabs } from "../components/ui/Tabs.jsx";
import { Chip } from "../components/ui/Chip.jsx";
import { StatusBadge } from "../components/ui/StatusBadge.jsx";
import { VerdictPill } from "../components/ui/VerdictPill.jsx";
import { Panel } from "../components/ui/Panel.jsx";
import { Kpi, KpiStrip } from "../components/ui/Kpi.jsx";
import { Banner } from "../components/ui/Banner.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { Tooltip } from "../components/ui/Tooltip.jsx";

export function KitPage() {
  const [segVal, setSegVal] = useState("Price");
  const [tabVal, setTabVal] = useState("overview");

  useEffect(() => {
    document.title = "UI Kit · Stolgo";
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--gap)" }}>
      <section>
        <div className="eyebrow">Design system</div>
        <h1 style={{ margin: "4px 0 0", fontSize: "28px", fontWeight: 600 }}>
          Components &amp; states
        </h1>
        <div className="muted">
          Class names match <span className="mono">docs/design/components.css</span>. Built from real
          React components (UI plan §5).
        </div>
      </section>

      {/* Colour tokens */}
      <section className="panel">
        <div className="panel__head">
          <span className="eyebrow">Colour tokens</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(12, minmax(0, 1fr))", gap: "12px" }}>
          {[
            { name: "--bg-app", label: "app bg", bg: "var(--bg-app)" },
            { name: "--bg-panel", label: "panel", bg: "var(--bg-panel)" },
            { name: "--bg-raised", label: "raised", bg: "var(--bg-raised)" },
            { name: "--bg-active", label: "active", bg: "var(--bg-active)" },
            { name: "--line", label: "line", bg: "var(--line)" },
            { name: "--text-1", label: "text-1", bg: "var(--text-1)" },
            { name: "--text-muted", label: "text-muted", bg: "var(--text-muted)" },
            { name: "--accent", label: "accent", bg: "var(--accent)" },
            { name: "--pos", label: "pos", bg: "var(--pos)" },
            { name: "--neg", label: "neg", bg: "var(--neg)" },
            { name: "--neg-text", label: "neg-text", bg: "var(--neg-text)" },
            { name: "--info", label: "info", bg: "var(--info)" },
          ].map((c) => (
            <div key={c.name} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div
                style={{
                  height: "44px",
                  borderRadius: "6px",
                  border: "1px solid var(--line)",
                  background: c.bg,
                }}
              />
              <span className="mono" style={{ fontSize: "11px", color: "var(--text-2)" }}>
                {c.name}
              </span>
              <span className="faint" style={{ fontSize: "11px" }}>
                {c.label}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* 3 columns: Buttons & Tabs, Badges & Numbers, Verdicts */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "var(--gap)" }}>
        <Panel eyebrow="Buttons · Button">
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <Button variant="primary">Primary</Button>
            <Button>Default</Button>
            <Button variant="ghost">Ghost</Button>
            <Button size="sm">Small</Button>
            <Button disabled>Disabled</Button>
            <Button
              icon={
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="15 3 21 3 21 9" />
                  <polyline points="9 21 3 21 3 15" />
                  <line x1="21" y1="3" x2="14" y2="10" />
                  <line x1="3" y1="21" x2="10" y2="14" />
                </svg>
              }
              aria-label="Expand"
            />
          </div>

          <div className="eyebrow" style={{ margin: "16px 0 8px" }}>
            Segmented · Tabs
          </div>
          <Seg
            options={[
              { label: "Price", value: "Price" },
              { label: "Equity", value: "Equity" },
            ]}
            value={segVal}
            onChange={setSegVal}
          />
          <div style={{ marginTop: "10px" }}>
            <Tabs
              tabs={[
                { id: "overview", label: "Overview" },
                { id: "trades", label: "Trades", count: 157 },
                { id: "diagnostics", label: "Diagnostics" },
              ]}
              activeTab={tabVal}
              onChange={setTabVal}
            />
          </div>
        </Panel>

        <Panel eyebrow="StatusBadge · all values">
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <StatusBadge status="ok" />
            <StatusBadge status="low_sample" />
            <StatusBadge status="short_window" />
            <StatusBadge status="data_issues" />
            <StatusBadge status="superseded" />
            <StatusBadge status="empty" />
            <span className="badge badge--info">calendar_daily</span>
          </div>

          <div className="eyebrow" style={{ margin: "16px 0 8px" }}>
            Chips
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <Chip>NIFTY</Chip>
            <Chip selected as="button">
              Selected
            </Chip>
            <Chip dotColor="var(--market-nifty-0)">NIFTY 0-DTE</Chip>
          </div>

          <div className="eyebrow" style={{ margin: "16px 0 8px" }}>
            Money &amp; numbers
          </div>
          <div className="mono" style={{ display: "flex", gap: "16px" }}>
            <span className="pos">+₹30,331</span>
            <span className="neg">−₹6,014</span>
            <span>0.73</span>
            <span className="neg">−9.5%</span>
            <span className="muted">—</span>
          </div>
        </Panel>

        <Panel eyebrow="VerdictPill · 5 states">
          <div style={{ display: "grid", gap: "8px" }}>
            <VerdictPill
              verdict={{
                label: "EDGE · ROBUST",
                style: "green",
                text: "Survives bootstrap and top-5 removal",
              }}
            />
            <VerdictPill
              verdict={{
                label: "EDGE · FRAGILE",
                style: "amber",
                text: "Profitable, but the best 5 trades carry it",
              }}
            />
            <VerdictPill
              verdict={{
                label: "EDGE · UNPROVEN",
                style: "amber",
                text: "Fewer than 30 trades",
              }}
            />
            <VerdictPill
              verdict={{
                label: "NO EDGE",
                style: "red",
                text: "P(net > 0) below 80%",
              }}
            />
            <VerdictPill
              verdict={{
                label: "NO TRADES",
                style: "muted",
                text: "Nothing to evaluate",
              }}
            />
          </div>
        </Panel>
      </div>

      {/* KPI Strip */}
      <KpiStrip>
        <Kpi label="Net P&L" value="+₹30,331" sub="+16.9% on capital" pos />
        <Kpi
          label="CAGR"
          value="+44.4%"
          sub="from 65 sessions · not comparable"
          warn
          warnTooltip="Annualised from a short window"
        />
        <Kpi label="Sharpe" value="0.73" sub="daily, √252" />
        <Kpi label="Avg R" value="—" sub="R not recorded for this run" muted />
        <Kpi label="Loading" loading />
        <Kpi label="Max drawdown" value="−9.5%" sub="347 sessions" neg />
      </KpiStrip>

      {/* Empty states */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "var(--gap)" }}>
        <EmptyState
          title="No price data for this run"
          variant="no-price"
          action={<Button size="sm">Show equity instead</Button>}
        />
        <EmptyState variant="not-migrated" />
        <EmptyState variant="no-trades" />
        <EmptyState variant="error" action={<Button size="sm">Retry</Button>} />
      </div>

      {/* Banners & Tooltip */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "var(--gap)" }}>
        <Banner variant="warn">Warning banner: amber, for data issues and short windows.</Banner>
        <Banner variant="bad">Error banner: red, for failed loads.</Banner>
        <div style={{ position: "relative", height: "120px" }}>
          <div className="tooltip" style={{ left: 0, top: 0, position: "absolute" }}>
            <div className="mono" style={{ color: "var(--text-1)" }}>
              08 Sep 2026 · #157
            </div>
            <div className="kv">
              <span>Net</span>
              <span className="pos">+₹1,155</span>
            </div>
            <div className="kv">
              <span>R</span>
              <span>+0.64</span>
            </div>
            <div className="kv">
              <span>Exit</span>
              <span>TIME_EXIT</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table states */}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Row states</th>
              <th className="num">Net</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Default</td>
              <td className="num pos">+₹1,155</td>
              <td className="muted">36px height</td>
            </tr>
            <tr style={{ background: "var(--bg-raised)" }}>
              <td>Hover</td>
              <td className="num neg">−₹902</td>
              <td className="muted">var(--bg-raised)</td>
            </tr>
            <tr aria-selected="true">
              <td>Selected</td>
              <td className="num pos">+₹3,043</td>
              <td className="muted">bg-active + 2px amber inset</td>
            </tr>
            <tr style={{ opacity: 0.78 }}>
              <td>Low sample (dimmed)</td>
              <td className="num pos">+₹17,307</td>
              <td className="muted">opacity .78</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
