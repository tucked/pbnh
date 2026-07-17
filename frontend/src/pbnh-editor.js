import { basicSetup, EditorView } from "codemirror";
import { EditorState, Compartment } from "@codemirror/state";
import { LanguageDescription } from "@codemirror/language";
import { languages } from "@codemirror/language-data";
import { monokai } from "@uiw/codemirror-theme-monokai";

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
 * Text editor used by pbnh.
 */
export class PbnhEditor {
  #languageCompartment = new Compartment();
  #view;

  constructor({ parent, url, onKeyDown, onLoad } = {}) {
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

    // Make `view` private to keep CodeMirror as an implementation detail.
    this.#view = new EditorView({
      parent,
      doc,
      extensions: [
        basicSetup,
        monokai,
        EditorView.domEventHandlers({
          keydown: (event, view) => {
            onKeyDown?.(event);
            return false;
          },
        }),
        this.#languageCompartment.of([]),
        EditorState.readOnly.of(!!url),
        EditorView.theme({ "&": { height: "100%" } }),
      ],
    });

    if (onLoad) onLoad();

    if (filename || mime) {
      const description = findLanguage(filename, mime);
      if (description) {
        console.log(description.name);
        description
          .load()
          .then((support) => {
            this.#view.dispatch({
              effects: this.#languageCompartment.reconfigure(support),
            });
          })
          .catch((err) => {
            console.warn("could not load the language support for", description.name, err);
          });
      } else {
        console.warn("could not find the right highlighter");
      }
    }
  }

  /**
   * Get the current document content.
   * @returns {string} The document content.
   */
  getValue() {
    return this.#view.state.doc.toString();
  }

  /**
   * Focus the editor.
   */
  focus() {
    this.#view.focus();
  }
}
