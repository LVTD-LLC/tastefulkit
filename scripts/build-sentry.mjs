import { build } from "esbuild";

export async function buildSentry() {
  await build({
    entryPoints: ["frontend/src/js/sentry.js"],
    bundle: true,
    outfile: "frontend/static/js/sentry.js",
    // Keep stack locations readable without uploading a private source archive.
    minify: false,
    sourcemap: false,
    format: "iife",
    target: ["es2020"],
  });
}
