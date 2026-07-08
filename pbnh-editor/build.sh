#!/usr/bin/env sh
set -o errexit
here="$(cd "$(dirname "$0")" && pwd)"
set -o xtrace
outdir="$here/dist"
rm -rf "$outdir"
npx esbuild "$here/src/pbnh-editor.js" \
    --format=esm --bundle --minify --outdir="$outdir" \
    --splitting --chunk-names='chunks/[name]-[hash]'
