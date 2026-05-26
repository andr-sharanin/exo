import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        // Proxy API calls to FastAPI backend — avoids CORS in browser
        source: "/api/backend/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
