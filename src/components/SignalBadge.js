import { escapeHtml } from "./formatters.js";

export function SignalBadge(signal) {
  const styles = {
    買い候補: "good",
    分割買い候補: "good",
    押し目待ち: "wait",
    様子見: "neutral",
    高値掴み注意: "danger",
    利確候補: "warning",
    損切り警戒: "danger",
    見送り: "neutral"
  };
  return `<span class="signal-badge ${styles[signal] || "neutral"}">${escapeHtml(signal)}</span>`;
}
