import React, { useState } from 'react';
import { BarChart3, HelpCircle, Layers, FileCode2, Cpu, CheckCircle2 } from 'lucide-react';
import { AnalysisData } from '../types/translation';
import { KnowHowModal } from './KnowHowModal';

interface AnalysisPanelProps {
  analysis?: AnalysisData;
  isTranslating: boolean;
  hasOutput: boolean;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  analysis,
  isTranslating,
  hasOutput,
}) => {
  const [isKnowHowOpen, setIsKnowHowOpen] = useState(false);

  if (!hasOutput || isTranslating) {
    return null;
  }

  const metrics = analysis?.metrics;

  return (
    <section className="analysis-panel" aria-label="Translation Efficiency and Analysis Panel">
      <div className="analysis-panel-header">
        <div className="panel-title-group">
          <BarChart3 size={15} className="accent-teal" />
          <h3 className="panel-title">Translation Efficiency &amp; Analysis</h3>
        </div>
        <span className="analysis-method-badge" title="Deterministic static AST inventory">
          Defensible Metrics
        </span>
      </div>

      <div className="analysis-metrics-grid">
        {/* Metric 1: Structural Preservation */}
        <div className="metric-row">
          <div className="metric-meta">
            <div className="metric-name-wrap">
              <Layers size={13} className="accent-blue" />
              <span className="metric-name">Structural Preservation</span>
            </div>
            <span className="metric-value-label">
              {metrics?.structural_preservation?.score !== null && metrics?.structural_preservation?.score !== undefined
                ? `${metrics.structural_preservation.score}%`
                : 'Insufficient data'}
            </span>
          </div>
          <div className="metric-progress-track">
            <div
              className="metric-progress-fill fill-blue"
              style={{
                width: `${metrics?.structural_preservation?.score ?? 0}%`,
              }}
            />
          </div>
          <p className="metric-sub-note">Functions, control flow branches, loops &amp; return points</p>
        </div>

        {/* Metric 2: Content Preservation */}
        <div className="metric-row">
          <div className="metric-meta">
            <div className="metric-name-wrap">
              <FileCode2 size={13} className="accent-teal" />
              <span className="metric-name">Content Preservation</span>
            </div>
            <span className="metric-value-label">
              {metrics?.content_preservation?.score !== null && metrics?.content_preservation?.score !== undefined
                ? `${metrics.content_preservation.score}%`
                : 'Insufficient data'}
            </span>
          </div>
          <div className="metric-progress-track">
            <div
              className="metric-progress-fill fill-teal"
              style={{
                width: `${metrics?.content_preservation?.score ?? 0}%`,
              }}
            />
          </div>
          <p className="metric-sub-note">User identifiers, string literals &amp; comments</p>
        </div>

        {/* Metric 3: Semantic Fidelity */}
        <div className="metric-row">
          <div className="metric-meta">
            <div className="metric-name-wrap">
              <Cpu size={13} className="accent-violet" />
              <span className="metric-name">Semantic Fidelity</span>
            </div>
            <span className="metric-value-label estimate">
              {metrics?.semantic_fidelity?.score !== null && metrics?.semantic_fidelity?.score !== undefined
                ? `${metrics.semantic_fidelity.score}% (Estimate)`
                : 'Insufficient data'}
            </span>
          </div>
          <div className="metric-progress-track">
            <div
              className="metric-progress-fill fill-violet"
              style={{
                width: `${metrics?.semantic_fidelity?.score ?? 0}%`,
              }}
            />
          </div>
          <p className="metric-sub-note">Static heuristic estimate • Unverified at runtime</p>
        </div>

        {/* Metric 4: Behavioral Verification */}
        <div className="metric-row verification-row">
          <div className="metric-meta">
            <div className="metric-name-wrap">
              <CheckCircle2 size={13} className={metrics?.behavioral_verification?.verified ? 'accent-emerald' : 'accent-muted'} />
              <span className="metric-name">Behavioral Verification</span>
            </div>
            <span
              className={`metric-tag-pill ${
                metrics?.behavioral_verification?.verified
                  ? 'pill-verified'
                  : metrics?.behavioral_verification?.label?.includes('Mismatch')
                  ? 'pill-mismatch'
                  : 'pill-unverified'
              }`}
            >
              {metrics?.behavioral_verification?.label || 'Not verified'}
            </span>
          </div>
          <p className="verification-instruction">
            {metrics?.behavioral_verification?.verified
              ? '✓ Outputs verified matching across test inputs.'
              : 'Run test inputs in the Code Execution Console below to verify program behavior.'}
          </p>
        </div>
      </div>

      {/* "Know How?" Button */}
      <div className="analysis-panel-footer">
        <button
          type="button"
          className="btn-know-how"
          onClick={() => setIsKnowHowOpen(true)}
          title="See exact calculation formulas and analysis breakdown"
          aria-label="Open Know How explanation dialog"
        >
          <HelpCircle size={14} />
          <span>Know How?</span>
        </button>
      </div>

      {/* Know How Modal */}
      <KnowHowModal
        isOpen={isKnowHowOpen}
        onClose={() => setIsKnowHowOpen(false)}
        analysis={analysis}
      />
    </section>
  );
};
