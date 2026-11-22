"""
MTCB Safe Code Execution Sandbox Service.
Executes code in isolated, resource-constrained subprocesses with strict timeouts,
empty environment variables (no access to secrets/API keys), and temporary scratchpads.
"""

import os
import sys
import time
import tempfile
import subprocess
from typing import Dict, Any, Optional

MAX_CODE_LENGTH = 32_768
MAX_INPUT_LENGTH = 8_192
MAX_OUTPUT_LENGTH = 16_384
DEFAULT_TIMEOUT_SECONDS = 3.0


def execute_python_code(code: str, stdin_data: str = "") -> Dict[str, Any]:
    """
    Execute Python code in an isolated, sandboxed subprocess:
    - python -I (isolated mode: ignores user environment variables and system site-packages)
    - Stripped environment dict containing ONLY minimal system variables (no secrets, no API keys)
    - Sterile temporary working directory
    - Hard timeout (default 3.0s)
    - Output length truncation to avoid DOS
    """
    if len(code) > MAX_CODE_LENGTH:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Code length exceeds security limit ({MAX_CODE_LENGTH} bytes).",
            "execution_time_ms": 0,
            "timed_out": False,
            "status": "SecurityRejection"
        }

    if len(stdin_data) > MAX_INPUT_LENGTH:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Input length exceeds security limit ({MAX_INPUT_LENGTH} bytes).",
            "execution_time_ms": 0,
            "timed_out": False,
            "status": "SecurityRejection"
        }

    # Sterile minimal environment - zero secrets, zero API keys
    safe_env = {
        "PYTHONIOENCODING": "utf-8",
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
        "PATH": os.environ.get("PATH", ""),
    }

    start_time = time.perf_counter()

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "snippet.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        cmd = [sys.executable, "-I", script_path]

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=temp_dir,
                env=safe_env,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            stdout, stderr = process.communicate(
                input=stdin_data,
                timeout=DEFAULT_TIMEOUT_SECONDS
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Output truncation
            if len(stdout) > MAX_OUTPUT_LENGTH:
                stdout = stdout[:MAX_OUTPUT_LENGTH] + "\n... [Output truncated: size limit exceeded]"
            if len(stderr) > MAX_OUTPUT_LENGTH:
                stderr = stderr[:MAX_OUTPUT_LENGTH] + "\n... [Error log truncated: size limit exceeded]"

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": process.returncode,
                "execution_time_ms": round(elapsed_ms, 2),
                "timed_out": False,
                "status": "Completed" if process.returncode == 0 else "RuntimeError"
            }

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {DEFAULT_TIMEOUT_SECONDS} seconds.",
                "exit_code": -1,
                "execution_time_ms": round(elapsed_ms, 2),
                "timed_out": True,
                "status": "Timeout"
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Sandbox execution error: {str(e)}",
                "exit_code": -1,
                "execution_time_ms": round(elapsed_ms, 2),
                "timed_out": False,
                "status": "InternalError"
            }
