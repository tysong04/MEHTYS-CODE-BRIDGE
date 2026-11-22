export type Language = 'python' | 'javascript';
export type ProviderType = 'ollama' | 'gemini' | 'mock';

export interface ProviderConfig {
  provider: ProviderType;
  api_key?: string;
  model?: string;
  base_url?: string;
  consent_granted: boolean;
}

export interface TranslationRequest {
  source_lang: Language;
  target_lang: Language;
  code: string;
  instructions?: string;
  provider_config?: ProviderConfig;
}

export interface ProviderTestRequest {
  provider: ProviderType;
  api_key?: string;
  model?: string;
  base_url?: string;
}

export interface ModelOption {
  id: string;
  label: string;
}

export interface ProviderTestResponse {
  valid: boolean;
  provider: string;
  model: string;
  message: string;
  details?: string | null;
  error_type?: string | null;
  available_models?: ModelOption[] | null;
}

export interface ProviderInfo {
  provider: string;
  model: string;
  execution_time_ms?: number;
  verified: boolean;
}

export interface MetricItem {
  score: number | null;
  label: string;
  method: string;
  reliable: boolean;
  verified?: boolean;
  summary: string;
}

export interface AnalysisBreakdown {
  source_structure: Record<string, number>;
  target_structure: Record<string, number>;
  identifiers_source_count: number;
  identifiers_retained_count: number;
  strings_source_count: number;
  strings_retained_count: number;
  comments_source_count: number;
  comments_target_count: number;
  warning_count: number;
}

export interface KnowHowData {
  structural_explanation: string;
  content_explanation: string;
  semantic_explanation: string;
  what_was_not_verified: string[];
  why_preservation_is_not_guarantee: string;
}

export interface AnalysisData {
  metrics: {
    structural_preservation: MetricItem;
    content_preservation: MetricItem;
    semantic_fidelity: MetricItem;
    behavioral_verification: MetricItem;
  };
  breakdown: AnalysisBreakdown;
  know_how: KnowHowData;
}

export interface ExecutionResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code?: number;
  execution_time_ms: number;
  timed_out: boolean;
  status: 'Completed' | 'RuntimeError' | 'Timeout' | 'SecurityRejection' | 'InternalError';
  disclaimer?: string;
}

export interface TranslationResponse {
  source_lang: Language;
  target_lang: Language;
  translated_code: string;
  explanation: string;
  warnings: string[];
  provider_info: ProviderInfo;
  analysis?: AnalysisData;
}

export interface ProviderStatusResponse {
  provider: string;
  available: boolean;
  model: string;
  details: string;
  setup_instructions?: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  app_name: string;
}

export interface ApiError {
  message: string;
  setup_instructions?: string | null;
  error_type?: string;
}
