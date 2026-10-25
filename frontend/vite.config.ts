import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// AWARE_RECEIVER points the companion at a receiver elsewhere (another port or the inference Mac).
const proxy = {
  "/pi-audio": {
    target: process.env.AWARE_PI_LEVELS ?? "http://127.0.0.1:8768",
    rewrite: (path: string) => path.replace(/^\/pi-audio/, ""),
  },
  "/api": {
    target: process.env.AWARE_RECEIVER ?? "http://127.0.0.1:8765",
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};
export default defineConfig({
  // AWARE_BASE is the site's path when hosted, e.g. /calhacks2026/ on GitHub Pages.
  base: process.env.AWARE_BASE ?? "/",
  plugins: [react()],
  server: { strictPort: true, proxy },
  preview: { proxy },
});
