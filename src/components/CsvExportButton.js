export function CsvExportButton(disabled = false) {
  return `<button id="exportAnalysisCsvBtn" class="primary" ${disabled ? "disabled" : ""}>分析結果をCSV出力</button>`;
}
