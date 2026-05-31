import { getInternalEnv } from "../config/env.js";
import { validateJQuantsConfig } from "../services/jquantsClient.js";

export function healthResponse(config = getInternalEnv()) {
  const validation = validateJQuantsConfig(config);
  const mode = !config.jquantsEnabled ? "mock" : validation.ok ? "api_key_ready" : "config_error";

  return {
    ok: true,
    service: "stock-analyzer-backend",
    mode,
    apiVersion: config.apiVersion,
    externalApiEnabled: Boolean(config.jquantsEnabled),
    jquantsEnabled: Boolean(config.jquantsEnabled),
    aiSummary: {
      mockEnabled: Boolean(config.aiSummaryMockEnabled),
      externalApiEnabled: Boolean(config.aiSummaryExternalApiEnabled),
      provider: "none"
    },
    themeSummary: {
      mockEnabled: Boolean(config.themeSummaryMockEnabled),
      externalNewsApiEnabled: Boolean(config.themeSummaryExternalNewsApiEnabled),
      scoreEnabled: Boolean(config.themeSummaryScoreEnabled)
    },
    didNetworkRequest: false,
    message: config.jquantsEnabled
      ? "Backend is running. J-Quants V2 API key mode is enabled. Real stock fetch depends on JQUANTS_USE_REAL_STOCKS."
      : "Backend is running. External APIs are disabled."
  };
}
