import { basicSetup, EditorView } from "codemirror";
import { EditorState, Compartment } from "@codemirror/state";
import { keymap } from "@codemirror/view";
import { LanguageDescription } from "@codemirror/language";
import { languages } from "@codemirror/language-data";
import { monokai } from "@uiw/codemirror-theme-monokai";

const languageCompartment = new Compartment();
const readOnlyCompartment = new Compartment();

function findLanguage(extension, mime) {
  if (extension) {
    const byExtension = LanguageDescription.matchFilename(
      languages,
      `paste.${extension}`
    );
    if (byExtension) {
      return byExtension;
    }
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
 * APIs that the surrounding templates rely on (getValue/setReadOnly),
 * plus the raw EditorView as `view` for anything more advanced.
 */
export function createEditor({
  parent,
  doc = "",
  extension = "",
  mime = "",
  readOnly = false,
  onSave,
  onNew,
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
  if (onNew) {
    extraKeys.push({
      key: "Ctrl-n",
      mac: "Cmd-n",
      preventDefault: true,
      run: () => {
        onNew();
        return true;
      },
    });
  }

  const view = new EditorView({
    parent,
    doc,
    extensions: [
      basicSetup,
      monokai,
      keymap.of(extraKeys),
      languageCompartment.of([]),
      readOnlyCompartment.of(EditorState.readOnly.of(readOnly)),
      EditorView.theme({ "&": { height: "100%" } }),
    ],
  });

  const description = findLanguage(extension, mime);
  if (description) {
    console.log(description.name);
    description
      .load()
      .then((support) => {
        view.dispatch({ effects: languageCompartment.reconfigure(support) });
      })
      .catch((err) => {
        console.warn("could not load the language support for", description.name, err);
      });
  } else {
    console.warn("could not find the right highlighter");
  }

  return {
    view,
    getValue: () => view.state.doc.toString(),
    setReadOnly: (value) =>
      view.dispatch({
        effects: readOnlyCompartment.reconfigure(EditorState.readOnly.of(!!value)),
      }),
    focus: () => view.focus(),
  };
}
