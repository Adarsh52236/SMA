import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  async redirects() {
    return [
      {
        source: "/predict",
        destination: "/",
        permanent: false,
      },
      {
        source: "/discovery",
        destination: "/",
        permanent: false,
      },
      {
        source: "/insights",
        destination: "/",
        permanent: false,
      },
      {
        source: "/methodology",
        destination: "/",
        permanent: false,
      },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
