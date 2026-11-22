import React, { useState } from 'react';
import { X, User, Mail, Lock, Eye, EyeOff, LogIn, UserPlus, LogOut, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const { user, isAuthenticated, login, register, logout, isLoading } = useAuth();

  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      if (activeTab === 'login') {
        if (!email.trim() || !password) {
          setErrorMsg('Please enter both email and password.');
          return;
        }
        await login({ email: email.trim(), password });
        setSuccessMsg('Signed in successfully!');
        setTimeout(() => {
          onClose();
          setSuccessMsg(null);
        }, 800);
      } else {
        if (!name.trim() || name.trim().length < 2) {
          setErrorMsg('Name must be at least 2 characters.');
          return;
        }
        if (!email.trim() || !email.includes('@')) {
          setErrorMsg('Please enter a valid email address.');
          return;
        }
        if (password.length < 8) {
          setErrorMsg('Password must be at least 8 characters long.');
          return;
        }
        await register({ name: name.trim(), email: email.trim(), password });
        setSuccessMsg('Account created successfully!');
        setTimeout(() => {
          onClose();
          setSuccessMsg(null);
        }, 800);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication request failed.');
    }
  };

  const handleLogout = async () => {
    setErrorMsg(null);
    await logout();
    onClose();
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <div className="modal-dialog auth-modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge">
              <ShieldCheck size={18} className="accent-teal" />
            </div>
            <div>
              <h2 id="auth-modal-title" className="modal-title">
                {isAuthenticated ? 'User Account' : activeTab === 'login' ? 'Sign In to MTCB' : 'Create an Account'}
              </h2>
              <p className="modal-subtitle">
                {isAuthenticated
                  ? 'Manage your profile and authenticated session'
                  : 'Optional account registration • Basic translation is always free without sign-in'}
              </p>
            </div>
          </div>
          <button type="button" className="btn-modal-close" onClick={onClose} aria-label="Close dialog">
            <X size={16} />
          </button>
        </div>

        {/* Content Body */}
        <div className="modal-body">
          {isAuthenticated && user ? (
            /* Logged-In Profile View */
            <div className="user-profile-view">
              <div className="profile-card">
                <div className="profile-avatar">
                  {user.name.slice(0, 2).toUpperCase()}
                </div>
                <div className="profile-info">
                  <h3 className="profile-name">{user.name}</h3>
                  <p className="profile-email">{user.email}</p>
                  <span className="profile-badge">
                    <CheckCircle2 size={12} color="#10b981" /> Verified Session
                  </span>
                </div>
              </div>

              <div className="profile-meta-grid">
                <div className="meta-item">
                  <span className="meta-label">Member Since</span>
                  <span className="meta-value">
                    {new Date(user.created_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Session Protection</span>
                  <span className="meta-value">PBKDF2-HMAC-SHA256</span>
                </div>
              </div>

              <div className="profile-actions">
                <button
                  type="button"
                  className="btn-danger-outline"
                  onClick={handleLogout}
                  disabled={isLoading}
                >
                  <LogOut size={14} />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          ) : (
            /* Sign In / Sign Up Form */
            <>
              {/* Tab Selector */}
              <div className="auth-tab-bar" role="tablist">
                <button
                  type="button"
                  className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
                  onClick={() => {
                    setActiveTab('login');
                    setErrorMsg(null);
                  }}
                  role="tab"
                  aria-selected={activeTab === 'login'}
                >
                  <LogIn size={14} />
                  <span>Sign In</span>
                </button>
                <button
                  type="button"
                  className={`auth-tab ${activeTab === 'register' ? 'active' : ''}`}
                  onClick={() => {
                    setActiveTab('register');
                    setErrorMsg(null);
                  }}
                  role="tab"
                  aria-selected={activeTab === 'register'}
                >
                  <UserPlus size={14} />
                  <span>Create Account</span>
                </button>
              </div>

              {errorMsg && (
                <div className="auth-error-banner" role="alert">
                  <span>{errorMsg}</span>
                </div>
              )}

              {successMsg && (
                <div className="auth-success-banner" role="status">
                  <CheckCircle2 size={14} />
                  <span>{successMsg}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="auth-form">
                {activeTab === 'register' && (
                  <div className="form-group">
                    <label htmlFor="auth-name" className="form-label">
                      Full Name
                    </label>
                    <div className="input-with-icon">
                      <User size={15} className="input-lead-icon" />
                      <input
                        id="auth-name"
                        type="text"
                        className="form-input"
                        placeholder="Ada Lovelace"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        autoComplete="name"
                      />
                    </div>
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="auth-email" className="form-label">
                    Email Address
                  </label>
                  <div className="input-with-icon">
                    <Mail size={15} className="input-lead-icon" />
                    <input
                      id="auth-email"
                      type="email"
                      className="form-input"
                      placeholder="developer@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      autoComplete="email"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="auth-password" className="form-label">
                    Password {activeTab === 'register' && <span className="label-hint">(min 8 characters)</span>}
                  </label>
                  <div className="input-with-icon">
                    <Lock size={15} className="input-lead-icon" />
                    <input
                      id="auth-password"
                      type={showPassword ? 'text' : 'password'}
                      className="form-input"
                      placeholder="••••••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete={activeTab === 'login' ? 'current-password' : 'new-password'}
                    />
                    <button
                      type="button"
                      className="btn-password-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                      tabIndex={-1}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>

                <div className="auth-footer-actions">
                  <button
                    type="submit"
                    className="btn-primary auth-submit-btn"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <span className="btn-spinner"></span>
                    ) : activeTab === 'login' ? (
                      <>
                        <LogIn size={14} />
                        <span>Sign In</span>
                      </>
                    ) : (
                      <>
                        <UserPlus size={14} />
                        <span>Create Account</span>
                      </>
                    )}
                  </button>
                </div>
              </form>

              <div className="guest-notice">
                <span className="guest-badge">Guest Friendly</span>
                <p>
                  You do not need an account to use MTCB translation. Feel free to close this dialog and translate freely.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
