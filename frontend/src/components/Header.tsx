import React from 'react';
import { StatusBadge } from './StatusBadge';
import { HealthResponse, ProviderStatusResponse, ProviderConfig } from '../types/translation';
import logoImg from '../assets/mehtys-logo.jpeg';

interface HeaderProps {
  backendHealth: HealthResponse | null;
  providerStatus: ProviderStatusResponse | null;
  isLoadingStatus: boolean;
  onRefreshStatus: () => void;
  currentProviderConfig: ProviderConfig;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  backendHealth,
  providerStatus,
  isLoadingStatus,
  onRefreshStatus,
  currentProviderConfig,
  onOpenSettings,
}) => {
  return (
    <header className="workspace-header">
      <div className="brand-lockup">
        <div className="brand-symbol" title="MEHTYS CODE BRIDGE">
          <img src={logoImg} alt="MEHTYS Logo" className="brand-logo-img" />
        </div>
        <div className="brand-text">
          <div className="brand-heading">
            <span className="brand-acronym">MTCB</span>
            <span className="brand-divider">/</span>
            <span className="brand-name">MEHTYS CODE BRIDGE</span>
          </div>
          <span className="brand-subtitle">
            Local &amp; Cloud Python ⇄ JavaScript bidirectional translation
          </span>
        </div>
      </div>

      <StatusBadge
        backendHealth={backendHealth}
        providerStatus={providerStatus}
        isLoading={isLoadingStatus}
        onRefresh={onRefreshStatus}
        currentProviderConfig={currentProviderConfig}
        onOpenSettings={onOpenSettings}
      />
    </header>
  );
};
