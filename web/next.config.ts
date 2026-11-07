import type { NextConfig } from "next";

// The FastAPI backend (uvicorn server:app --port 8000). The browser only talks to Next,
// which proxies /api/* there, so there are no CORS issues and no backend URL in the client.
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
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
