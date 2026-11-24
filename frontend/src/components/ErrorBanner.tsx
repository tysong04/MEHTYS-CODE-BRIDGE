import React from 'react';
import { AlertCircle, Terminal, X, Copy, Check, ArrowRightLeft, Sliders, Shield } from 'lucide-react';
import { ApiError } from '../types/translation';

interface ErrorBannerProps {
  error: ApiError | null;
  onDismiss: () => void;
  onSwitchToMock?: () => void;
  onOpenSettings?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  error,
  onDismiss,
  onSwitchToMock,
  onOpenSettings,
}) => {
  const [copied, setCopied] = React.useState(false);

  if (!error) return null;

  const handleCopyInstructions = () => {
    if (!error.setup_instructions) return;
    navigator.clipboard.writeText(error.setup_instructions);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isBusy = error.error_type === 'ProviderBusy' || error.can_switch_provider;

  return (
    <div className={`system-callout-banner ${isBusy ? 'banner-warning' : 'banner-danger'}`} role="alert">
      <div className="banner-top-row">
        <div className="banner-title-group">
          <AlertCircle size={15} className="banner-leading-icon" />
          <span className="banner-title">{error.error_type || 'Translation Error'}</span>
        </div>
        <button
          onClick={onDismiss}
          className="btn-banner-close"
          title="Dismiss notification"
          aria-label="Dismiss notification"
        >
          <X size={14} />
        </button>
      </div>

      <p className="banner-message">{error.message}</p>

      {/* Explicit Provider Switch Options */}
      {isBusy && (
        <div className="banner-switch-options">
          <div className="banner-switch-header">
            <Shield size={13} color="var(--accent-emerald)" />
            <span>Your code and settings have been safely preserved.</span>
          </div>
          <div className="banner-actions-row">
            {onSwitchToMock && (
              <button
                type="button"
                className="btn-banner-action primary"
                onClick={onSwitchToMock}
                title="Explicitly switch to Mock translation provider"
              >
                <ArrowRightLeft size={13} />
                <span>Switch to Mock Provider (Offline)</span>
              </button>
            )}
            {onOpenSettings && (
              <button
                type="button"
                className="btn-banner-action secondary"
                onClick={onOpenSettings}
                title="Open Provider Settings to select another model or key"
              >
                <Sliders size={13} />
                <span>Configure Providers</span>
              </button>
            )}
          </div>
        </div>
      )}

      {error.setup_instructions && (
        <div className="banner-setup-guide">
          <div className="setup-guide-header">
            <Terminal size={13} />
            <span>Setup Guide</span>
            <button
              type="button"
              className="btn-copy-instructions"
              onClick={handleCopyInstructions}
              title="Copy setup commands"
            >
              {copied ? <Check size={11} color="var(--accent-emerald)" /> : <Copy size={11} />}
              <span>{copied ? 'Copied' : 'Copy Commands'}</span>
            </button>
          </div>
          <pre className="banner-code-block">
            <code>{error.setup_instructions}</code>
          </pre>
        </div>
      )}
    </div>
  );
};
