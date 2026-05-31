import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { env } from "./config/env.js";
import { healthResponse } from "./routes/health.js";
import { routeStocks } from "./routes/stocks.js";

export function createServer() {
  return http.createServer(async (req, res) => {
    const url = new URL(req.url, `http://${req.headers.host || `${env.host}:${env.port}`}`);
    const routed = await route(req, url);
    sendJson(res, routed.status, routed.body);
  });
}

async function route(req, url) {
  if (req.method !== "GET") {
    return { status: 405, body: { ok: false, error: "Method not allowed" } };
  }
  if (url.pathname === "/api/health") {
    return { status: 200, body: healthResponse() };
  }
  const stockRoute = await routeStocks(req, url);
  if (stockRoute) return stockRoute;
  return { status: 404, body: { ok: false, error: "Not found" } };
}

function sendJson(res, status, body) {
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "http://127.0.0.1:4173",
    "cache-control": "no-store"
  });
  res.end(JSON.stringify(body));
}

const isDirectRun = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isDirectRun) {
  const server = createServer();
  server.listen(env.port, env.host, () => {
    console.log(`stock-analyzer-backend listening on http://${env.host}:${env.port}`);
    console.log("mock mode: external APIs are disabled");
  });
}
