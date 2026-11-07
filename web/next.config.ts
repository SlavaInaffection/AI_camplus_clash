import path from "node:path";
import type { NextConfig } from "next";

// The FastAPI backend (uvicorn server:app --port 8000). The browser only talks to Next,
// which proxies /api/* there, so there are no CORS issues and no backend URL in the client.
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // the repo root also has a package-lock.json; pin the app root to web/
  turbopack: { root: path.join(__dirname) },
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    // the report call runs several agents and can take ~30 s
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};

export default nextConfig;
