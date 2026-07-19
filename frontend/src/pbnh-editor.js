import { basicSetup, EditorView } from "codemirror";
import { EditorState, Compartment } from "@codemirror/state";
import { LanguageDescription } from "@codemirror/language";
import { languages } from "@codemirror/language-data";
import { monokai } from "@uiw/codemirror-theme-monokai";

function findLanguage(filename, mime) {
  if (filename) {
    const byFilename = LanguageDescription.matchFilename(languages, filename);
    if (byFilename) return byFilename;
  }
  if (mime) {
    const name = mime
      .split("/")
      .pop()
      .replace(/^(x-|vnd\.)/i, "")
      .split(/[+\.]/)
      .pop()
      .trim();
    const byMime = LanguageDescription.matchLanguageName(languages, name, true);
    if (byMime) return byMime;
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
        this.#languageCompartment.of([]),
        EditorState.readOnly.of(!!url),
        EditorView.theme({ "&": { height: "100%" } }),
        EditorView.domEventHandlers({
          keydown: (event, view) => {
            onKeyDown?.(event);
            return false;
          },
        }),
      ],
    });

    if (onLoad) onLoad();

    if (filename || mime) {
      const description = findLanguage(filename, mime);
      if (description) {
        console.info(`Language: ${description.name}`);
        description
          .load()
          .then((support) => {
            this.#view.dispatch({
              effects: this.#languageCompartment.reconfigure(support),
            });
          })
          .catch((err) => {
            console.error(`Loading the ${description.name} highlighter failed!`, err);
          });
      } else {
        let target = filename || mime;
        if (filename && mime) target += " (" + mime + ")";
        console.warn(`An appropriate highlighter for ${target} could not be found.`);
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
