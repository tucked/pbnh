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

  constructor({ parent, url, onKeyDown } = {}) {
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

    if (filename || mime) this.setLanguage(filename, mime);
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

  /**
   * Set the language for the editor.
   * @param {string} filename - The filename to use for language detection.
   * @param {string} mime - The MIME type to use for language detection.
   */
  setLanguage(filename, mime) {
    if (!filename && !mime) return;
    const description = findLanguage(filename, mime);
    if (!description) {
      let target = filename || mime;
      if (filename && mime) target += " (" + mime + ")";
      console.warn(`An appropriate highlighter for ${target} could not be found.`);
      return;
    }
    console.info(`Language: ${description.name}`);
    description
      .load()
      .then((support) => {
        this.#view.dispatch({
          effects: this.#languageCompartment.reconfigure(support),
        });
      })
      .catch((err) => {
        console.error(`The ${description.name} highlighter failed to load!`, err);
      });
  }

  /**
   * Update the document content.
   * @param {string} doc - The new document content.
   */
  setValue(doc) {
    this.#view.dispatch({
      changes: {
        from: 0,
        to: this.#view.state.doc.length,
        insert: doc,
      },
    });
  }
}
