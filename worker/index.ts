/**
 * MTCB (MEHTYS CODE BRIDGE) - Cloudflare Worker Entrypoint
 * Handles static asset delivery with SPA fallback and provides cloud translation API endpoints.
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
    `----------------------------------------------------\n\n` +
    `${guidanceSection}` +
    `TASK:\n` +
    `Translate the following ${sourceLang} source code into ${targetLang}.\n` +
    `Remember: Do NOT fix bugs, do NOT correct typos in strings or comments, do NOT remove duplicated items, and do NOT refactor code.\n\n` +
    `Respond STRICTLY with valid JSON conforming to this schema:\n` +
    `{\n` +
    `  "translated_code": "pure translated code preserving all content, typos, and bugs",\n` +
    `  "explanation": "concise explanation of necessary syntax adaptations made",\n` +
    `  "warnings": ["list of behavioral differences, potential bugs identified in source, or platform caveats"]\n` +
    `}\n\n` +
    `--- SOURCE CODE (${sourceLang}) ---\n` +
    `${code}\n` +
    `--- END SOURCE CODE ---\n`
  );
}

function mockTranslate(sourceLang: string, targetLang: string, code: string): string {
  if (sourceLang === 'python' && targetLang === 'javascript') {
    return code
      .split('\n')
      .map((line) => {
        let l = line.replace(/^\s*#/, '//');
        l = l.replace(/\bprint\s*\(/g, 'console.log(');
        l = l.replace(/\bdef\s+([a-zA-Z0-9_]+)\s*\((.*?)\):/g, 'function $1($2) {');
        l = l.replace(/\bTrue\b/g, 'true').replace(/\bFalse\b/g, 'false').replace(/\bNone\b/g, 'null');
        return l;
      })
      .join('\n');
  } else if (sourceLang === 'javascript' && targetLang === 'python') {
    return code
      .split('\n')
      .map((line) => {
        let l = line.replace(/^\s*\/\//, '#');
        l = l.replace(/\bconsole\.log\s*\(/g, 'print(');
        l = l.replace(/\bfunction\s+([a-zA-Z0-9_]+)\s*\((.*?)\)\s*\{/g, 'def $1($2):');
        l = l.replace(/\btrue\b/g, 'True').replace(/\bfalse\b/g, 'False').replace(/\bnull\b/g, 'None');
        l = l.replace(/;\s*$/, '');
        return l;
      })
      .join('\n');
  }
  return code;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Handle CORS preflight for all /api endpoints
    if (request.method === 'OPTIONS' && url.pathname.startsWith('/api/')) {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, x-goog-api-key',
        },
      });
    }

    // Optional proxy to external backend if BACKEND_API_URL is configured
    if (env.BACKEND_API_URL && url.pathname.startsWith('/api/')) {
      const backendUrl = new URL(url.pathname + url.search, env.BACKEND_API_URL);
      const newReq = new Request(backendUrl.toString(), {
        method: request.method,
        headers: request.headers,
        body: request.body,
        redirect: 'follow',
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
        {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
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
        {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
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
              details: null,
              error_type: null,
            }),
            { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
          );
        }

        if (provider === 'gemini') {
          const apiKey = (body.api_key || '').trim();
          if (!apiKey) {
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

          const googleRes = await fetch('https://generativelanguage.googleapis.com/v1beta/models', {
            headers: { 'x-goog-api-key': apiKey },
          });

          if (googleRes.status === 200) {
            const data = (await googleRes.json()) as any;
            const models = (data.models || [])
              .filter((m: any) => (m.supportedGenerationMethods || []).includes('generateContent'))
              .map((m: any) => {
                const id = m.name.replace('models/', '');
                return { id, label: `${m.displayName || id} (${id})` };
              });

            return new Response(
              JSON.stringify({
                valid: true,
                provider: 'gemini',
                model: body.model || 'gemini-3.8-flash',
                message: `Connected successfully to Google Gemini. Verified access to ${models.length} active models.`,
                available_models: models,
              }),
              { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
            );
          } else {
            return new Response(
              JSON.stringify({
                valid: false,
                provider: 'gemini',
                model: body.model || 'gemini-3.8-flash',
                message: 'Invalid Google Gemini API key.',
                details: 'Please verify your API key from Google AI Studio (https://aistudio.google.com).',
                error_type: 'InvalidApiKey',
              }),
              { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
            );
          }
        }

        if (provider === 'ollama') {
          return new Response(
            JSON.stringify({
              valid: false,
              provider: 'ollama',
              model: body.model || 'qwen2.5-coder:7b',
              message: 'Local Ollama is offline or unreachable from cloud worker.',
              details: 'Ollama runs locally on http://localhost:11434. For cloud translation, select Google Gemini in settings.',
              error_type: 'OllamaUnavailable',
            }),
            { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
          );
        }

        return new Response(
          JSON.stringify({
            valid: false,
            provider,
            model: '',
            message: `Unknown provider: '${provider}'.`,
            error_type: 'UnsupportedProvider',
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

          return new Response(
            JSON.stringify({
              source_lang: src,
              target_lang: tgt,
              translated_code: translated,
              explanation: `MTCB faithful translation from ${src} to ${tgt}.`,
              warnings: ['Translated under MTCB Faithful Translation Policy v1.0.0.'],
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
          const geminiRes = await fetch(geminiUrl, {
            method: 'POST',
            headers: {
              'x-goog-api-key': config.api_key.trim(),
              'Content-Type': 'application/json',
              'User-Agent': 'MTCB-MehtysCodeBridge/0.1.0',
            },
            body: JSON.stringify(payload),
          });

          if (!geminiRes.ok) {
            const errText = await geminiRes.text();
            let errMsg = 'Gemini translation request failed.';
            try {
              const errJson = JSON.parse(errText);
              errMsg = errJson.error?.message || errMsg;
            } catch {}
            return new Response(
              JSON.stringify({
                detail: {
                  message: `Google Gemini error: ${errMsg}`,
                  error_type: 'TranslationExecutionError',
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
