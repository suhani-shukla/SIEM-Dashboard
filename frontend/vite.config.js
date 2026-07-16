// FILE LOCATION: frontend/vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev mode, proxy /api to the api container so the browser can call
// relative /api/... paths exactly like it will in production behind nginx.
// This means VITE_API_BASE_URL can default to "/api" in both environments.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_API_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, "/api"),
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
  },
});
