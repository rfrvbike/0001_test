export function ScoreGauge({ totalScore, buyScore }) {
  const normalized = Math.max(0, Math.min(100, totalScore + 100)) / 2;
  return `
    <div class="score-gauge">
      <div class="gauge-ring" style="--score:${normalized}">
        <div class="gauge-center">
          <span>${totalScore}</span>
          <small>総合スコア</small>
        </div>
      </div>
      <div class="buy-score">
        <span>${buyScore}</span>
        <small>買いスコア</small>
      </div>
    </div>
  `;
}
