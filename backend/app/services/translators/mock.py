import time
import re
from typing import Optional, List, Tuple
from app.schemas.translation import Language, ProviderStatusResponse
from app.services.translators.base import (
    BaseTranslationProvider,
    TranslationResult,
    ProviderUnavailableError
)
from app.services.translators.policy import TRANSLATION_POLICY_VERSION


def _mask_strings(line: str) -> Tuple[str, List[str]]:
    """
    Safely extract and replace string literals with opaque tokens so that
    translation transformations do not alter string contents, typos, or quotes.
    """
    strings: List[str] = []
    pattern = re.compile(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)')

    def repl(m: re.Match) -> str:
        idx = len(strings)
        strings.append(m.group(0))
        return f"__STR_TOKEN_{idx}__"

    masked = pattern.sub(repl, line)
    return masked, strings


def _unmask_strings(line: str, strings: List[str]) -> str:
    """Restore verbatim string literals from opaque tokens."""
    for idx, s in enumerate(strings):
        line = line.replace(f"__STR_TOKEN_{idx}__", s)
    return line


def _python_to_javascript_faithful(code: str) -> str:
    """
    Strict faithful translation from Python to JavaScript.
    Preserves exact comments, string literals, identifiers, statement ordering,
    arithmetic expressions, and logical bugs/mistakes.
    """
    lines = code.split("\n")
    out_lines: List[str] = []
    indent_stack: List[int] = [0]

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            out_lines.append("")
            continue

        current_indent = len(raw_line) - len(raw_line.lstrip(" "))

        # Close blocks whose indentation level is strictly greater than current line
        while len(indent_stack) > 1 and current_indent < indent_stack[-1]:
            indent_stack.pop()
            indent_str = " " * (indent_stack[-1] if len(indent_stack) > 1 else 0)
            out_lines.append(f"{indent_str}}}")

        # Separate comment from code
        masked_code, str_tokens = _mask_strings(raw_line)
        comment_part = ""
        code_part = raw_line

        if "#" in masked_code:
            hash_idx = masked_code.index("#")
            masked_code_part = masked_code[:hash_idx]
            masked_comment_part = masked_code[hash_idx:]
            code_part = _unmask_strings(masked_code_part, str_tokens)
            comment_text = _unmask_strings(masked_comment_part, str_tokens)
            # Adapt delimiter: '#' -> '//' preserving exact text
            comment_part = "//" + comment_text[1:]
        else:
            code_part = raw_line

        code_stripped = code_part.strip()
        leading_space = " " * current_indent

        if not code_stripped:
            # Comment-only line
            out_lines.append(leading_space + comment_part.strip())
            continue

        # Translate code statement while protecting string tokens
        masked_line, line_str_tokens = _mask_strings(code_stripped)

        # Python block patterns
        m_def = re.match(r'^def\s+([a-zA-Z_]\w*)\s*\((.*?)\)\s*:$', masked_line)
        m_async_def = re.match(r'^async\s+def\s+([a-zA-Z_]\w*)\s*\((.*?)\)\s*:$', masked_line)
        m_class = re.match(r'^class\s+([a-zA-Z_]\w*)(?:\((.*?)\))?\s*:$', masked_line)
        m_if = re.match(r'^if\s+(.*?)\s*:$', masked_line)
        m_elif = re.match(r'^elif\s+(.*?)\s*:$', masked_line)
        m_else = re.match(r'^else\s*:$', masked_line)
        m_while = re.match(r'^while\s+(.*?)\s*:$', masked_line)
        m_for_range = re.match(r'^for\s+([a-zA-Z_]\w*)\s+in\s+range\((.*?)\)\s*:$', masked_line)
        m_for_iter = re.match(r'^for\s+([a-zA-Z_]\w*)\s+in\s+(.*?)\s*:$', masked_line)
        m_try = re.match(r'^try\s*:$', masked_line)
        m_except = re.match(r'^except(?:\s+([a-zA-Z_]\w*)(?:\s+as\s+([a-zA-Z_]\w*))?)?\s*:$', masked_line)
        m_finally = re.match(r'^finally\s*:$', masked_line)

        is_block = False
        new_line = masked_line

        if m_def:
            name, args = m_def.group(1), m_def.group(2)
            new_line = f"function {name}({args}) {{"
            is_block = True
        elif m_async_def:
            name, args = m_async_def.group(1), m_async_def.group(2)
            new_line = f"async function {name}({args}) {{"
            is_block = True
        elif m_class:
            cname, base = m_class.group(1), m_class.group(2)
            ext = f" extends {base}" if base else ""
            new_line = f"class {cname}{ext} {{"
            is_block = True
        elif m_if:
            cond = m_if.group(1)
            # Adapt logical operators inside condition
            cond = re.sub(r'\band\b', '&&', cond)
            cond = re.sub(r'\bor\b', '||', cond)
            cond = re.sub(r'\bnot\s+', '!', cond)
            new_line = f"if ({cond}) {{"
            is_block = True
        elif m_elif:
            cond = m_elif.group(1)
            cond = re.sub(r'\band\b', '&&', cond)
            cond = re.sub(r'\bor\b', '||', cond)
            cond = re.sub(r'\bnot\s+', '!', cond)
            new_line = f"else if ({cond}) {{"
            is_block = True
        elif m_else:
            new_line = "else {"
            is_block = True
        elif m_while:
            cond = m_while.group(1)
            cond = re.sub(r'\band\b', '&&', cond)
            cond = re.sub(r'\bor\b', '||', cond)
            cond = re.sub(r'\bnot\s+', '!', cond)
            new_line = f"while ({cond}) {{"
            is_block = True
        elif m_for_range:
            var, rargs = m_for_range.group(1), m_for_range.group(2)
            rparts = [p.strip() for p in rargs.split(",")]
            if len(rparts) == 1:
                new_line = f"for (let {var} = 0; {var} < {rparts[0]}; {var}++) {{"
            elif len(rparts) == 2:
                new_line = f"for (let {var} = {rparts[0]}; {var} < {rparts[1]}; {var}++) {{"
            elif len(rparts) >= 3:
                new_line = f"for (let {var} = {rparts[0]}; {var} < {rparts[1]}; {var} += {rparts[2]}) {{"
            is_block = True
        elif m_for_iter:
            var, it = m_for_iter.group(1), m_for_iter.group(2)
            new_line = f"for (const {var} of {it}) {{"
            is_block = True
        elif m_try:
            new_line = "try {"
            is_block = True
        elif m_except:
            err_var = m_except.group(2) or "e"
            new_line = f"catch ({err_var}) {{"
            is_block = True
        elif m_finally:
            new_line = "finally {"
            is_block = True
        else:
            # Statement adaptations
            new_line = re.sub(r'\bprint\((.*)\)', r'console.log(\1)', new_line)
            new_line = re.sub(r'\braise\s+(.*)', r'throw \1', new_line)
            new_line = re.sub(r'\bself\.', 'this.', new_line)
            new_line = re.sub(r'\bTrue\b', 'true', new_line)
            new_line = re.sub(r'\bFalse\b', 'false', new_line)
            new_line = re.sub(r'\bNone\b', 'null', new_line)
            new_line = re.sub(r'\band\b', '&&', new_line)
            new_line = re.sub(r'\bor\b', '||', new_line)
            new_line = re.sub(r'\bnot\s+', '!', new_line)
            # Integer division a // b -> Math.floor(a / b)
            new_line = re.sub(r'([a-zA-Z0-9_\w]+)\s*//\s*([a-zA-Z0-9_\w]+)', r'Math.floor(\1 / \2)', new_line)

            # Semicolon insertion
            if not new_line.endswith(";") and not new_line.endswith("{") and not new_line.endswith("}"):
                new_line += ";"

        # Unmask string literals
        new_line = _unmask_strings(new_line, line_str_tokens)

        if comment_part:
            final_line = f"{leading_space}{new_line} {comment_part}"
        else:
            final_line = f"{leading_space}{new_line}"

        out_lines.append(final_line)

        if is_block:
            indent_stack.append(current_indent + 4)

    # Close any remaining open blocks at EOF
    while len(indent_stack) > 1:
        indent_stack.pop()
        indent_str = " " * (indent_stack[-1] if len(indent_stack) > 1 else 0)
        out_lines.append(f"{indent_str}}}")

    return "\n".join(out_lines)


