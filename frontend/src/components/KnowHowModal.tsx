import React from 'react';
import { X, HelpCircle, AlertTriangle, CheckCircle2, ShieldAlert, Cpu, Layers, FileCode2 } from 'lucide-react';
import { AnalysisData } from '../types/translation';

interface KnowHowModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis?: AnalysisData;
}

export const KnowHowModal: React.FC<KnowHowModalProps> = ({ isOpen, onClose, analysis }) => {
  if (!isOpen) return null;

  const knowHow = analysis?.know_how;
  const breakdown = analysis?.breakdown;
  const metrics = analysis?.metrics;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="know-how-title">
      <div className="modal-dialog know-how-modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge">
              <HelpCircle size={18} className="accent-teal" />
            </div>
            <div>
              <h2 id="know-how-title" className="modal-title">
                Know How? Translation Analysis Explained
              </h2>
              <p className="modal-subtitle">
                Transparent breakdown of how your translation was measured, compared, and analyzed
              </p>
            </div>
          </div>
          <button type="button" className="btn-modal-close" onClick={onClose} aria-label="Close dialog">
            <X size={16} />
          </button>
        </div>

        {/* Content Body */}
        <div className="modal-body know-how-body">
          {/* Construct Inventory Summary */}
          {breakdown && (
            <div className="profile-meta-grid">
              <div className="meta-item">
                <span className="meta-label">Identifiers Analyzed</span>
                <span className="meta-value">
                  {breakdown.identifiers_retained_count} of {breakdown.identifiers_source_count} retained
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-label">String Literals Analyzed</span>
                <span className="meta-value">
                  {breakdown.strings_retained_count} of {breakdown.strings_source_count} preserved
                </span>
              </div>
            </div>
          )}

          {/* Section 1: Critical Disclosure */}
          <div className="know-how-callout alert-warning">
            <div className="callout-header">
              <ShieldAlert size={16} color="#f59e0b" />
              <h4>Why High Structural Preservation Is Not a Guarantee of Correctness</h4>
            </div>
            <p>
              {knowHow?.why_preservation_is_not_guarantee ||
                'Two programs can have identical 100% structural preservation (same number of functions, loops, and variables) yet produce completely different results if language semantics differ (such as Python integer division // vs JavaScript / or 0-indexing edge cases). Always run test inputs in the Execution Console to verify actual runtime behavior.'}
            </p>
          </div>

          {/* Section 2: Four Core Metric Explanations */}
          <div className="metric-explanation-list">
            {/* Metric 1 */}
            <div className="metric-card">
              <div className="metric-card-header">
                <Layers size={16} className="accent-blue" />
                <div>
                  <h3 className="metric-card-title">1. Structural Preservation</h3>
                  <span className="metric-method-tag">Method: Static AST &amp; Construct Inventory</span>
                </div>
                <span className="metric-score-badge">
                  {metrics?.structural_preservation?.label || 'N/A'}
                </span>
              </div>
              <p className="metric-desc">
                Measures whether your original program's architecture—functions, control flow, loops, and return statements—was retained intact.
              </p>
              {knowHow?.structural_explanation && (
                <div className="metric-specific-box">
                  <strong>Specific to this translation:</strong> {knowHow.structural_explanation}
                </div>
              )}
            </div>

            {/* Metric 2 */}
            <div className="metric-card">
              <div className="metric-card-header">
                <FileCode2 size={16} className="accent-teal" />
                <div>
                  <h3 className="metric-card-title">2. Content Preservation</h3>
                  <span className="metric-method-tag">Method: Identifier &amp; Literal Retention</span>
                </div>
                <span className="metric-score-badge">
                  {metrics?.content_preservation?.label || 'N/A'}
                </span>
              </div>
              <p className="metric-desc">
                Measures whether your variable names, function identifiers, string literals, and comments were preserved without unwanted renaming or deletion.
              </p>
              {knowHow?.content_explanation && (
                <div className="metric-specific-box">
                  <strong>Specific to this translation:</strong> {knowHow.content_explanation}
                </div>
              )}
            </div>

            {/* Metric 3 */}
            <div className="metric-card">
              <div className="metric-card-header">
                <Cpu size={16} className="accent-violet" />
                <div>
                  <h3 className="metric-card-title">3. Semantic Fidelity (Static Estimate)</h3>
                  <span className="metric-method-tag">Method: Heuristic Idiom &amp; Diagnostic Weighting</span>
                </div>
                <span className="metric-score-badge">
                  {metrics?.semantic_fidelity?.label || 'N/A'}
                </span>
              </div>
              <p className="metric-desc">
                An estimated score combining structural symmetry and identifier fidelity, penalized if translation warnings or idiom risks were detected.
              </p>
              {knowHow?.semantic_explanation && (
                <div className="metric-specific-box">
                  <strong>Specific to this translation:</strong> {knowHow.semantic_explanation}
                </div>
              )}
            </div>

            {/* Metric 4 */}
            <div className="metric-card">
              <div className="metric-card-header">
                <CheckCircle2 size={16} className="accent-emerald" />
                <div>
                  <h3 className="metric-card-title">4. Behavioral Verification</h3>
                  <span className="metric-method-tag">Method: Live Runtime Output Comparison</span>
                </div>
                <span className={`metric-score-badge ${metrics?.behavioral_verification?.verified ? 'verified' : 'unverified'}`}>
                  {metrics?.behavioral_verification?.label || 'Not verified'}
                </span>
              </div>
              <p className="metric-desc">
                Static analysis cannot prove that code behaves properly. True behavioral verification happens only when you run both original and translated programs with equivalent inputs and observe identical outputs.
              </p>
            </div>
          </div>

          {/* Section 3: What Was NOT Verified */}
          <div className="what-not-verified-section">
            <h4 className="section-subtitle">
              <AlertTriangle size={15} color="#ef4444" />
              <span>What Was Not Verified by Static Analysis</span>
            </h4>
            <ul className="not-verified-list">
              {knowHow?.what_was_not_verified?.map((item, idx) => (
                <li key={idx}>
                  <span className="bullet-dot">&bull;</span>
                  <span>{item}</span>
                </li>
              )) || (
                <>
                  <li>Runtime outputs across diverse user inputs</li>
                  <li>Floating point rounding differences between Python and JavaScript</li>
                  <li>Infinite loops or recursion stack overflows</li>
                  <li>Async promise and microtask scheduling differences</li>
                </>
              )}
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button type="button" className="btn-primary" onClick={onClose}>
            Understood
          </button>
        </div>
      </div>
    </div>
  );
};
