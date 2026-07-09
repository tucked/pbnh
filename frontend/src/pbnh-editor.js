import { basicSetup, EditorView } from "codemirror";
import { EditorState, Compartment } from "@codemirror/state";
import { keymap } from "@codemirror/view";
import { LanguageDescription } from "@codemirror/language";
import { languages } from "@codemirror/language-data";
import { monokai } from "@uiw/codemirror-theme-monokai";

const languageCompartment = new Compartment();

function findLanguage(filename, mime) {
  if (filename) {
    const byExtension = LanguageDescription.matchFilename(languages, filename);
    if (byExtension) return byExtension;
  }
  if (mime) {
    const subtype = mime.split("/").pop().replace(/^(x-|vnd\.)/, "");
    const byMime = LanguageDescription.matchLanguageName(languages, subtype, true);
    if (byMime) {
      return byMime;
    }
  }
  return null;
}

/**
 * Create a CodeMirror 6 editor and mount it under `parent`.
 *
 * Returns a small wrapper object exposing the handful of CodeMirror 5
 * APIs that the surrounding templates rely on (getValue),
 * plus the raw EditorView as `view` for anything more advanced.
 */
export function createEditor({
  parent,
  url = "",
  onSave,
} = {}) {
  const extraKeys = [];
  if (onSave) {
    extraKeys.push({
      key: "Ctrl-s",
      mac: "Cmd-s",
      preventDefault: true,
      run: () => {
        onSave();
        return true;
      },
    });
  }
  let doc = "";
  let mime = "";
  let filename = "";
  if (url) {
    const xmlhttp = new XMLHttpRequest();
    xmlhttp.open("GET", url, false);
    xmlhttp.send();
    doc = xmlhttp.responseText;
    mime = (xmlhttp.getResponseHeader("Content-Type") || "").split(";")[0].trim();
    filename = new URL(url, window.location.href).pathname;
  }

  const view = new EditorView({
    parent,
    doc,
    extensions: [
      basicSetup,
      monokai,
      keymap.of(extraKeys),
      languageCompartment.of([]),
      EditorState.readOnly.of(!!url),
      EditorView.theme({ "&": { height: "100%" } }),
    ],
  });

  if (filename || mime) {
    const description = findLanguage(filename, mime);
    if (description) {
      console.log(description.name);
      description
        .load()
        .then((support) => {
          view.dispatch({
            effects: languageCompartment.reconfigure(support),
          });
        })
        .catch((err) => {
          console.warn("could not load the language support for", description.name, err);
        });
    } else {
      console.warn("could not find the right highlighter");
    }
  }

  return {
    view,
    getValue: () => view.state.doc.toString(),
    focus: () => view.focus(),
  };
}
