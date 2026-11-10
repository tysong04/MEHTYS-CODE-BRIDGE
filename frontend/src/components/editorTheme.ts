import { EditorView } from '@codemirror/view';
import { Extension } from '@codemirror/state';
import { oneDark } from '@codemirror/theme-one-dark';

export const mtcbEditorTheme: Extension = EditorView.theme(
  {
    '&': {
      backgroundColor: '#0b0d13 !important',
      color: '#e6edf3',
      fontSize: '13.5px',
      fontFamily: "var(--font-mono)",
      height: '100%',
    },
    '.cm-scroller': {
      overflow: 'auto',
      fontFamily: "var(--font-mono)",
    },
    '.cm-content': {
      caretColor: '#38bdf8',
      padding: '12px 4px',
      lineHeight: '1.65',
    },
    '&.cm-focused .cm-cursor': {
      borderLeftColor: '#38bdf8',
      borderLeftWidth: '2px',
    },
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
      backgroundColor: 'rgba(56, 189, 248, 0.2) !important',
    },
    '.cm-gutters': {
      backgroundColor: '#090b10',
      color: '#49566d',
      borderRight: '1px solid #1c2232',
      userSelect: 'none',
    },
    '.cm-activeLineGutter': {
      backgroundColor: 'transparent',
      color: '#909fb5',
    },
    '.cm-activeLine': {
      backgroundColor: 'rgba(255, 255, 255, 0.025)',
    },
    '.cm-lineNumbers .cm-gutterElement': {
      minWidth: '38px',
      textAlign: 'right',
      paddingRight: '12px',
      fontSize: '12px',
    },
    '.cm-placeholder': {
      color: '#49566d',
      fontStyle: 'normal',
    },
  },
  { dark: true }
);

export const getEditorExtensions = (language: 'python' | 'javascript', pythonExt: Extension, jsExt: Extension): Extension[] => {
  const langExtension = language === 'python' ? pythonExt : jsExt;
  return [oneDark, mtcbEditorTheme, langExtension];
};
