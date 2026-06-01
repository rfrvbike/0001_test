import {
  JQUANTS_MASTER_MOCK_SOURCE,
  buildCsvFromMasterData,
  fetchMasterMock,
  normalizeMasterData
} from "./jquantsMasterService.js";
import {
  mergeStockMasterRows
} from "./stockMasterCsvService.js";

export const MASTER_SYNC_SOURCES = Object.freeze({
  CSV_IMPORT: "CSV_IMPORT",
  JQUANTS_MOCK: JQUANTS_MASTER_MOCK_SOURCE,
  JQUANTS_REAL: "JQUANTS_REAL"
});

export class MasterSyncProvider {
  constructor(source) {
    this.source = source;
  }

  async sync() {
    throw new Error("MasterSyncProvider.sync() is not implemented.");
  }

  async dryRun() {
    const result = await this.sync({ dryRun: true });
    return buildMasterSyncDryRunSummary(result);
  }
}

export class MockMasterSyncProvider extends MasterSyncProvider {
  constructor() {
    super(MASTER_SYNC_SOURCES.JQUANTS_MOCK);
  }

  async sync() {
    const fetched = await fetchMasterMock();
    const records = normalizeMasterData(fetched.rows);
    const csv = buildCsvFromMasterData(records);
    return buildMasterSyncResult({
      source: MASTER_SYNC_SOURCES.JQUANTS_MOCK,
      records,
      warnings: [],
      didNetworkRequest: false,
      importedAt: new Date().toISOString(),
      csvText: csv.csvText,
      fetchedCount: fetched.rows.length,
      csvCount: csv.count
    });
  }
}

export class CsvMasterSyncProvider extends MasterSyncProvider {
  constructor(records = [], meta = {}) {
    super(MASTER_SYNC_SOURCES.CSV_IMPORT);
    this.records = records;
    this.meta = meta;
  }

  async sync() {
    const records = mergeStockMasterRows(this.records);
    return buildMasterSyncResult({
      source: MASTER_SYNC_SOURCES.CSV_IMPORT,
      records,
      warnings: [],
      didNetworkRequest: false,
      importedAt: this.meta.importedAt || new Date().toISOString(),
      fetchedCount: records.length,
      csvCount: records.length
    });
  }
}

export class JQuantsMasterSyncProvider extends MasterSyncProvider {
  constructor() {
    super(MASTER_SYNC_SOURCES.JQUANTS_REAL);
  }

  async sync() {
    throw new Error("JQUANTS_REAL master sync is not implemented. Real J-Quants API access is disabled in this mock-only foundation.");
  }

  async dryRun() {
    throw new Error("JQUANTS_REAL dry-run is not implemented without an approved mock transport.");
  }
}

export class MasterSyncManager {
  constructor(providers = {}) {
    this.providers = {
      [MASTER_SYNC_SOURCES.CSV_IMPORT]: providers[MASTER_SYNC_SOURCES.CSV_IMPORT] || new CsvMasterSyncProvider(),
      [MASTER_SYNC_SOURCES.JQUANTS_MOCK]: providers[MASTER_SYNC_SOURCES.JQUANTS_MOCK] || new MockMasterSyncProvider(),
      [MASTER_SYNC_SOURCES.JQUANTS_REAL]: providers[MASTER_SYNC_SOURCES.JQUANTS_REAL] || new JQuantsMasterSyncProvider()
    };
  }

  getProvider(source) {
    const normalized = normalizeMasterSyncSource(source);
    const provider = this.providers[normalized];
    if (!provider) throw new Error(`Unsupported master sync source: ${source}`);
    return provider;
  }

  async syncMaster(source, options = {}) {
    return this.getProvider(source).sync(options);
  }

  async buildMasterSyncDryRun(source, options = {}) {
    const provider = this.getProvider(source);
    if (typeof provider.dryRun === "function") {
      return provider.dryRun(options);
    }
    const result = await provider.sync({ ...options, dryRun: true });
    return buildMasterSyncDryRunSummary(result);
  }
}

export async function syncMaster(source = MASTER_SYNC_SOURCES.JQUANTS_MOCK, options = {}) {
  return new MasterSyncManager(options.providers).syncMaster(source, options);
}

export async function buildMasterSyncDryRun(source = MASTER_SYNC_SOURCES.JQUANTS_MOCK, options = {}) {
  return new MasterSyncManager(options.providers).buildMasterSyncDryRun(source, options);
}

export function buildMasterSyncResult({
  source,
  records = [],
  warnings = [],
  didNetworkRequest = false,
  importedAt = new Date().toISOString(),
  csvText = "",
  fetchedCount = records.length,
  csvCount = records.length
} = {}) {
  const safeRecords = mergeStockMasterRows(records);
  return {
    source: normalizeMasterSyncSource(source),
    count: safeRecords.length,
    importedAt,
    records: safeRecords,
    warnings: Array.isArray(warnings) ? warnings.map((warning) => String(warning)) : [],
    didNetworkRequest: Boolean(didNetworkRequest),
    fetchedCount: Number.isFinite(Number(fetchedCount)) ? Number(fetchedCount) : safeRecords.length,
    csvCount: Number.isFinite(Number(csvCount)) ? Number(csvCount) : safeRecords.length,
    csvText: String(csvText || "")
  };
}

export function buildMasterSyncDryRunSummary(result = {}) {
  return {
    ok: true,
    source: normalizeMasterSyncSource(result.source),
    count: Number.isFinite(Number(result.count)) ? Number(result.count) : 0,
    fetchedCount: Number.isFinite(Number(result.fetchedCount)) ? Number(result.fetchedCount) : Number(result.count || 0),
    csvCount: Number.isFinite(Number(result.csvCount)) ? Number(result.csvCount) : Number(result.count || 0),
    warnings: Array.isArray(result.warnings) ? result.warnings : [],
    didNetworkRequest: Boolean(result.didNetworkRequest),
    importedAt: result.importedAt || "",
    sampleRows: Array.isArray(result.records) ? result.records.slice(0, 5) : []
  };
}

export function normalizeMasterSyncSource(source) {
  const value = String(source || MASTER_SYNC_SOURCES.CSV_IMPORT).trim().toUpperCase();
  if (value === MASTER_SYNC_SOURCES.JQUANTS_MOCK) return MASTER_SYNC_SOURCES.JQUANTS_MOCK;
  if (value === MASTER_SYNC_SOURCES.JQUANTS_REAL) return MASTER_SYNC_SOURCES.JQUANTS_REAL;
  return MASTER_SYNC_SOURCES.CSV_IMPORT;
}
