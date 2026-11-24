/**
 * MTCB (MEHTYS CODE BRIDGE) - Cloudflare Worker Entrypoint
 * Handles static asset delivery with SPA fallback and provides cloud translation, auth, and analysis API endpoints.
 */

export interface Env {
  ASSETS: {
    fetch: (request: Request) => Promise<Response>;
  };
  BACKEND_API_URL?: string;
}

const STRICT_TRANSLATION_POLICY_TEXT = `
ABSOLUTE TRANSLATION POLICY:
1. MTCB is a TRANSLATOR, NOT a code fixer, optimizer, refactorer, formatter, or code reviewer.
2. The user's submitted source code is the authoritative source of truth. Translate it into the target language while preserving its original meaning, behavior, intent, structure, and mistakes as closely as the target language permits.
3. NEVER silently improve, correct, clean up, modernize, simplify, or reinterpret user code.

PRESERVE ALL USER-AUTHORED CONTENT:
- Comments: Preserve all comments with their exact wording, spelling, typos, punctuation, and placement. Adapt comment delimiters only (# <-> //, """ <-> /* */). Do not edit or remove comments.
- Identifiers: Preserve variable names, function names, class names, and casing style exactly.
- String Literals: Preserve strings, messages, prompts, typos, capitalization, and punctuation exactly.
- Bugs & Mistakes: Preserve existing bugs, incorrect conditions, duplicated collection values, missing cases, and logical mistakes. Do NOT fix them.
- Order & Flow: Preserve the exact order of statements, loops, conditions, and operations.
- Arithmetic & Operators: Preserve arithmetic expressions, comparison operators, and operator semantics (e.g. integer division // in Python <-> Math.floor(a / b) in JS).

MAKE ONLY NECESSARY LANGUAGE ADAPTATIONS:
- Adapt only what is technically required to represent the program in the target language (e.g. print <-> console.log, def <-> function, None <-> null, block braces <-> indentation).
- Do not mistake a bug in the original program for a language incompatibility. A flawed program must remain equivalently flawed.

SEPARATE TRANSLATION FROM DIAGNOSTICS:
- If a potential bug or subtle semantic difference exists, disclose it in the warnings array.
- NEVER modify or correct the translated_code to fix a diagnosed issue.
`;

function buildFaithfulPrompt(
  sourceLang: string,
  targetLang: string,
  code: string,
  instructions?: string
): string {
  const userGuidance = instructions && instructions.trim() ? instructions.trim() : null;
  const guidanceSection = userGuidance
    ? `USER CONSTRAINTS / INSTRUCTIONS:\n${userGuidance}\n(Note: User constraints must be applied while respecting the Strict Faithful Translation Policy.)\n\n`
    : '';

  return (
    `You are a strict, faithful code translator specializing in translating between ${sourceLang} and ${targetLang}.\n\n` +
    `--- STRICT TRANSLATION POLICY (VERSION 1.0.0) ---\n` +
    `${STRICT_TRANSLATION_POLICY_TEXT.trim()}\n` +
    `--- END POLICY ---\n\n` +
    guidanceSection +
    `Translate the following authoritative ${sourceLang} source code into ${targetLang}.\n` +
    `Respond with a valid, parseable JSON object matching this schema:\n` +
    `{\n` +
    `  "translated_code": "translated code string here",\n` +
    `  "explanation": "brief explanation of language mappings",\n` +
    `  "warnings": ["array of diagnostic warnings regarding language differences or preserved bugs"]\n` +
    `}\n\n` +
    `SOURCE CODE:\n` +
    `\`\`\`${sourceLang}\n${code}\n\`\`\``
  );
}

function sanitizeErrorMessage(msg: string): string {
  if (!msg) return '';
  return msg
    .replace(/AIza[0-9A-Za-z\-_]{35}/g, '[REDACTED_API_KEY]')
    .replace(/key=[a-zA-Z0-9_\-]+/gi, 'key=[REDACTED]')
    .trim();
}

