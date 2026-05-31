export function BulkAnalysisSummary(summary) {
  const items = [
    ["対象", summary.total],
    ["買い候補", summary.buy],
    ["分割買い候補", summary.splitBuy],
    ["押し目待ち", summary.pullback],
    ["高値掴み注意", summary.overheatWarning],
    ["見送り", summary.skip],
    ["過熱HIGH", summary.highRisk],
    ["上方修正", summary.upwardRevision],
    ["下方修正", summary.downwardRevision],
    ["国策テーマ", summary.policyTheme],
    ["CSV取込", summary.csv],
    ["モック", summary.mock]
  ];
  return `
    <div class="bulk-summary">
      ${items.map(([label, value]) => `<div><span>${label}</span><strong>${value}件</strong></div>`).join("")}
    </div>
  `;
}