def _javascript_to_python_faithful(code: str) -> str:
    """
    Strict faithful translation from JavaScript to Python.
    Preserves exact comments, string literals, identifiers, statement ordering,
    and logical bugs/mistakes.
    """
    lines = code.split("\n")
    out_lines: List[str] = []
    current_indent = 0

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            out_lines.append("")
            continue

        # Check for closing brace lines
        if stripped in ("}", "};"):
            current_indent = max(0, current_indent - 4)
            continue

        if stripped.startswith("}"):
            current_indent = max(0, current_indent - 4)
            stripped = stripped[1:].strip()
            if not stripped:
                continue

        # Separate comment from code
        masked_line, str_tokens = _mask_strings(stripped)
        comment_part = ""
        code_part = masked_line

        if "//" in masked_line:
            c_idx = masked_line.index("//")
            code_part = masked_line[:c_idx].strip()
            comment_text = masked_line[c_idx:]
            # Delimiter '//' -> '#' preserving exact text
            comment_part = "#" + comment_text[2:]

        leading_space = " " * current_indent

        if not code_part:
            # Comment-only line
            out_lines.append(leading_space + _unmask_strings(comment_part, str_tokens))
            continue

        if code_part.endswith(";"):
            code_part = code_part[:-1].strip()

        opens_block = False
        if code_part.endswith("{"):
            opens_block = True
            code_part = code_part[:-1].strip()

        # JS patterns
        m_func = re.match(r'^(?:async\s+)?function\s+([a-zA-Z_]\w*)\s*\((.*?)\)$', code_part)
        m_class = re.match(r'^class\s+([a-zA-Z_]\w*)(?:\s+extends\s+([a-zA-Z_]\w*))?$', code_part)
        m_if = re.match(r'^if\s*\((.*?)\)$', code_part)
        m_elif = re.match(r'^(?:else\s+if|elif)\s*\((.*?)\)$', code_part)
        m_else = re.match(r'^else$', code_part)
        m_while = re.match(r'^while\s*\((.*?)\)$', code_part)
        m_for_of = re.match(r'^for\s*\((?:const|let|var)\s+([a-zA-Z_]\w*)\s+of\s+(.*?)\)$', code_part)
        m_for_c = re.match(r'^for\s*\(let\s+([a-zA-Z_]\w*)\s*=\s*(.*?);\s*\1\s*<\s*(.*?);\s*\1(?:\+\+|\s*\+=\s*1)\)$', code_part)
        m_try = re.match(r'^try$', code_part)
        m_catch = re.match(r'^catch\s*(?:\(([a-zA-Z_]\w*)\))?$', code_part)
        m_finally = re.match(r'^finally$', code_part)

        if m_func:
            is_async = "async " if "async" in code_part.split()[:2] else ""
            name, args = m_func.group(1), m_func.group(2)
            new_line = f"{is_async}def {name}({args}):"
        elif m_class:
            cname, base = m_class.group(1), m_class.group(2)
            inh = f"({base})" if base else ""
            new_line = f"class {cname}{inh}:"
        elif m_if:
            cond = m_if.group(1)
            cond = re.sub(r'&&', 'and', cond)
            cond = re.sub(r'\|\|', 'or', cond)
            cond = re.sub(r'!(?!=)', 'not ', cond)
            new_line = f"if {cond}:"
        elif m_elif:
            cond = m_elif.group(1)
            cond = re.sub(r'&&', 'and', cond)
            cond = re.sub(r'\|\|', 'or', cond)
            cond = re.sub(r'!(?!=)', 'not ', cond)
            new_line = f"elif {cond}:"
        elif m_else:
            new_line = "else:"
        elif m_while:
            cond = m_while.group(1)
            cond = re.sub(r'&&', 'and', cond)
            cond = re.sub(r'\|\|', 'or', cond)
            cond = re.sub(r'!(?!=)', 'not ', cond)
            new_line = f"while {cond}:"
        elif m_for_of:
            var, it = m_for_of.group(1), m_for_of.group(2)
            new_line = f"for {var} in {it}:"
        elif m_for_c:
            var, start, stop = m_for_c.group(1), m_for_c.group(2), m_for_c.group(3)
            if start == "0":
                new_line = f"for {var} in range({stop}):"
            else:
                new_line = f"for {var} in range({start}, {stop}):"
        elif m_try:
            new_line = "try:"
        elif m_catch:
            err = m_catch.group(1) or "e"
            new_line = f"except Exception as {err}:"
        elif m_finally:
            new_line = "finally:"
        else:
            new_line = code_part
            # Declarations: let x = 1 -> x = 1
            new_line = re.sub(r'^(?:let|const|var)\s+([a-zA-Z_]\w*)\s*=', r'\1 =', new_line)
            # console.log -> print
            new_line = re.sub(r'\bconsole\.log\((.*)\)', r'print(\1)', new_line)
            # throw -> raise
            new_line = re.sub(r'\bthrow\s+(.*)', r'raise \1', new_line)
            # this. -> self.
            new_line = re.sub(r'\bthis\.', 'self.', new_line)
            # true, false, null, undefined
            new_line = re.sub(r'\btrue\b', 'True', new_line)
            new_line = re.sub(r'\bfalse\b', 'False', new_line)
            new_line = re.sub(r'\bnull\b', 'None', new_line)
            new_line = re.sub(r'\bundefined\b', 'None', new_line)
            # Logical operators
            new_line = re.sub(r'&&', 'and', new_line)
            new_line = re.sub(r'\|\|', 'or', new_line)
            new_line = re.sub(r'!(?!=)', 'not ', new_line)
            # Math.floor(a / b) -> a // b
            new_line = re.sub(r'Math\.floor\((.*?)\s*/\s*(.*?)\)', r'\1 // \2', new_line)

        new_line = _unmask_strings(new_line, str_tokens)

        if comment_part:
            c_text = _unmask_strings(comment_part, str_tokens)
            final_line = f"{leading_space}{new_line}  {c_text}" if new_line else f"{leading_space}{c_text}"
        else:
            final_line = f"{leading_space}{new_line}"

        out_lines.append(final_line)

        if opens_block:
            current_indent += 4

    return "\n".join(out_lines)


