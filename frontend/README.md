# pbnh Front-End

pbnh makes use of libraries from NPM for various front-end functionality.

Some libraries (e.g. `marked`, `dompurify`, etc.) come pre-built
and can just be installed and copied into place.

- Note: This is done instead of fetching from a CDN at request time to
  keep the project completely self-contained (e.g. for airgapped deployments)
  while still letting `npm` manage locking/updates like any other dependency.

Other dependencies, such as pbnh's CodeMirror-based editor, must be built
and bundled using custom integration code.

## Layout

- `package(-lock).json` lists NPM dependencies.

  - Note: `@babel/runtime` is listed even though nothing uses it directly.
    It's there because `@uiw/codemirror-theme-monokai` imports from it
    but doesn't declare it as a dependency of its own package correctly:
    https://github.com/uiwjs/react-codemirror/issues/755

- `src/` contains original integration code for bundling.

- `build.sh` bundles the editor and copies the vendored libraries into
  `dist/` (which is copied into `pbnh/static/dist/` during the Docker build).

## Building

Use `npm` to build:

```sh
npm install
npm run build
```

Dependencies can also be updated using `npm` as usual
(e.g. `npm install marked@latest`).
