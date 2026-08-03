import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // PGlite ships a WASM binary + an .data file that must not be bundled/minified
  // into the serverless function graph by webpack. Mark it external so it is
  // required at runtime from node_modules (Vercel includes it via the trace).
  serverExternalPackages: ["@electric-sql/pglite"],
  // The baked claim-graph artifact is read via fs at runtime; force it into every
  // route's serverless bundle so Vercel ships it.
  outputFileTracingIncludes: {
    "/**/*": ["./data/claim-graph.json"],
  },
};

export default nextConfig;
