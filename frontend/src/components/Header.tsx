import React from 'react';
import { LogIn } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { HealthResponse, ProviderStatusResponse, ProviderConfig } from '../types/translation';
import { useAuth } from '../context/AuthContext';
import logoImg from '../assets/mehtys-logo.jpeg';

interface HeaderProps {
  backendHealth: HealthResponse | null;
  providerStatus: ProviderStatusResponse | null;
  isLoadingStatus: boolean;
  onRefreshStatus: () => void;
  currentProviderConfig: ProviderConfig;
  onOpenSettings: () => void;
  onOpenAuth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  backendHealth,
  providerStatus,
  isLoadingStatus,
  onRefreshStatus,
  currentProviderConfig,
  onOpenSettings,
  onOpenAuth,
}) => {
  const { user, isAuthenticated } = useAuth();

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

      <div className="header-right-actions">
        <StatusBadge
          backendHealth={backendHealth}
          providerStatus={providerStatus}
          isLoading={isLoadingStatus}
          onRefresh={onRefreshStatus}
          currentProviderConfig={currentProviderConfig}
          onOpenSettings={onOpenSettings}
        />

        <button
          type="button"
          className={`btn-header-auth ${isAuthenticated ? 'logged-in' : ''}`}
          onClick={onOpenAuth}
          title={isAuthenticated ? `Signed in as ${user?.name}` : 'Sign In or Register'}
          aria-label={isAuthenticated ? 'Open user profile' : 'Sign In'}
        >
          {isAuthenticated && user ? (
            <>
              <span className="auth-avatar-pill">
                {user.name.slice(0, 2).toUpperCase()}
              </span>
              <span className="auth-user-name">{user.name.split(' ')[0]}</span>
            </>
          ) : (
            <>
              <LogIn size={13} />
              <span>Sign In</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