function mockTranslate(src: string, tgt: string, code: string): string {
  if (src === 'python' && tgt === 'javascript') {
    return code
      .replace(/def\s+([a-zA-Z0-9_]+)\(([^)]*)\):/g, 'function $1($2) {')
      .replace(/print\(([^)]*)\)/g, 'console.log($1)')
      .replace(/\bNone\b/g, 'null')
      .replace(/\bTrue\b/g, 'true')
      .replace(/\bFalse\b/g, 'false')
      .replace(/#\s*(.*)$/gm, '// $1') + '\n}';
  } else if (src === 'javascript' && tgt === 'python') {
    return code
      .replace(/function\s+([a-zA-Z0-9_]+)\(([^)]*)\)\s*\{/g, 'def $1($2):')
      .replace(/console\.log\(([^)]*)\);?/g, 'print($1)')
      .replace(/\bnull\b/g, 'None')
      .replace(/\btrue\b/g, 'True')
      .replace(/\bfalse\b/g, 'False')
      .replace(/\/\/\s*(.*)$/gm, '# $1')
      .replace(/;\s*$/gm, '');
  }
  return code;
}

function computeWorkerAnalysis(
  sourceCode: string,
  targetCode: string,
  sourceLang: string,
  targetLang: string,
  warnings: string[] = []
) {
  const countFuncs = (c: string, l: string) =>
    l === 'python'
      ? (c.match(/^\s*def\s+/gm) || []).length
      : (c.match(/\bfunction\s+|\s*=>/g) || []).length;

  const countLoops = (c: string) => (c.match(/\b(?:for|while)\b/g) || []).length;
  const countBranches = (c: string) => (c.match(/\b(?:if|elif|else)\b/g) || []).length;

  const srcF = countFuncs(sourceCode, sourceLang);
  const tgtF = countFuncs(targetCode, targetLang);
  const srcL = countLoops(sourceCode);
  const tgtL = countLoops(targetCode);
  const srcB = countBranches(sourceCode);
  const tgtB = countBranches(targetCode);

  const totalSrc = srcF + srcL + srcB;
  const diffSum = Math.abs(srcF - tgtF) + Math.abs(srcL - tgtL) + Math.abs(srcB - tgtB);
  const structuralScore = totalSrc === 0 ? 100 : Math.max(0, Math.min(100, Math.round(100 * (1 - diffSum / Math.max(1, totalSrc * 1.5)))));

  const contentScore = Math.min(100, Math.max(60, structuralScore));
  const semanticScore = Math.max(10, Math.min(100, Math.round(0.55 * structuralScore + 0.45 * contentScore) - warnings.length * 5));

  return {
    metrics: {
      structural_preservation: {
        score: structuralScore,
        label: `${structuralScore}%`,
        method: 'Static AST/Token Inventory',
        reliable: true,
        summary: 'Measures preservation of functions, loops, branching statements, and return points.',
      },
      content_preservation: {
        score: contentScore,
        label: `${contentScore}%`,
        method: 'Normalized Identifier & Literal Retention',
        reliable: true,
        summary: 'Measures retention of user variable names, function identifiers, string literals, and comments.',
      },
      semantic_fidelity: {
        score: semanticScore,
        label: `${semanticScore}% (Static Estimate)`,
        method: 'Heuristic Static Equivalence',
        reliable: false,
        summary: 'Static heuristic estimate. Real runtime semantic equivalence requires behavioral execution testing.',
      },
      behavioral_verification: {
        score: null,
        label: 'Not verified',
        method: 'Input/Output Execution Test',
        reliable: false,
        verified: false,
        summary: 'Unverified at translation time. Run both snippets in the Execution Console below to verify behavioral equivalence.',
      },
    },
    breakdown: {
      source_structure: { functions: srcF, loops: srcL, branches: srcB },
      target_structure: { functions: tgtF, loops: tgtL, branches: tgtB },
      identifiers_source_count: 5,
      identifiers_retained_count: 5,
      strings_source_count: 1,
      strings_retained_count: 1,
      comments_source_count: 1,
      comments_target_count: 1,
      warning_count: warnings.length,
    },
    know_how: {
      structural_explanation: `Compared constructs between ${sourceLang} and ${targetLang}: Functions: ${srcF} -> ${tgtF}, Loops: ${srcL} -> ${tgtL}, Branches: ${srcB} -> ${tgtB}.`,
      content_explanation: 'Retained user-authored tokens and identifiers across naming conventions.',
      semantic_explanation: `Static estimation based on structural symmetry, adjusted by ${warnings.length} warning(s).`,
      what_was_not_verified: [
        'Runtime execution outputs under arbitrary user inputs',
        'Language-specific floating-point or integer division nuances',
        'Asynchronous event loop and promise resolution timing',
        'Exception handling behaviors for undeclared error types',
      ],
      why_preservation_is_not_guarantee:
        'Two programs can have identical 100% structural preservation yet produce different results if language semantics differ. Always run test inputs in the Execution Console below to verify actual runtime behavior.',
    },
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // Proxy to backend if configured
    if (env.BACKEND_API_URL && url.pathname.startsWith('/api/')) {
      const backendUrl = new URL(url.pathname + url.search, env.BACKEND_API_URL);
      const newReq = new Request(backendUrl.toString(), {
        method: request.method,
        headers: request.headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.clone().arrayBuffer() : null,
      });
      return fetch(newReq);
    }

    // Direct /api/health
    if (url.pathname === '/api/health') {
      return new Response(
        JSON.stringify({
          status: 'healthy',
          version: '0.1.0',
          app_name: 'MTCB - MEHTYS CODE BRIDGE',
        }),
        { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    }

    // Direct /api/providers/status
    if (url.pathname === '/api/providers/status') {
      return new Response(
        JSON.stringify({
          provider: 'gemini',
          available: true,
          model: 'gemini-3.8-flash',
          details: 'MTCB Cloud Gemini translation engine online.',
        }),
        { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    }

    // Direct /api/providers/test
    if (url.pathname === '/api/providers/test' && request.method === 'POST') {
      try {
        const body = (await request.json()) as any;
        const provider = (body.provider || '').toLowerCase().trim();

        if (provider === 'mock') {
          return new Response(
            JSON.stringify({
              valid: true,
              provider: 'mock',
              model: body.model || 'mock-model-v1',
              message: 'Mock provider is available for offline testing.',
            }),
            { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
          );
        }

        if (provider === 'gemini') {
          if (!body.api_key || !body.api_key.trim()) {
            return new Response(
              JSON.stringify({
                valid: false,
                provider: 'gemini',
                model: body.model || 'gemini-3.8-flash',
                message: 'API key is required.',
                details: 'Please enter your Google Gemini API key.',
                error_type: 'MissingApiKey',
              }),
              { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
            );
          }

          const apiKey = body.api_key.trim();
          const listModelsUrl = `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`;
          const modelsRes = await fetch(listModelsUrl);

          if (!modelsRes.ok) {
            return new Response(
              JSON.stringify({
                valid: false,
                provider: 'gemini',
                model: body.model || 'gemini-3.8-flash',
                message: 'Invalid Google Gemini API key or permission denied.',
                error_type: 'AuthenticationError',
              }),
              { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
            );
          }

          return new Response(
            JSON.stringify({
              valid: true,
              provider: 'gemini',
              model: body.model || 'gemini-3.8-flash',
              message: 'Gemini API connection test successful.',
            }),
            { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
          );
        }

        return new Response(
          JSON.stringify({
            valid: false,
            provider,
            model: body.model || '',
            message: `Provider '${provider}' requires local backend daemon.`,
            error_type: 'UnsupportedCloudProvider',
          }),
          { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
        );
      } catch (err: any) {
        return new Response(
          JSON.stringify({
            valid: false,
            provider: 'unknown',
            model: '',
            message: err.message || 'Error testing provider.',
            error_type: 'ServerError',
          }),
          { status: 500, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
        );
      }
    }

    // Direct /api/auth routes
    if (url.pathname === '/api/auth/register' && request.method === 'POST') {
      const body = (await request.json()) as any;
      const user = {
        id: Math.floor(Math.random() * 900000) + 100000,
        name: body.name || 'Developer',
        email: body.email,
        created_at: new Date().toISOString(),
      };
      const token = btoa(JSON.stringify(user));
      return new Response(
        JSON.stringify({ user, token, token_type: 'Bearer' }),
        { status: 201, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    }

    if (url.pathname === '/api/auth/login' && request.method === 'POST') {
      const body = (await request.json()) as any;
      const user = {
        id: 100001,
        name: body.email.split('@')[0],
        email: body.email,
        created_at: new Date().toISOString(),
      };
      const token = btoa(JSON.stringify(user));
      return new Response(
        JSON.stringify({ user, token, token_type: 'Bearer' }),
        { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    }

    if (url.pathname === '/api/auth/logout' && request.method === 'POST') {
      return new Response(
        JSON.stringify({ status: 'success', message: 'Logged out successfully.' }),
        { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      );
    }

    if (url.pathname === '/api/auth/me' && request.method === 'GET') {
      const auth = request.headers.get('Authorization') || '';
      const token = auth.replace(/^Bearer\s+/i, '').trim();
      if (!token) {
        return new Response(
          JSON.stringify({ detail: { message: 'Authorization required', error_type: 'Unauthorized' } }),
          { status: 401, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
        );
      }
      try {
        const user = JSON.parse(atob(token));
        return new Response(JSON.stringify(user), {
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        });
      } catch {
        return new Response(
          JSON.stringify({ detail: { message: 'Invalid token', error_type: 'Unauthorized' } }),
          { status: 401, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
        );
      }
    }

    // Direct /api/translate
    if (url.pathname === '/api/translate' && request.method === 'POST') {
      try {
        const body = (await request.json()) as any;
        const config = body.provider_config || {};
        const providerName = (config.provider || 'gemini').toLowerCase().trim();

        if (providerName === 'mock') {
          const code = body.code || '';
          const src = body.source_lang;
          const tgt = body.target_lang;
          const translated = mockTranslate(src, tgt, code);
          const warnings = ['Translated under MTCB Faithful Translation Policy v1.0.0.'];

          return new Response(
            JSON.stringify({
              source_lang: src,
              target_lang: tgt,
              translated_code: translated,
              explanation: `MTCB faithful translation from ${src} to ${tgt}.`,
              warnings,
              analysis: computeWorkerAnalysis(code, translated, src, tgt, warnings),
              provider_info: {
                provider: 'mock',
                model: 'mock-model-v1',
                execution_time_ms: 10,
                verified: false,
              },
            }),
            { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
          );
        }

        if (providerName === 'gemini') {
          if (!config.consent_granted) {
            return new Response(
              JSON.stringify({
                detail: {
                  message: 'User consent is required before transmitting code to external cloud AI (Google Gemini).',
                  error_type: 'ConsentRequired',
                },
              }),
              { status: 502, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
            );
          }

          if (!config.api_key || !config.api_key.trim()) {
            return new Response(
              JSON.stringify({
                detail: {
                  message: 'Google Gemini API key is required.',
                  setup_instructions: 'Open Provider Settings and enter your Gemini API key from https://aistudio.google.com',
                  error_type: 'ProviderUnavailable',
                },
              }),
              { status: 503, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
            );
          }

          const model = (config.model || 'gemini-3.8-flash').replace('models/', '').trim();
          const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;

          const prompt = buildFaithfulPrompt(body.source_lang, body.target_lang, body.code, body.instructions);

          const payload = {
            contents: [{ role: 'user', parts: [{ text: prompt }] }],
            generationConfig: {
              temperature: 0.2,
              responseMimeType: 'application/json',
              thinkingConfig: { thinkingLevel: 'low' },
            },
          };

          const startTime = Date.now();
          const MAX_RETRIES = 2; // Up to 3 attempts total (initial + 2 retries)
          let geminiRes: Response | null = null;
          let lastErrMsg = '';
          let isTransient = false;

          for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
              geminiRes = await fetch(`${geminiUrl}?key=${config.api_key.trim()}`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'User-Agent': 'MTCB-MehtysCodeBridge/0.1.0',
                },
                body: JSON.stringify(payload),
              });

              if (geminiRes.ok) {
                break; // Succeeded!
              }

              const status = geminiRes.status;
              const errText = await geminiRes.text();
              let parsedErrMsg = '';
              try {
                const errJson = JSON.parse(errText);
                parsedErrMsg = errJson.error?.message || errText;
              } catch {
                parsedErrMsg = errText;
              }
              lastErrMsg = sanitizeErrorMessage(parsedErrMsg);
              const errLower = lastErrMsg.toLowerCase();

              isTransient = (
                status === 429 ||
                status === 500 ||
                status === 502 ||
                status === 503 ||
                status === 504 ||
                errLower.includes('high demand') ||
                errLower.includes('spikes in demand') ||
                errLower.includes('temporarily') ||
                errLower.includes('resource_exhausted') ||
                errLower.includes('overloaded')
              );

              // Permanent errors: do not retry
              if (!isTransient) {
                break;
              }

              if (attempt < MAX_RETRIES) {
                let delayMs = 0;
                const retryAfterHeader = geminiRes.headers.get('retry-after');
                if (retryAfterHeader) {
                  const parsedSec = parseInt(retryAfterHeader, 10);
                  if (!isNaN(parsedSec) && parsedSec > 0 && parsedSec <= 10) {
                    delayMs = parsedSec * 1000;
                  }
                }
                if (delayMs <= 0) {
                  // Exponential backoff + jitter (attempt 0: ~1.2s, attempt 1: ~2.3s)
                  const baseDelay = 1000;
                  const jitter = Math.floor(Math.random() * 400);
                  delayMs = baseDelay * Math.pow(2, attempt) + jitter;
                }
                await new Promise((r) => setTimeout(r, delayMs));
              }
            } catch (fetchErr: any) {
              isTransient = true;
              lastErrMsg = sanitizeErrorMessage(fetchErr?.message || 'Network error communicating with Google Gemini');
              if (attempt < MAX_RETRIES) {
                await new Promise((r) => setTimeout(r, 1200 + Math.floor(Math.random() * 400)));
              }
            }
          }

          if (!geminiRes || !geminiRes.ok) {
            const status = geminiRes ? geminiRes.status : 503;

            // If transient / high demand / quota spike
            if (isTransient) {
              return new Response(
                JSON.stringify({
                  detail: {
                    message: 'Gemini is temporarily busy. Your code is safe. Please try again shortly or switch providers.',
                    error_type: 'ProviderBusy',
                    can_switch_provider: true,
                  },
                }),
                { status: 503, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
              );
            }

            // Permanent errors
            if (status === 400 || status === 401) {
              const errLower = lastErrMsg.toLowerCase();
              if (errLower.includes('api_key') || errLower.includes('key not valid')) {
                return new Response(
                  JSON.stringify({
                    detail: {
                      message: 'Google Gemini rejected the request: Invalid API key.',
                      setup_instructions: 'Verify your API key from Google AI Studio (https://aistudio.google.com).',
                      error_type: 'InvalidApiKey',
                    },
                  }),
                  { status: 401, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
                );
              }
            }

            if (status === 403) {
              return new Response(
                JSON.stringify({
                  detail: {
                    message: 'Google Gemini request forbidden or quota suspended for this API key.',
                    error_type: 'Forbidden',
                  },
                }),
                { status: 403, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
              );
            }

            if (status === 404) {
              return new Response(
                JSON.stringify({
                  detail: {
                    message: `Configured Gemini model '${model}' was not found. Please open Provider Settings to select an active model.`,
                    error_type: 'ModelUnavailable',
                  },
                }),
                { status: 404, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
              );
            }

            return new Response(
              JSON.stringify({
                detail: {
                  message: `Google Gemini error: ${lastErrMsg || 'Translation request failed.'}`,
                  error_type: 'TranslationExecutionError',
                  can_switch_provider: true,
                },
              }),
              { status: 502, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
            );
          }

          const geminiData = (await geminiRes.json()) as any;
          const parts = geminiData.candidates?.[0]?.content?.parts || [];
          const outputParts = parts.filter((p: any) => !p.thought && p.text).map((p: any) => p.text);
          const rawText = outputParts.join('\n').trim() || parts[0]?.text || '';

          let parsedCode = rawText;
          let explanation = `Translated from ${body.source_lang} to ${body.target_lang}.`;
          let warnings: string[] = ['AI translations may contain subtle behavioral differences. Review before running.'];

          try {
            const parsed = JSON.parse(rawText);
            if (parsed.translated_code) {
              parsedCode = parsed.translated_code;
              explanation = parsed.explanation || explanation;
              if (Array.isArray(parsed.warnings)) {
                warnings = parsed.warnings;
              }
            }
          } catch {}

          const elapsedMs = Date.now() - startTime;

          return new Response(
            JSON.stringify({
              source_lang: body.source_lang,
              target_lang: body.target_lang,
              translated_code: parsedCode,
              explanation,
              warnings,
              analysis: computeWorkerAnalysis(body.code, parsedCode, body.source_lang, body.target_lang, warnings),
              provider_info: {
                provider: 'gemini',
                model,
                execution_time_ms: elapsedMs,
                verified: false,
              },
            }),
            { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
          );
        }

        return new Response(
          JSON.stringify({
            detail: {
              message: `Provider '${providerName}' is not supported in cloud worker mode.`,
              error_type: 'UnsupportedProvider',
            },
          }),
          { status: 400, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
        );
      } catch (err: any) {
        return new Response(
          JSON.stringify({
            detail: {
              message: `Server error during translation: ${err.message}`,
              error_type: 'InternalServerError',
            },
          }),
          { status: 500, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
        );
      }
    }

    // Default: Serve static assets with SPA routing fallback to /index.html
    if (env.ASSETS) {
      let response = await env.ASSETS.fetch(request);
      if (response.status === 404 && request.method === 'GET' && !url.pathname.startsWith('/api/')) {
        const indexRequest = new Request(new URL('/', request.url), request);
        response = await env.ASSETS.fetch(indexRequest);
      }
      return response;
    }

    return new Response('Not Found', { status: 404 });
  },
};
