# PBNH Editor

CodeMirror 6 changed the old "drop-in `<script>` tag" model to many small,
composable npm packages meant to be assembled by consumers and run through a
bundler. This directory exists to do that.

- `src/` contains original integration code.
- `package(-lock).json` lists the npm dependencies to bundle.
  - Note: `@babel/runtime` is listed as a direct dependency even though nothing
    in `src/` uses it. It's there because `@uiw/codemirror-theme-monokai` imports
    from it but doesn't declare it as a dependency of its own package correctly:
    https://github.com/uiwjs/react-codemirror/issues/755
- `build.sh` bundles everything into `dist/`
  (which is copied into `pbnh/static/` during the Docker build).

To build the editor locally:

```sh
npm install
npm run build
```
