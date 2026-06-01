import {
  MASTER_SYNC_SOURCES,
  MasterSyncManager,
  normalizeMasterSyncSource
} from "../services/masterSync/index.js";

const manager = new MasterSyncManager();

export async function routeMasterSync(req, url) {
  if (url.pathname === "/api/master-sync/dry-run") {
    if (req.method !== "GET") return methodNotAllowed(["GET"]);
    return handleDryRun(url);
  }

  if (url.pathname === "/api/master-sync/sync") {
    if (req.method !== "POST") return methodNotAllowed(["POST"]);
    return handleSync(req);
  }

  return null;
}

async function handleDryRun(url) {
  const source = normalizeMasterSyncSource(url.searchParams.get("source") || MASTER_SYNC_SOURCES.JQUANTS_MOCK);
  if (source === MASTER_SYNC_SOURCES.JQUANTS_REAL) return realNotImplemented();
  if (source !== MASTER_SYNC_SOURCES.JQUANTS_MOCK) {
    return {
      status: 400,
      body: {
        ok: false,
        error: `Unsupported master sync source: ${source}`,
        source,
        didNetworkRequest: false
      }
    };
  }

  const result = await manager.buildMasterSyncDryRun(source);
  return {
    status: 200,
    body: {
      ...result,
      ok: true,
      mode: "master_sync_dry_run",
      didNetworkRequest: false
    }
  };
}

async function handleSync(req) {
  const body = await readJsonBody(req);
  const source = normalizeMasterSyncSource(body.source || MASTER_SYNC_SOURCES.JQUANTS_MOCK);
  if (source === MASTER_SYNC_SOURCES.JQUANTS_REAL) return realNotImplemented();
  if (source !== MASTER_SYNC_SOURCES.JQUANTS_MOCK) {
    return {
      status: 400,
      body: {
        ok: false,
        error: `Unsupported master sync source: ${source}`,
        source,
        didNetworkRequest: false
      }
    };
  }

  const result = await manager.syncMaster(source);
  return {
    status: 200,
    body: {
      ok: true,
      mode: "master_sync",
      source: result.source,
      count: result.count,
      importedAt: result.importedAt,
      records: result.records,
      warnings: result.warnings,
      didNetworkRequest: false
    }
  };
}

function realNotImplemented() {
  return {
    status: 501,
    body: {
      ok: false,
      error: "JQUANTS_REAL is not implemented. Real J-Quants API access is disabled for master sync.",
      source: MASTER_SYNC_SOURCES.JQUANTS_REAL,
      didNetworkRequest: false
    }
  };
}

function methodNotAllowed(methods) {
  return {
    status: 405,
    body: {
      ok: false,
      error: "Method not allowed",
      allowedMethods: methods,
      didNetworkRequest: false
    }
  };
}

function readJsonBody(req) {
  return new Promise((resolve) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 4096) req.destroy();
    });
    req.on("end", () => {
      if (!raw.trim()) {
        resolve({});
        return;
      }
      try {
        const parsed = JSON.parse(raw);
        resolve(parsed && typeof parsed === "object" ? parsed : {});
      } catch {
        resolve({});
      }
    });
    req.on("error", () => resolve({}));
  });
}
