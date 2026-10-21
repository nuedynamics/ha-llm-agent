import { defineConfig } from "vite";

// One self-contained ES module, served by the integration from www/.
export default defineConfig({
  build: {
    outDir: "../custom_components/llm_agent/www",
    emptyOutDir: false, // www/i18n holds the translations
    target: "es2022",
    sourcemap: false,
    lib: {
      entry: "src/panel.ts",
      formats: ["es"],
      fileName: () => "llm-agent-panel.js",
    },
  },
});
