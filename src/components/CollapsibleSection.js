import { escapeHtml } from "./formatters.js";

export function CollapsibleSection({ title, defaultOpen = false, children = "", className = "" } = {}) {
  return `
    <details class="collapsible-section ${escapeHtml(className)}" ${defaultOpen ? "open" : ""}>
      <summary>${escapeHtml(title || "詳細")}</summary>
      <div class="collapsible-body">
        ${children || ""}
      </div>
    </details>
  `;
}
