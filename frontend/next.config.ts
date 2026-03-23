import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
      {
        source: "/pdfs/:path*",
        destination: `${BACKEND_URL}/pdfs/:path*`,
      },
    ];
  },
};

export default nextConfig;
