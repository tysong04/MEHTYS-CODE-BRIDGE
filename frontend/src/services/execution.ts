import { ExecutionResult } from '../types/translation';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const TIMEOUT_MS = 3000;

/**
 * Execute JavaScript safely client-side in an isolated Web Worker.
 * - Disables network access (fetch, XMLHttpRequest, WebSocket)
 * - Has no DOM or storage access
 * - Captures console.log, console.warn, console.error
 * - Enforces a 3-second hard timeout via worker.terminate()
 */
export function executeJavaScript(code: string, stdin: string = ''): Promise<ExecutionResult> {
  return new Promise((resolve) => {
    const startTime = performance.now();

    // Script to run inside the Web Worker
    const workerScript = `
      // Block network capabilities
      self.fetch = undefined;
      self.XMLHttpRequest = undefined;
      self.WebSocket = undefined;
      self.importScripts = undefined;

      const outputLogs = [];
      const errorLogs = [];

      // Intercept console outputs
      console.log = (...args) => {
        outputLogs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
      };
      console.info = console.log;
      console.warn = (...args) => {
        outputLogs.push('[WARN] ' + args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
      };
      console.error = (...args) => {
        errorLogs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
      };

      // Stdin line provider
      const stdinData = ${JSON.stringify(stdin)};
      let stdinLines = stdinData ? stdinData.split('\\n') : [];
      let stdinIndex = 0;
      function input(promptText) {
        if (promptText) console.log(promptText);
        if (stdinIndex < stdinLines.length) {
          return stdinLines[stdinIndex++];
        }
        return '';
      }
      self.input = input;
      self.readline = input;

      self.onmessage = () => {
        try {
          // Execute user script in worker scope
          const userFn = new Function('input', 'readline', ${JSON.stringify(code)});
          userFn(input, input);

          self.postMessage({
            success: true,
            stdout: outputLogs.join('\\n'),
            stderr: errorLogs.join('\\n'),
            status: 'Completed'
          });
        } catch (err) {
          self.postMessage({
            success: false,
            stdout: outputLogs.join('\\n'),
            stderr: (errorLogs.length ? errorLogs.join('\\n') + '\\n' : '') + (err && err.stack ? err.stack : String(err)),
            status: 'RuntimeError'
          });
        }
      };
    `;

    let worker: Worker;
    try {
      const blob = new Blob([workerScript], { type: 'application/javascript' });
      const workerUrl = URL.createObjectURL(blob);
      worker = new Worker(workerUrl);
      URL.revokeObjectURL(workerUrl);
    } catch (e: any) {
      resolve({
        success: false,
        stdout: '',
        stderr: `Failed to initialize isolated worker: ${e.message}`,
        execution_time_ms: 0,
        timed_out: false,
        status: 'InternalError',
        disclaimer: 'Browser Web Worker sandbox',
      });
      return;
    }

    let isFinished = false;

    // Hard timeout timer
    const timeoutTimer = setTimeout(() => {
      if (!isFinished) {
        isFinished = true;
        worker.terminate();
        const elapsed = Math.round(performance.now() - startTime);
        resolve({
          success: false,
          stdout: '',
          stderr: `Execution timed out after ${TIMEOUT_MS / 1000} seconds. Infinite loop prevented.`,
          execution_time_ms: elapsed,
          timed_out: true,
          status: 'Timeout',
          disclaimer: 'Client-side isolated Web Worker (no network, no DOM, 3s hard limit)',
        });
      }
    }, TIMEOUT_MS);

    worker.onmessage = (event) => {
      if (!isFinished) {
        isFinished = true;
        clearTimeout(timeoutTimer);
        worker.terminate();
        const elapsed = Math.round(performance.now() - startTime);
        const data = event.data;
        resolve({
          success: data.success,
          stdout: data.stdout,
          stderr: data.stderr,
          execution_time_ms: elapsed,
          timed_out: false,
          status: data.status,
          disclaimer: 'Client-side isolated Web Worker (no network, no DOM)',
        });
      }
    };

    worker.onerror = (err) => {
      if (!isFinished) {
        isFinished = true;
        clearTimeout(timeoutTimer);
        worker.terminate();
        const elapsed = Math.round(performance.now() - startTime);
        resolve({
          success: false,
          stdout: '',
          stderr: `Worker error: ${err.message}`,
          execution_time_ms: elapsed,
          timed_out: false,
          status: 'RuntimeError',
          disclaimer: 'Client-side isolated Web Worker',
        });
      }
    };

    worker.postMessage('start');
  });
}

/**
 * Execute Python safely via the backend isolated sandbox.
 */
export async function executePython(code: string, stdin: string = ''): Promise<ExecutionResult> {
  const startTime = performance.now();
  try {
    const res = await fetch(`${BASE_URL}/api/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        language: 'python',
        code,
        stdin,
      }),
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => null);
      const msg = errBody?.detail?.message || `Execution endpoint returned HTTP ${res.status}`;
      return {
        success: false,
        stdout: '',
        stderr: msg,
        execution_time_ms: Math.round(performance.now() - startTime),
        timed_out: false,
        status: 'RuntimeError',
        disclaimer: 'Isolated subprocess sandbox',
      };
    }

    return await res.json();
  } catch (netErr: any) {
    return {
      success: false,
      stdout: '',
      stderr: `Failed to connect to backend execution runner: ${netErr.message}. Ensure FastAPI backend is running.`,
      execution_time_ms: Math.round(performance.now() - startTime),
      timed_out: false,
      status: 'InternalError',
      disclaimer: 'Local sandbox runner',
    };
  }
}
