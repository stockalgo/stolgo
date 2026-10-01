import React, { useMemo } from "react";
import { calculateKnobEffects } from "../../lib/groupLogic.js";

export function KnobEffects({ runs = [], axes = {}, cols = [], rows = [], rowAxis, colAxis }) {
  const analysis = useMemo(
    () => calculateKnobEffects({ runs, axes, cols, rows, rowAxis, colAxis }),
    [runs, axes, cols, rows, rowAxis, colAxis]
  );

  if (!analysis) {
    return <div className="muted" style={{ padding: 16 }}>No knob analysis available</div>;
  }

  const getRatioClass = (pos, total) => {
    if (total === 0) return "";
    if (pos === total) return "pos";
    if (pos === 0) return "neg";
    return "accent";
  };

  return (
    <div>
      {/* 1. Column variants positive */}
      {analysis.colStats.map((cs) => (
        <div key={cs.key} className="kv kv--divided">
          <span>{cs.col} · variants positive</span>
          <span className={getRatioClass(cs.pos, cs.total)}>
            {cs.pos} / {cs.total}
          </span>
        </div>
      ))}

      {/* 2. Best col 2-valued axes */}
      {analysis.bestCol2ValAxes.map((bca, idx) => (
        <div key={`bca-${idx}`} className="kv kv--divided">
          <span>{bca.label}</span>
          <span className={getRatioClass(bca.pos, bca.total)}>
            {bca.pos} / {bca.total}
          </span>
        </div>
      ))}

      {/* 3. Other 2-valued axes over whole group */}
      {analysis.wholeGroup2ValAxes.map((wga, idx) => (
        <div key={`wga-${idx}`} className="kv">
          <span>{wga.label}</span>
          <span>
            {wga.val1} vs {wga.val2}
          </span>
        </div>
      ))}

      {/* Callout */}
      <div className="callout" style={{ marginTop: 10 }}>
        {analysis.calloutText}
      </div>
    </div>
  );
}
