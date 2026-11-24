import {
  HealthResponse,
  ProviderStatusResponse,
  ProviderTestRequest,
  ProviderTestResponse,
  TranslationRequest,
  TranslationResponse,
} from '../types/translation';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class TranslationApiError extends Error {
  setup_instructions?: string | null;
  error_type?: string;
  statusCode?: number;
  can_switch_provider?: boolean;

  constructor(
    message: string,
    setup_instructions?: string | null,
    error_type?: string,
    statusCode?: number,
    can_switch_provider?: boolean
  ) {
    super(message);
    this.name = 'TranslationApiError';
    this.setup_instructions = setup_instructions;
    this.error_type = error_type;
    this.statusCode = statusCode;
    this.can_switch_provider = can_switch_provider;
  }
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) {
    throw new TranslationApiError(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function getProviderStatus(): Promise<ProviderStatusResponse> {
  try {
    const res = await fetch(`${BASE_URL}/api/providers/status`);
    if (!res.ok) {
      return {
        provider: 'unknown',
        available: false,
        model: 'unknown',
        details: `Backend returned status ${res.status}`,
      };
    }
    return await res.json();
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Backend offline or unreachable';
    return {
      provider: 'ollama',
      available: false,
      model: 'unknown',
      details: errorMsg,
      setup_instructions: 'Ensure the backend server is running on port 8000.',
    };
  }
}

export async function testProvider(req: ProviderTestRequest): Promise<ProviderTestResponse> {
  try {
    const res = await fetch(`${BASE_URL}/api/providers/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      return {
        valid: false,
        provider: req.provider,
        model: req.model || '',
        message: `Connection test endpoint returned HTTP ${res.status}`,
        error_type: 'HttpError',
      };
    }
    return await res.json();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Network error';
    return {
      valid: false,
      provider: req.provider,
      model: req.model || '',
      message: `Failed to connect to backend server: ${msg}`,
      error_type: 'NetworkError',
    };
  }
}

export async function translateCode(request: TranslationRequest): Promise<TranslationResponse> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/translate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  } catch (networkError: unknown) {
    const msg = networkError instanceof Error ? networkError.message : 'Network error';
    throw new TranslationApiError(
      `Failed to connect to backend server: ${msg}. Please ensure FastAPI is running.`,
      'Run: uvicorn app.main:app --reload --port 8000',
      'NetworkError'
    );
  }

  if (!response.ok) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      // Non-JSON response
    }

    if (errorData && errorData.detail) {
      if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
        throw new TranslationApiError(
          errorData.detail.message || 'Translation failed.',
          errorData.detail.setup_instructions,
          errorData.detail.error_type,
          response.status,
          errorData.detail.can_switch_provider
        );
      } else if (Array.isArray(errorData.detail)) {
        // FastAPI validation errors
        const validationMsg = errorData.detail
          .map((d: any) => `${d.loc?.slice(-1)[0] || 'field'}: ${d.msg}`)
          .join('; ');
        throw new TranslationApiError(validationMsg, null, 'ValidationError', response.status);
      } else {
        throw new TranslationApiError(String(errorData.detail), null, 'ApiError', response.status);
      }
    }

    throw new TranslationApiError(
      `Translation request failed with status ${response.status}`,
      null,
      'HttpError',
      response.status
    );
  }

  return response.json();
}
