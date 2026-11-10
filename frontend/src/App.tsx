import React, { useState, useEffect, useCallback } from 'react';
import { ArrowRight, RotateCcw, AlertTriangle, Terminal, Shield, Copy, Check, X, Sliders } from 'lucide-react';
import { Header } from './components/Header';
import { LanguageSelector } from './components/LanguageSelector';
import { InstructionsInput } from './components/InstructionsInput';
import { CodeEditor } from './components/CodeEditor';
import { OutputPanel } from './components/OutputPanel';
import { ExplanationCard } from './components/ExplanationCard';
import { ErrorBanner } from './components/ErrorBanner';
import { ProviderSettingsModal } from './components/ProviderSettingsModal';
import {
  Language,
  HealthResponse,
  ProviderStatusResponse,
  ProviderInfo,
  ApiError,
  ProviderConfig,
} from './types/translation';
import { checkHealth, getProviderStatus, translateCode, TranslationApiError } from './services/api';
import './App.css';

export const App: React.FC = () => {
  const [sourceLang, setSourceLang] = useState<Language>('python');
  const [targetLang, setTargetLang] = useState<Language>('javascript');
  const [code, setCode] = useState<string>('');
  const [filename, setFilename] = useState<string | null>(null);
  const [instructions, setInstructions] = useState<string>('');

  const [translatedCode, setTranslatedCode] = useState<string>('');
  const [explanation, setExplanation] = useState<string>('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [providerInfo, setProviderInfo] = useState<ProviderInfo | undefined>(undefined);
  const [isStale, setIsStale] = useState<boolean>(false);

  const [isTranslating, setIsTranslating] = useState<boolean>(false);
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [dismissedOfflineWarning, setDismissedOfflineWarning] = useState<boolean>(false);
  const [copiedOllamaCmds, setCopiedOllamaCmds] = useState<boolean>(false);

  // In-memory provider configuration (Never saved to localStorage or cookies)
  const [providerConfig, setProviderConfig] = useState<ProviderConfig>({
    provider: 'gemini',
    model: 'gemini-3.8-flash',
    consent_granted: false,
  });
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

  // Refresh backend and provider status
  const refreshStatus = useCallback(async () => {
    setIsLoadingStatus(true);
    setDismissedOfflineWarning(false);
    try {
      const [health, provider] = await Promise.allSettled([
        checkHealth(),
        getProviderStatus(),
      ]);

      if (health.status === 'fulfilled') {
        setBackendHealth(health.value);
      } else {
        setBackendHealth(null);
      }

      if (provider.status === 'fulfilled') {
        setProviderStatus(provider.value);
      } else {
        setProviderStatus(null);
      }
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  // Code change tracking
  const handleCodeChange = (newCode: string) => {
    setCode(newCode);
    if (error) setError(null);
    if (translatedCode) {
      setIsStale(true);
    }
  };

  // Swap source & target languages
  const handleSwapLanguages = () => {
    const nextSource = targetLang;
    const nextTarget = sourceLang;
    setSourceLang(nextSource);
    setTargetLang(nextTarget);

    // If output is present, promote output to new source for round-trip testing
    if (translatedCode) {
      setCode(translatedCode);
      setTranslatedCode('');
      setFilename(null);
      setExplanation('');
      setWarnings([]);
      setIsStale(false);
    }
  };

  // Reset workspace
  const handleClear = () => {
    setCode('');
    setFilename(null);
    setTranslatedCode('');
    setExplanation('');
    setWarnings([]);
    setError(null);
    setIsStale(false);
  };

  // File loaded via upload button or drag-and-drop
  const handleFileLoaded = (fileContent: string, name: string) => {
    setCode(fileContent);
    setFilename(name);
    setTranslatedCode('');
    setExplanation('');
    setWarnings([]);
    setError(null);
    setIsStale(false);
  };

  // Perform translation
  const handleTranslate = useCallback(async () => {
    if (!code || !code.trim()) {
      setError({
        message: 'Please provide code in the editor or upload a source file before translating.',
        error_type: 'Validation Warning',
      });
      return;
    }

    if (sourceLang === targetLang) {
      setError({
        message: 'Source and target languages must be different.',
        error_type: 'Configuration Warning',
      });
      return;
    }

    // Provider pre-validation
    if (providerConfig.provider === 'gemini') {
      if (!providerConfig.api_key || !providerConfig.api_key.trim()) {
        setError({
          message: 'Google Gemini API key is required. Please click "Configure Provider" to supply your key or switch to Mock/Ollama.',
          error_type: 'API Key Required',
        });
        setIsSettingsOpen(true);
        return;
      }

      if (!providerConfig.consent_granted) {
        setError({
          message: 'Explicit consent is required to transmit source code to Google Gemini APIs. Please open settings and accept the data consent checkbox.',
          error_type: 'Consent Required',
        });
        setIsSettingsOpen(true);
        return;
      }
    }

    setError(null);
    setIsTranslating(true);
    setTranslatedCode('');
    setExplanation('');
    setWarnings([]);
    setIsStale(false);

    try {
      const result = await translateCode({
        source_lang: sourceLang,
        target_lang: targetLang,
        code,
        instructions: instructions.trim() ? instructions.trim() : undefined,
        provider_config: providerConfig,
      });

      setTranslatedCode(result.translated_code);
      setExplanation(result.explanation);
      setWarnings(result.warnings || []);
      setProviderInfo(result.provider_info);
      setIsStale(false);
    } catch (err: unknown) {
      if (err instanceof TranslationApiError) {
        setError({
          message: err.message,
          setup_instructions: err.setup_instructions,
          error_type: err.error_type || 'Translation Error',
        });
      } else {
        setError({
          message: err instanceof Error ? err.message : 'An unexpected error occurred during translation.',
          error_type: 'Application Error',
        });
      }
    } finally {
      setIsTranslating(false);
    }
  }, [code, sourceLang, targetLang, instructions, providerConfig]);

  // Global Ctrl+Enter shortcut handler
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        if (!isTranslating && code.trim()) {
          handleTranslate();
        }
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [handleTranslate, isTranslating, code]);

  const copyOllamaInstructions = () => {
    if (providerStatus?.setup_instructions) {
      navigator.clipboard.writeText(providerStatus.setup_instructions);
      setCopiedOllamaCmds(true);
      setTimeout(() => setCopiedOllamaCmds(false), 2000);
    }
  };

  return (
    <div className="workspace-container">
      {/* Top Application Header */}
      <Header
        backendHealth={backendHealth}
        providerStatus={providerStatus}
        isLoadingStatus={isLoadingStatus}
        onRefreshStatus={refreshStatus}
        currentProviderConfig={providerConfig}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main Workspace Toolbar */}
      <section className="workspace-toolbar" aria-label="Translation Controls">
        <div className="toolbar-left">
          <LanguageSelector
            sourceLang={sourceLang}
            targetLang={targetLang}
            onSourceLangChange={(lang) => {
              setSourceLang(lang);
              if (lang === targetLang) {
                setTargetLang(lang === 'python' ? 'javascript' : 'python');
              }
            }}
            onTargetLangChange={(lang) => {
              setTargetLang(lang);
              if (lang === sourceLang) {
                setSourceLang(lang === 'python' ? 'javascript' : 'python');
              }
            }}
            onSwapLanguages={handleSwapLanguages}
            disabled={isTranslating}
          />
        </div>

        <div className="toolbar-center">
          <InstructionsInput
            value={instructions}
            onChange={setInstructions}
            disabled={isTranslating}
          />
        </div>

        <div className="toolbar-right">
          <button
            type="button"
            className="btn-toolbar-ghost"
            onClick={() => setIsSettingsOpen(true)}
            title="Configure AI Provider & API Keys"
            aria-label="Configure AI Provider"
          >
            <Sliders size={13} />
            <span>Provider</span>
          </button>

          <button
            type="button"
            className="btn-toolbar-ghost"
            onClick={handleClear}
            disabled={isTranslating || (!code && !translatedCode)}
            title="Reset workspace (clear code and output)"
            aria-label="Reset workspace"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          <button
            type="button"
            className={`btn-toolbar-primary ${isTranslating ? 'loading' : ''}`}
            onClick={handleTranslate}
            disabled={isTranslating || !code.trim()}
            title="Translate source code (Ctrl+Enter)"
            aria-label="Translate source code"
          >
            {isTranslating ? (
              <>
                <span className="btn-spinner"></span>
                <span>Translating...</span>
              </>
            ) : (
              <>
                <span>Translate</span>
                <ArrowRight size={14} />
                <span className="shortcut-badge">Ctrl ↵</span>
              </>
            )}
          </button>
        </div>
      </section>

      {/* System Error Banner */}
      <ErrorBanner error={error} onDismiss={() => setError(null)} />

      {/* Ollama Offline System Notice (ONLY shown when Ollama is the actively selected provider) */}
      {backendHealth && providerConfig.provider === 'ollama' && providerStatus && !providerStatus.available && !error && !dismissedOfflineWarning && (
        <aside className="system-callout-banner banner-warning" role="status">
          <div className="banner-top-row">
            <div className="banner-title-group">
              <AlertTriangle size={15} className="banner-leading-icon" />
              <span className="banner-title">
                Local AI Model Offline ({providerStatus.provider}: {providerStatus.model})
              </span>
            </div>
            <button
              onClick={() => setDismissedOfflineWarning(true)}
              className="btn-banner-close"
              title="Dismiss warning"
              aria-label="Dismiss warning"
            >
              <X size={14} />
            </button>
          </div>

          <p className="banner-message">{providerStatus.details}</p>

          {providerStatus.setup_instructions && (
            <div className="banner-setup-guide">
              <div className="setup-guide-header">
                <Terminal size={13} />
                <span>To enable local AI translation:</span>
                <button
                  type="button"
                  className="btn-copy-instructions"
                  onClick={copyOllamaInstructions}
                  title="Copy setup commands"
                >
                  {copiedOllamaCmds ? (
                    <Check size={11} color="var(--accent-emerald)" />
                  ) : (
                    <Copy size={11} />
                  )}
                  <span>{copiedOllamaCmds ? 'Copied' : 'Copy Commands'}</span>
                </button>
              </div>
              <pre className="banner-code-block">
                <code>{providerStatus.setup_instructions}</code>
              </pre>
            </div>
          )}
        </aside>
      )}

      {/* Split-Pane Translation Editors */}
      <main className="workspace-editor-grid">
        <CodeEditor
          code={code}
          onChange={handleCodeChange}
          onClear={() => {
            setCode('');
            setFilename(null);
            setIsStale(false);
          }}
          sourceLang={sourceLang}
          filename={filename}
          onFileLoaded={handleFileLoaded}
          onError={(msg) => setError({ message: msg, error_type: 'File Upload Error' })}
          onTranslateShortcut={handleTranslate}
          disabled={isTranslating}
        />

        <OutputPanel
          translatedCode={translatedCode}
          targetLang={targetLang}
          providerInfo={providerInfo}
          isTranslating={isTranslating}
          isStale={isStale}
        />
      </main>

      {/* Explanation, Idioms, Assumptions & Warnings */}
      <ExplanationCard explanation={explanation} warnings={warnings} />

      {/* Footer Strip */}
      <footer className="workspace-footer">
        <div className="footer-left">
          <Shield size={13} color="var(--accent-emerald)" />
          <span>
            {providerConfig.provider === 'gemini'
              ? 'Cloud Gemini translation • Secure memory transit • Untrusted code is never evaluated'
              : 'Local memory execution • Untrusted code is never evaluated • No external telemetry'}
          </span>
        </div>
        <div className="footer-right">
          <span>MTCB &bull; Developer Code Translation</span>
        </div>
      </footer>

      {/* Provider Configuration Modal */}
      <ProviderSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={providerConfig}
        onSaveConfig={(newConfig) => {
          setProviderConfig(newConfig);
          if (
            error?.error_type === 'API Key Required' ||
            error?.error_type === 'Consent Required'
          ) {
            setError(null);
          }
        }}
        onClearKey={() => {
          setProviderConfig((prev) => ({
            ...prev,
            api_key: undefined,
            consent_granted: false,
          }));
        }}
      />
    </div>
  );
};
