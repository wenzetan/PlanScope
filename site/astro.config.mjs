import { defineConfig } from "astro/config";

// GitHub Pages project-site path: /<repository-name>/
// CI sets PLANSCOPE_BASE (e.g. "/planscope/", or "/" for a *.github.io repo).
// The hostname is never hardcoded here.
export default defineConfig({
  base: process.env.PLANSCOPE_BASE || "/planscope/",
  output: "static",
  trailingSlash: "always",
});
