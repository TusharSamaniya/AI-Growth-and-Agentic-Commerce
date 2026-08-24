import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev server + React support. Serves the app on http://localhost:5173.
export default defineConfig({
  plugins: [react()],
});
