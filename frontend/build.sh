#!/usr/bin/env sh
set -o errexit
here="$(cd "$(dirname "$0")" && pwd)"
set -o xtrace
outdir="$here/dist"
rm -rf "$outdir"
npx esbuild "$here/src/pbnh-editor.js" \
    --format=esm --bundle --minify --outdir="$outdir" \
    --splitting --chunk-names='pbnh-editor-chunks/[name]-[hash]'

node_modules="$here/node_modules"

# asciinema-player (Asciicast rendring)
cp "$node_modules/asciinema-player/dist/bundle/asciinema-player.min.js" "$outdir/asciinema-player.min.js"
cp "$node_modules/asciinema-player/dist/bundle/asciinema-player.css" "$outdir/asciinema-player.css"

# Lucide (static SVGs)
mkdir -p "$outdir/lucide/icons"
for icon in loader file-exclamation-point circle-help file-plus external-link save; do
  cp "$node_modules/lucide-static/icons/$icon.svg" "$outdir/lucide/icons/$icon.svg"
done
