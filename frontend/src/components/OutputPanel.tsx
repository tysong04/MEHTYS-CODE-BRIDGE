import React, { useState, useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { Copy, Check, Download, Code2, Loader2, Sparkles, Terminal } from 'lucide-react';
import { Language, ProviderInfo } from '../types/translation';
import { getEditorExtensions } from './editorTheme';

interface OutputPanelProps {
  translatedCode: string;
  targetLang: Language;
  providerInfo?: ProviderInfo;
  isTranslating: boolean;
  isStale?: boolean;
}

export const OutputPanel: React.FC<OutputPanelProps> = ({
  translatedCode,
  targetLang,
  providerInfo,
  isTranslating,
  isStale = false,
}) => {
  const [copied, setCopied] = useState(false);

  const extensions = useMemo(() => {
    return getEditorExtensions(targetLang, python(), javascript({ jsx: true, typescript: true }));
  }, [targetLang]);

  const lineCount = useMemo(() => (translatedCode ? translatedCode.split('\n').length : 0), [translatedCode]);
  const byteCount = useMemo(() => new Blob([translatedCode]).size, [translatedCode]);

  const handleCopy = async () => {
    if (!translatedCode) return;
    try {
      await navigator.clipboard.writeText(translatedCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textArea = document.createElement('textarea');
      textArea.value = translatedCode;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!translatedCode) return;
    const extension = targetLang === 'python' ? '.py' : '.js';
    const filename = `mtcb_translation${extension}`;
    const blob = new Blob([translatedCode], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="editor-workspace-card output-card">
      {/* Output Header */}
      <div className="editor-card-header">
        <div className="editor-header-meta">
          <Code2 size={15} className="editor-icon accent-violet" />
          <span className="editor-title">Output</span>
          <span className="editor-lang-badge violet">
            {targetLang === 'python' ? 'Python' : 'JavaScript'}
          </span>
          {isStale && translatedCode && !isTranslating && (
            <span className="stale-badge" title="Source code was edited after this translation was generated">
              Modified
            </span>
          )}
        </div>

        <div className="editor-actions">
          {translatedCode && (
            <>
              <button
                type="button"
                className={`btn-panel-action ${copied ? 'success' : ''}`}
                onClick={handleCopy}
                title="Copy translated code to clipboard"
                aria-label="Copy translated code"
              >
                {copied ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                type="button"
                className="btn-panel-action"
                onClick={handleDownload}
                title={`Download as ${targetLang === 'python' ? '.py' : '.js'} file`}
                aria-label="Download translated code"
              >
                <Download size={13} />
                <span>Export</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Surface Area */}
      <div className="editor-surface">
        {isTranslating ? (
          <div className="output-state-container loading">
            <div className="loading-orbit">
              <Loader2 size={32} className="spinner" />
            </div>
            <p className="state-headline">Translating Code</p>
            <p className="state-sub">Processing via local AI model...</p>
          </div>
        ) : translatedCode ? (
          <CodeMirror
            value={translatedCode}
            height="100%"
            extensions={extensions}
            readOnly={true}
            editable={false}
            basicSetup={{
              lineNumbers: true,
              highlightActiveLineGutter: false,
              foldGutter: true,
              syntaxHighlighting: true,
              bracketMatching: true,
            }}
          />
        ) : (
          <div className="output-state-container empty">
            <div className="empty-icon-box">
              <Terminal size={26} />
            </div>
            <p className="state-headline">Ready for Translation</p>
            <p className="state-sub">
              Paste code on the left and click <strong>Translate Code</strong> or press <kbd>Ctrl</kbd>+<kbd>Enter</kbd>.
            </p>
          </div>
        )}
      </div>

      {/* Output Footer */}
      <div className="editor-card-footer">
        <div className="editor-footer-left">
          {providerInfo ? (
            <span className="provider-pill">
              <Sparkles size={11} className="pill-sparkle" />
              <span>{providerInfo.provider}</span>
              <span className="pill-dot">&bull;</span>
              <span>{providerInfo.model}</span>
              {providerInfo.execution_time_ms && (
                <>
                  <span className="pill-dot">&bull;</span>
                  <span>{Math.round(providerInfo.execution_time_ms)}ms</span>
                </>
              )}
            </span>
          ) : (
            <span className="status-muted">Awaiting translation</span>
          )}
        </div>

        <div className="editor-footer-right">
          {translatedCode && (
            <span className="status-metric">
              {lineCount} {lineCount === 1 ? 'line' : 'lines'} &bull; {byteCount.toLocaleString()} bytes
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
