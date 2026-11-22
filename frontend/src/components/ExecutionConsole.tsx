import React, { useState } from 'react';
import { Play, PlayCircle, Terminal, CheckCircle2, XCircle, Clock, Shield, AlertTriangle, ArrowRightLeft, Loader2 } from 'lucide-react';
import { Language, ExecutionResult } from '../types/translation';
import { executeJavaScript, executePython } from '../services/execution';

interface ExecutionConsoleProps {
  originalCode: string;
  translatedCode: string;
  sourceLang: Language;
  targetLang: Language;
  onVerificationUpdate?: (verified: boolean, label: string) => void;
}

export const ExecutionConsole: React.FC<ExecutionConsoleProps> = ({
  originalCode,
  translatedCode,
  sourceLang,
  targetLang,
  onVerificationUpdate,
}) => {
  const [activeTab, setActiveTab] = useState<'original' | 'translated' | 'compare'>('compare');
  const [stdinInput, setStdinInput] = useState<string>('');

  const [origResult, setOrigResult] = useState<ExecutionResult | null>(null);
  const [transResult, setTransResult] = useState<ExecutionResult | null>(null);
  const [isRunningOrig, setIsRunningOrig] = useState<boolean>(false);
  const [isRunningTrans, setIsRunningTrans] = useState<boolean>(false);
  const [lastRunTime, setLastRunTime] = useState<string | null>(null);

  const runCodeSnippet = async (code: string, lang: Language): Promise<ExecutionResult> => {
    if (lang === 'javascript') {
      return await executeJavaScript(code, stdinInput);
    } else {
      return await executePython(code, stdinInput);
    }
  };

  const handleRunOriginal = async () => {
    if (!originalCode.trim()) return;
    setIsRunningOrig(true);
    try {
      const res = await runCodeSnippet(originalCode, sourceLang);
      setOrigResult(res);
      setLastRunTime(new Date().toLocaleTimeString());
      checkMatch(res, transResult);
    } finally {
      setIsRunningOrig(false);
    }
  };

  const handleRunTranslated = async () => {
    if (!translatedCode.trim()) return;
    setIsRunningTrans(true);
    try {
      const res = await runCodeSnippet(translatedCode, targetLang);
      setTransResult(res);
      setLastRunTime(new Date().toLocaleTimeString());
      checkMatch(origResult, res);
    } finally {
      setIsRunningTrans(false);
    }
  };

  const handleRunBothAndCompare = async () => {
    if (!originalCode.trim() || !translatedCode.trim()) return;
    setIsRunningOrig(true);
    setIsRunningTrans(true);
    try {
      const [orig, trans] = await Promise.all([
        runCodeSnippet(originalCode, sourceLang),
        runCodeSnippet(translatedCode, targetLang),
      ]);
      setOrigResult(orig);
      setTransResult(trans);
      setLastRunTime(new Date().toLocaleTimeString());
      checkMatch(orig, trans);
    } finally {
      setIsRunningOrig(false);
      setIsRunningTrans(false);
    }
  };

  const checkMatch = (orig: ExecutionResult | null, trans: ExecutionResult | null) => {
    if (!orig || !trans || !onVerificationUpdate) return;

    if (!orig.success || !trans.success) {
      onVerificationUpdate(false, 'Execution error');
      return;
    }

    const origTrim = orig.stdout.trim();
    const transTrim = trans.stdout.trim();

    if (origTrim === transTrim) {
      onVerificationUpdate(true, '100% Verified (Outputs match)');
    } else {
      onVerificationUpdate(false, 'Output mismatch detected');
    }
  };

  const isOutputsMatching =
    origResult &&
    transResult &&
    origResult.success &&
    transResult.success &&
    origResult.stdout.trim() === transResult.stdout.trim();

  const isOutputsMismatch =
    origResult &&
    transResult &&
    origResult.success &&
    transResult.success &&
    origResult.stdout.trim() !== transResult.stdout.trim();

  return (
    <section className="execution-console-container" aria-label="Code Execution and Testing Environment">
      {/* Console Header */}
      <div className="console-header">
        <div className="console-title-group">
          <Terminal size={16} className="accent-teal" />
          <h3 className="console-title">Code Execution &amp; Behavioral Testing</h3>
          <span className="sandbox-security-pill">
            <Shield size={11} color="#10b981" />
            <span>Isolated Sandbox • 3s Timeout</span>
          </span>
        </div>

        {/* Console Action Buttons */}
        <div className="console-actions">
          <button
            type="button"
            className="btn-console-run secondary"
            onClick={handleRunOriginal}
            disabled={isRunningOrig || isRunningTrans || !originalCode.trim()}
            title={`Run original ${sourceLang} code`}
          >
            {isRunningOrig ? <Loader2 size={13} className="spinner" /> : <Play size={13} />}
            <span>Run Original ({sourceLang})</span>
          </button>

          <button
            type="button"
            className="btn-console-run secondary"
            onClick={handleRunTranslated}
            disabled={isRunningOrig || isRunningTrans || !translatedCode.trim()}
            title={`Run translated ${targetLang} code`}
          >
            {isRunningTrans ? <Loader2 size={13} className="spinner" /> : <Play size={13} />}
            <span>Run Translated ({targetLang})</span>
          </button>

          <button
            type="button"
            className="btn-console-run primary"
            onClick={handleRunBothAndCompare}
            disabled={isRunningOrig || isRunningTrans || !originalCode.trim() || !translatedCode.trim()}
            title="Execute both programs under identical input and compare outputs"
          >
            {isRunningOrig || isRunningTrans ? (
              <Loader2 size={14} className="spinner" />
            ) : (
              <PlayCircle size={14} />
            )}
            <span>Run Both &amp; Compare</span>
          </button>
        </div>
      </div>

      {/* Stdin Input Bar */}
      <div className="console-stdin-bar">
        <span className="stdin-label">Standard Input (stdin):</span>
        <input
          type="text"
          className="stdin-input"
          placeholder="Provide optional input (e.g. 5, or line-separated text) to pass to input() / readline()"
          value={stdinInput}
          onChange={(e) => setStdinInput(e.target.value)}
        />
      </div>

      {/* Comparison Match Status Banner */}
      {origResult && transResult && (
        <div className={`comparison-banner ${isOutputsMatching ? 'match' : isOutputsMismatch ? 'mismatch' : 'error'}`}>
          <div className="banner-status-icon">
            {isOutputsMatching ? (
              <CheckCircle2 size={16} color="#10b981" />
            ) : isOutputsMismatch ? (
              <XCircle size={16} color="#ef4444" />
            ) : (
              <AlertTriangle size={16} color="#f59e0b" />
            )}
          </div>
          <div className="banner-status-text">
            <strong>
              {isOutputsMatching
                ? 'Behavioral Verification Passed: Outputs Match Identically'
                : isOutputsMismatch
                ? 'Behavioral Divergence Detected: Outputs Differ'
                : 'Execution Error in One or Both Programs'}
            </strong>
            <p>
              {isOutputsMatching
                ? 'Both the original and translated snippets executed under the supplied input and generated matching standard output.'
                : isOutputsMismatch
                ? 'The original and translated code produced different outputs. Inspect the comparison outputs below.'
                : 'Check stderr logs below for runtime or syntax errors.'}
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="console-tab-bar" role="tablist">
        <button
          type="button"
          className={`console-tab ${activeTab === 'compare' ? 'active' : ''}`}
          onClick={() => setActiveTab('compare')}
          role="tab"
          aria-selected={activeTab === 'compare'}
        >
          <ArrowRightLeft size={13} />
          <span>Output Comparison</span>
        </button>
        <button
          type="button"
          className={`console-tab ${activeTab === 'original' ? 'active' : ''}`}
          onClick={() => setActiveTab('original')}
          role="tab"
          aria-selected={activeTab === 'original'}
        >
          <span>Original Output ({sourceLang})</span>
          {origResult && (
            <span className={`tab-indicator ${origResult.success ? 'success' : 'fail'}`} />
          )}
        </button>
        <button
          type="button"
          className={`console-tab ${activeTab === 'translated' ? 'active' : ''}`}
          onClick={() => setActiveTab('translated')}
          role="tab"
          aria-selected={activeTab === 'translated'}
        >
          <span>Translated Output ({targetLang})</span>
          {transResult && (
            <span className={`tab-indicator ${transResult.success ? 'success' : 'fail'}`} />
          )}
        </button>
      </div>

      {/* Console Surface Panels */}
      <div className="console-surface">
        {activeTab === 'compare' ? (
          /* Side-by-Side Comparison */
          <div className="console-comparison-grid">
            {/* Original Output Card */}
            <div className="console-output-card">
              <div className="output-card-header">
                <span className="output-pane-title">Original ({sourceLang})</span>
                {origResult && (
                  <span className="output-meta-tag">
                    <Clock size={11} /> {origResult.execution_time_ms}ms
                  </span>
                )}
              </div>
              <pre className="terminal-screen">
                <code>
                  {origResult ? (
                    origResult.stdout || origResult.stderr || '[Process terminated with no output]'
                  ) : (
                    <span className="terminal-placeholder">Awaiting original execution. Click "Run Both &amp; Compare" above.</span>
                  )}
                </code>
              </pre>
            </div>

            {/* Translated Output Card */}
            <div className="console-output-card">
              <div className="output-card-header">
                <span className="output-pane-title">Translated ({targetLang})</span>
                {transResult && (
                  <span className="output-meta-tag">
                    <Clock size={11} /> {transResult.execution_time_ms}ms
                  </span>
                )}
              </div>
              <pre className="terminal-screen">
                <code>
                  {transResult ? (
                    transResult.stdout || transResult.stderr || '[Process terminated with no output]'
                  ) : (
                    <span className="terminal-placeholder">Awaiting translated execution. Click "Run Both &amp; Compare" above.</span>
                  )}
                </code>
              </pre>
            </div>
          </div>
        ) : activeTab === 'original' ? (
          /* Detailed Original View */
          <div className="console-single-pane">
            <div className="single-pane-meta">
              <span className="meta-badge">Language: {sourceLang}</span>
              {origResult && (
                <>
                  <span className={`meta-badge ${origResult.success ? 'badge-success' : 'badge-danger'}`}>
                    Status: {origResult.status}
                  </span>
                  <span className="meta-badge">Time: {origResult.execution_time_ms}ms</span>
                </>
              )}
            </div>
            <pre className="terminal-screen full">
              <code>
                {origResult ? (
                  origResult.stdout ? (
                    origResult.stdout
                  ) : origResult.stderr ? (
                    <span className="terminal-stderr">{origResult.stderr}</span>
                  ) : (
                    '[Completed with no output]'
                  )
                ) : (
                  <span className="terminal-placeholder">Click "Run Original" to execute code.</span>
                )}
              </code>
            </pre>
            {origResult?.stderr && origResult.stdout && (
              <div className="stderr-drawer">
                <span className="stderr-title">Standard Error Logs:</span>
                <pre className="stderr-screen">{origResult.stderr}</pre>
              </div>
            )}
          </div>
        ) : (
          /* Detailed Translated View */
          <div className="console-single-pane">
            <div className="single-pane-meta">
              <span className="meta-badge">Language: {targetLang}</span>
              {transResult && (
                <>
                  <span className={`meta-badge ${transResult.success ? 'badge-success' : 'badge-danger'}`}>
                    Status: {transResult.status}
                  </span>
                  <span className="meta-badge">Time: {transResult.execution_time_ms}ms</span>
                </>
              )}
            </div>
            <pre className="terminal-screen full">
              <code>
                {transResult ? (
                  transResult.stdout ? (
                    transResult.stdout
                  ) : transResult.stderr ? (
                    <span className="terminal-stderr">{transResult.stderr}</span>
                  ) : (
                    '[Completed with no output]'
                  )
                ) : (
                  <span className="terminal-placeholder">Click "Run Translated" to execute code.</span>
                )}
              </code>
            </pre>
            {transResult?.stderr && transResult.stdout && (
              <div className="stderr-drawer">
                <span className="stderr-title">Standard Error Logs:</span>
                <pre className="stderr-screen">{transResult.stderr}</pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Console Security Footer */}
      <div className="console-footer">
        <span className="security-notice">
          Safety Notice: Code runs in strict sandboxed memory with zero network access and 3.0s termination timeout. Server credentials are never exposed.
        </span>
        {lastRunTime && <span className="last-run-timestamp">Last tested at {lastRunTime}</span>}
      </div>
    </section>
  );
};
