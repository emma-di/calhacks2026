import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// AWARE_RECEIVER points the companion at a receiver elsewhere (another port or the inference Mac).
const proxy = {
  "/api": {
    target: process.env.AWARE_RECEIVER ?? "http://127.0.0.1:8765",
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};
export default defineConfig({
  plugins: [react()],
  server: { strictPort: true, proxy },
  preview: { proxy },
});
