import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Requests to /api and /health are forwarded to the FastAPI backend, so the
// frontend can use plain relative URLs and there are no CORS problems.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
