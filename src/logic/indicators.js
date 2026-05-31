export function calculateIndicators(stock, today = new Date()) {
  const price = stock.price;
  const averageVolume20d = stock.averageVolume20d ?? stock.avgVolume20 ?? 0;
  const highYtd = stock.highYtd ?? stock.ytdHigh ?? 0;
  const volumeRatio = averageVolume20d > 0 ? stock.volume / averageVolume20d : 0;
  const ma25Deviation = stock.ma25 > 0 ? ((price - stock.ma25) / stock.ma25) * 100 : 0;
  const ma75Deviation = stock.ma75 > 0 ? ((price - stock.ma75) / stock.ma75) * 100 : 0;
  const high52wDrawdown = stock.high52w > 0 ? ((stock.high52w - price) / stock.high52w) * 100 : 0;
  const ytdHighDrawdown = highYtd > 0 ? ((highYtd - price) / highYtd) * 100 : 0;
  const change = stock.change ?? price - stock.previousClose;
  const changePercent = stock.changePercent ?? (stock.previousClose > 0 ? (change / stock.previousClose) * 100 : 0);
  const nextEarningsDate = stock.nextEarningsDate ?? stock.disclosure?.nextEarningsDate;
  const daysToEarnings = daysBetween(today, nextEarningsDate);
  const isBeforeEarnings = stock.isBeforeEarnings ?? (daysToEarnings >= 0 && daysToEarnings <= 10);

  return {
    currentPrice: price,
    change,
    changePercent,
    volume: stock.volume,
    volumeRatio,
    ma25: stock.ma25,
    ma75: stock.ma75,
    ma25Deviation,
    ma75Deviation,
    rsi: stock.rsi,
    high52w: stock.high52w,
    high52wDrawdown,
    ytdHigh: highYtd,
    ytdHighDrawdown,
    daysToEarnings,
    isBeforeEarnings,
    nearHigh52w: high52wDrawdown <= 3,
    overMa25: ma25Deviation >= 10,
    overheatRsi: stock.rsi >= 75,
    volumeSpike: volumeRatio >= 1.5,
    aboveMa25: price > stock.ma25,
    aboveMa75: price > stock.ma75,
    ma25AboveMa75: stock.ma25 > stock.ma75
  };
}

function daysBetween(today, isoDate) {
  if (!isoDate) return 999;
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const target = new Date(`${isoDate}T00:00:00`);
  return Math.ceil((target - start) / 86400000);
}
