const MOCK_THEME_MAP = {
  "7203": {
    themes: ["自動車", "円安メリット", "EV", "ハイブリッド", "グローバル景気", "決算期待"],
    importance: "medium"
  },
  "6758": {
    themes: ["エンタメ", "半導体", "イメージセンサー", "ゲーム", "AI関連"],
    importance: "medium"
  },
  "8035": {
    themes: ["半導体", "AI投資", "生成AI", "設備投資", "米国ハイテク株連動"],
    importance: "high"
  },
  "9984": {
    themes: ["AI関連", "半導体投資", "Arm", "ナスダック連動", "投資会社リスク"],
    importance: "high"
  },
  SPACE_THEME_SAMPLE: {
    themes: ["SpaceX上場観測", "宇宙関連", "衛星通信", "防衛宇宙", "思惑買い", "短期過熱"],
    importance: "high"
  }
};

export function buildThemeSummary(stockData, options = {}) {
  if (options.enabled === false) {
    return {
      status: {
        enabled: false,
        source: "LOCAL_MOCK_THEME",
        externalNewsApiUsed: false,
        externalAiUsed: false,
        message: "ニュース・テーマ材料レイヤーは無効です。"
      }
    };
  }

  const manualThemes = normalizeThemes(options.manualThemes || stockData?.manualThemes || stockData?.themeInput);
  const mock = getMockThemesForStock(stockData?.code);
  const themes = unique([...manualThemes, ...safeArray(mock?.themes)]);
  const available = themes.length > 0;
  const themeSummary = {
    available,
    source: manualThemes.length ? "MANUAL_AND_LOCAL_MOCK_THEME" : "LOCAL_MOCK_THEME",
    externalNewsApiUsed: false,
    externalAiUsed: false,
    themes,
    headlineLikeItems: available ? [
      {
        title: `${themes.slice(0, 3).join("・")}関連として見られる可能性があります`,
        type: "theme",
        importance: mock?.importance || (manualThemes.length ? "medium" : "low"),
        source: manualThemes.length ? "manual_and_local_mock" : "local_mock",
        url: null
      }
    ] : [],
    themeScore: 0,
    themeScoreMax: 2,
    themeScoreApplied: false,
    comment: "",
    risks: [],
    disclaimer: "テーマ材料は参考情報です。実売買前には必ず公式情報と最新ニュースを確認してください。"
  };
  themeSummary.comment = buildThemeComment(themeSummary);
  themeSummary.risks = buildThemeRisks(themeSummary);
  themeSummary.structuredPayload = buildThemeStructuredPayload(themeSummary);
  return themeSummary;
}

export function getMockThemesForStock(code) {
  const key = String(code || "").trim();
  return MOCK_THEME_MAP[key] || null;
}

export function buildThemeComment(themeSummary) {
  if (!themeSummary?.available) {
    return "この銘柄に対応するローカルテーマ材料はまだ登録されていません。";
  }
  const themes = safeArray(themeSummary.themes);
  return `この銘柄は${themes.slice(0, 4).join("・")}などのテーマで見られる可能性があります。ただし、今回のテーマ情報は外部ニュースAPIではなくローカルモックまたは手動入力です。`;
}

export function buildThemeRisks(themeSummary) {
  if (!themeSummary?.available) return [];
  const risks = [
    "テーマ買いは短期的に過熱しやすい場合があります",
    "ニュースや思惑だけで売買判断しないでください",
    "外部ニュースAPI未接続のため、最新ニュースは別途確認してください"
  ];
  if (safeArray(themeSummary.themes).some((theme) => /思惑|短期過熱|SpaceX|宇宙/.test(theme))) {
    risks.push("思惑性の高いテーマは材料出尽くしや急反落に注意が必要です");
  }
  return unique(risks);
}

export function buildThemeStructuredPayload(themeSummary) {
  return {
    available: Boolean(themeSummary?.available),
    themes: safeArray(themeSummary?.themes),
    comment: themeSummary?.comment || "",
    risks: safeArray(themeSummary?.risks),
    source: themeSummary?.source || "LOCAL_MOCK_THEME",
    externalNewsApiUsed: false,
    externalAiUsed: false
  };
}

function normalizeThemes(value) {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  if (!value) return [];
  return String(value)
    .split(/[,\u3001\u30fb]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function safeArray(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}
