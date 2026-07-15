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

# Font Awesome (icon font used via `fa fa-*` classes in templates)
mkdir -p "$outdir/font-awesome"
cp -r "$node_modules/font-awesome/css" "$outdir/font-awesome/css"
cp -r "$node_modules/font-awesome/fonts" "$outdir/font-awesome/fonts"
