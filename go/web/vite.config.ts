import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// Build output lands in the Go webui package so it can be embedded.
// Dev server proxies /api (and /docs, /openapi.json) to the running leil-api;
// the target is overridable via LEIL_API_URL (used by the dev compose service).
const apiTarget = process.env.LEIL_API_URL || "http://localhost:8001";

export default defineConfig({
  plugins: [preact()],
  build: {
    outDir: "../internal/webui/dist",
    emptyOutDir: true,
  },
  server: {
    host: true,
    proxy: {
      "/api": apiTarget,
      "/docs": apiTarget,
      "/openapi.json": apiTarget,
    },
  },
});
