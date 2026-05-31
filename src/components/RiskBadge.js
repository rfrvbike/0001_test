export function RiskBadge(level) {
  const label = { LOW: "LOW", MEDIUM: "MEDIUM", HIGH: "HIGH" }[level] || "MEDIUM";
  return `<span class="risk-badge ${label.toLowerCase()}">${label}</span>`;
}