class MockTranslationProvider(BaseTranslationProvider):
    """
    Deterministic Mock Translation Provider adhering strictly to
    MTCB Translation Policy v1.0.0 (Faithful translation over code improvement).
    """
    def __init__(self, is_available: bool = True, model_name: str = "mock-faithful-v1"):
        self._is_available = is_available
        self._model_name = model_name

    @property
    def name(self) -> str:
        return "mock"

    def set_available(self, available: bool) -> None:
        self._is_available = available

    async def get_status(self) -> ProviderStatusResponse:
        if not self._is_available:
            return ProviderStatusResponse(
                provider="mock",
                available=False,
                model=self._model_name,
                details="Mock provider is configured to simulate an unavailable state.",
                setup_instructions="Set mock provider availability to True."
            )
        return ProviderStatusResponse(
            provider="mock",
            available=True,
            model=self._model_name,
            details=f"Mock faithful provider active (Policy v{TRANSLATION_POLICY_VERSION}).",
            setup_instructions=None
        )

    async def translate(
        self,
        source_lang: Language,
        target_lang: Language,
        code: str,
        instructions: Optional[str] = None
    ) -> TranslationResult:
        if not self._is_available:
            raise ProviderUnavailableError(
                message="Mock translation provider is offline or disabled.",
                setup_instructions="Enable mock provider availability in settings or tests."
            )

        start_time = time.perf_counter()

        warnings: List[str] = [
            f"Translated under MTCB Faithful Translation Policy v{TRANSLATION_POLICY_VERSION}.",
            "All comments, identifiers, string literals, and source code mistakes were preserved verbatim."
        ]
        explanation_items = [
            f"Faithful translation from {source_lang.value} to {target_lang.value}."
        ]

        if source_lang == Language.PYTHON and target_lang == Language.JAVASCRIPT:
            translated = _python_to_javascript_faithful(code)
            explanation_items.append("Converted Python syntax and control blocks to JavaScript syntax with braces.")
            explanation_items.append("Preserved comments (# -> //), strings, identifiers, and logic unchanged.")
        elif source_lang == Language.JAVASCRIPT and target_lang == Language.PYTHON:
            translated = _javascript_to_python_faithful(code)
            explanation_items.append("Converted JavaScript syntax and control blocks to Python indentation.")
            explanation_items.append("Preserved comments (// -> #), strings, identifiers, and logic unchanged.")
        else:
            translated = code
            explanation_items.append(f"Pass-through translation for {source_lang.value} -> {target_lang.value}.")

        if instructions:
            explanation_items.append(f"Considered constraints: '{instructions}'.")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return TranslationResult(
            translated_code=translated,
            explanation="\n".join(explanation_items),
            warnings=warnings,
            model=self._model_name,
            provider_name="mock",
            execution_time_ms=round(elapsed_ms, 2)
        )
