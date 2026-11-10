"""
Strict Faithful Code Translation Benchmark Suite for MTCB.

Evaluates three orthogonal dimensions across 20 representative benchmark programs:
1. Content Fidelity: Preservation of comments, identifiers, string literals, and typos.
2. Behavioral Fidelity: Preservation of observable behavior, logical mistakes, and bugs without 'fixing'.
3. Target-Language Validity: Syntactic validity verified via ast.parse (Python) and node --check (JavaScript).

Target threshold: >= 90% overall and per-dimension fidelity.
"""

import ast
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Callable
import pytest

from app.schemas.translation import Language
from app.services.translators.mock import MockTranslationProvider
from app.services.translators.policy import TRANSLATION_POLICY_VERSION


@dataclass
class BenchmarkItem:
    item_id: str
    name: str
    category: str
    source_lang: Language
    target_lang: Language
    source_code: str
    # Required tokens/strings that must appear in translated output
    expected_comments: List[str] = field(default_factory=list)
    expected_strings: List[str] = field(default_factory=list)
    expected_identifiers: List[str] = field(default_factory=list)
    # Checks ensuring that the model did NOT 'fix' bugs or 'optimize'
    preserved_bug_markers: List[str] = field(default_factory=list)
    forbidden_fix_markers: List[str] = field(default_factory=list)
    # Optional execution verification on trusted isolated fixture
    expected_stdout: Optional[str] = None


BENCHMARK_SUITE: List[BenchmarkItem] = [
    # --------------------------------------------------------------------------
    # CATEGORY 1: Comments with typos and unusual punctuation
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_01_COMMENTS_TYPO",
        name="Comments with intentional typos and weird punctuation (Py -> JS)",
        category="Comments with typos & punctuation",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "# WRNINNG: do NOT fix this speling typo! ?? ::\n"
            "def calculate_sm(a, b):\n"
            "    # retun value beloww... !!\n"
            "    return a + b\n"
        ),
        expected_comments=["WRNINNG: do NOT fix this speling typo! ?? ::", "retun value beloww... !!"],
        expected_identifiers=["calculate_sm", "a", "b"],
    ),
    BenchmarkItem(
        item_id="JS2PY_01_COMMENTS_TYPO",
        name="Comments with intentional typos and weird punctuation (JS -> Py)",
        category="Comments with typos & punctuation",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "// ATTENSHUN: preserve ths punctuation ??? && !!!\n"
            "function compute_diffrnce(x, y) {\n"
            "    // calculat subtracshun here\n"
            "    return x - y;\n"
            "}\n"
        ),
        expected_comments=["ATTENSHUN: preserve ths punctuation ??? && !!!", "calculat subtracshun here"],
        expected_identifiers=["compute_diffrnce", "x", "y"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 2: Strings with spelling mistakes and unusual capitalization
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_02_STRINGS_TYPOS",
        name="String literals with typos and irregular casing (Py -> JS)",
        category="Strings with typos & capitalization",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def get_err_mesg():\n"
            '    msg = "Errror: unexpexted FoObAr condishun in data!"\n'
            "    print(msg)\n"
            "    return msg\n"
        ),
        expected_strings=['"Errror: unexpexted FoObAr condishun in data!"'],
        expected_identifiers=["get_err_mesg", "msg"],
    ),
    BenchmarkItem(
        item_id="JS2PY_02_STRINGS_TYPOS",
        name="String literals with typos and irregular casing (JS -> Py)",
        category="Strings with typos & capitalization",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function log_warnng() {\n"
            '    let banner = "FaTaL: missng cOnFiG valuuu";\n'
            "    console.log(banner);\n"
            "    return banner;\n"
            "}\n"
        ),
        expected_strings=['"FaTaL: missng cOnFiG valuuu"'],
        expected_identifiers=["log_warnng", "banner"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 3: Incorrect conditions and logical bugs
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_03_INCORRECT_CONDITION",
        name="Preserve off-by-one bug (< instead of <=) (Py -> JS)",
        category="Incorrect conditions & logical bugs",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def check_limit(count):\n"
            "    # Bug: user wrote < 10 but needed <= 10. Must NOT be fixed!\n"
            "    if count < 10:\n"
            "        return True\n"
            "    return False\n"
        ),
        expected_identifiers=["check_limit", "count"],
        preserved_bug_markers=["count < 10"],
        forbidden_fix_markers=["count <= 10", "count <=10"],
    ),
    BenchmarkItem(
        item_id="JS2PY_03_INCORRECT_CONDITION",
        name="Preserve inverted logic bug (x > 0 instead of x >= 0) (JS -> Py)",
        category="Incorrect conditions & logical bugs",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function is_valid_index(idx) {\n"
            "    // Bug: idx > 0 excludes index 0! Must NOT be corrected\n"
            "    if (idx > 0) {\n"
            "        return true;\n"
            "    }\n"
            "    return false;\n"
            "}\n"
        ),
        expected_identifiers=["is_valid_index", "idx"],
        preserved_bug_markers=["idx > 0"],
        forbidden_fix_markers=["idx >= 0", "idx >=0"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 4: Duplicated and missing collection values
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_04_DUPLICATES",
        name="Preserve duplicated collection values (Py -> JS)",
        category="Duplicated collection values",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def get_raw_scores():\n"
            "    # Duplicates are intentional here\n"
            "    scores = [42, 42, 99, 99, 105]\n"
            "    return scores\n"
        ),
        expected_identifiers=["get_raw_scores", "scores"],
        preserved_bug_markers=["42, 42, 99, 99, 105"],
        forbidden_fix_markers=["Set(", "[42, 99, 105]"],
    ),
    BenchmarkItem(
        item_id="JS2PY_04_DUPLICATES",
        name="Preserve duplicated collection values (JS -> Py)",
        category="Duplicated collection values",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function get_dupe_fruits() {\n"
            '    let fruits = ["apple", "apple", "banana", "banana"];\n'
            "    return fruits;\n"
            "}\n"
        ),
        expected_identifiers=["get_dupe_fruits", "fruits"],
        preserved_bug_markers=['"apple", "apple", "banana", "banana"'],
        forbidden_fix_markers=["set(", '["apple", "banana"]'],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 5: Loops, nested conditions, functions, classes, and exceptions
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_05_LOOPS_NESTED",
        name="Nested loops, try/except, and break statements (Py -> JS)",
        category="Loops, nested blocks & exceptions",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def process_matrix(matrix):\n"
            "    total = 0\n"
            "    try:\n"
            "        for row in matrix:\n"
            "            for val in row:\n"
            "                if val < 0:\n"
            "                    break\n"
            "                total = total + val\n"
            "    except Exception as err:\n"
            "        print(err)\n"
            "    return total\n"
        ),
        expected_identifiers=["process_matrix", "matrix", "total", "row", "val", "err"],
        preserved_bug_markers=["break", "catch (err)"],
    ),
    BenchmarkItem(
        item_id="JS2PY_05_LOOPS_NESTED",
        name="Nested loops, try/catch, and continue statements (JS -> Py)",
        category="Loops, nested blocks & exceptions",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function scan_grid(grid) {\n"
            "    let count = 0;\n"
            "    try {\n"
            "        for (const line of grid) {\n"
            "            if (line == null) {\n"
            "                continue;\n"
            "            }\n"
            "            count = count + 1;\n"
            "        }\n"
            "    } catch (e) {\n"
            "        console.log(e);\n"
            "    }\n"
            "    return count;\n"
            "}\n"
        ),
        expected_identifiers=["scan_grid", "grid", "count", "line", "e"],
        preserved_bug_markers=["continue", "except Exception as e:"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 6: Input/output behavior
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_06_IO",
        name="Multiple print invocations (Py -> JS)",
        category="Input/Output mapping",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def display_summary(title, score):\n"
            "    print(title)\n"
            "    print(score)\n"
        ),
        expected_identifiers=["display_summary", "title", "score"],
        preserved_bug_markers=["console.log(title)", "console.log(score)"],
    ),
    BenchmarkItem(
        item_id="JS2PY_06_IO",
        name="Multiple console.log invocations (JS -> Py)",
        category="Input/Output mapping",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function show_status(phase, pct) {\n"
            "    console.log(phase);\n"
            "    console.log(pct);\n"
            "}\n"
        ),
        expected_identifiers=["show_status", "phase", "pct"],
        preserved_bug_markers=["print(phase)", "print(pct)"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 7: Arithmetic and language-specific operator semantics
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_07_ARITHMETIC",
        name="Integer division and exponentiation (Py -> JS)",
        category="Arithmetic & operator semantics",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def math_ops(n, d):\n"
            "    q = n // d\n"
            "    p = n ** 2\n"
            "    return q + p\n"
        ),
        expected_identifiers=["math_ops", "n", "d", "q", "p"],
        preserved_bug_markers=["Math.floor(n / d)", "** 2"],
    ),
    BenchmarkItem(
        item_id="JS2PY_07_ARITHMETIC",
        name="Math.floor integer division and exponentiation (JS -> Py)",
        category="Arithmetic & operator semantics",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function compute_ratios(a, b) {\n"
            "    let div = Math.floor(a / b);\n"
            "    let exp = a ** 3;\n"
            "    return div + exp;\n"
            "}\n"
        ),
        expected_identifiers=["compute_ratios", "a", "b", "div", "exp"],
        preserved_bug_markers=["a // b", "** 3"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 8: Unknown characters and error conditions
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_08_UNICODE",
        name="Unicode strings with accents and symbols (Py -> JS)",
        category="Unicode & character preservation",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def get_venue():\n"
            '    venue_name = "Café Müller ✨ (Zürich)"\n'
            "    return venue_name\n"
        ),
        expected_strings=['"Café Müller ✨ (Zürich)"'],
        expected_identifiers=["get_venue", "venue_name"],
    ),
    BenchmarkItem(
        item_id="JS2PY_08_UNICODE",
        name="Unicode strings with accents and symbols (JS -> Py)",
        category="Unicode & character preservation",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function get_greeting() {\n"
            '    let greeting = "¡Hola, señorita! 🎉";\n'
            "    return greeting;\n"
            "}\n"
        ),
        expected_strings=['"¡Hola, señorita! 🎉"'],
        expected_identifiers=["get_greeting", "greeting"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 9: Empty values, edge cases, and boundary conditions
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_09_BOUNDARY",
        name="Empty strings, zero, None, and empty collections (Py -> JS)",
        category="Boundary & edge cases",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def init_defaults():\n"
            '    empty_txt = ""\n'
            "    zero_num = 0\n"
            "    null_ref = None\n"
            "    empty_arr = []\n"
            "    return null_ref\n"
        ),
        expected_identifiers=["init_defaults", "empty_txt", "zero_num", "null_ref", "empty_arr"],
        preserved_bug_markers=['""', "0", "null", "[]"],
    ),
    BenchmarkItem(
        item_id="JS2PY_09_BOUNDARY",
        name="Empty strings, zero, null, and empty collections (JS -> Py)",
        category="Boundary & edge cases",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function reset_state() {\n"
            '    let s = "";\n'
            "    let z = 0;\n"
            "    let n = null;\n"
            "    let lst = [];\n"
            "    return n;\n"
            "}\n"
        ),
        expected_identifiers=["reset_state", "s", "z", "n", "lst"],
        preserved_bug_markers=['""', "0", "None", "[]"],
    ),

    # --------------------------------------------------------------------------
    # CATEGORY 10: Seemingly helpful corrections that would change behavior
    # --------------------------------------------------------------------------
    BenchmarkItem(
        item_id="PY2JS_10_NO_CORRECTIONS",
        name="Preserve redundant code and inverted boolean (Py -> JS)",
        category="Do NOT fix or optimize",
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        source_code=(
            "def check_active():\n"
            "    # User intentionally wrote not True instead of False\n"
            "    status = not True\n"
            "    return status\n"
            "    # Dead code: optimizer must NOT remove this!\n"
            "    dead_var = 999\n"
        ),
        expected_identifiers=["check_active", "status", "dead_var"],
        preserved_bug_markers=["!true", "dead_var = 999"],
        forbidden_fix_markers=["status = false;"],
    ),
    BenchmarkItem(
        item_id="JS2PY_10_NO_CORRECTIONS",
        name="Preserve redundant code and inverted boolean (JS -> Py)",
        category="Do NOT fix or optimize",
        source_lang=Language.JAVASCRIPT,
        target_lang=Language.PYTHON,
        source_code=(
            "function get_flag() {\n"
            "    // Inverted boolean condition\n"
            "    let flag = !true;\n"
            "    return flag;\n"
            "    // Unreachable dead code\n"
            "    let dead_code = 404;\n"
            "}\n"
        ),
        expected_identifiers=["get_flag", "flag", "dead_code"],
        preserved_bug_markers=["not True", "dead_code = 404"],
        forbidden_fix_markers=["flag = False"],
    ),
]


def validate_target_syntax(target_lang: Language, code: str) -> bool:
    """
    Validates whether the translated code is syntactically valid in the target language.
    Python: validated via ast.parse.
    JavaScript: validated via node --check.
    """
    if target_lang == Language.PYTHON:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    elif target_lang == Language.JAVASCRIPT:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        try:
            res = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
            return res.returncode == 0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    return False


def evaluate_content_fidelity(item: BenchmarkItem, translated: str) -> float:
    """
    Evaluates preservation of user comments, string literals, identifiers, and typos.
    Score: fraction of expected elements found in translated code (0.0 to 1.0).
    """
    total_checks = 0
    passed_checks = 0

    # 1. Comments
    for comment in item.expected_comments:
        total_checks += 1
        if comment in translated:
            passed_checks += 1

    # 2. String literals
    for string_lit in item.expected_strings:
        total_checks += 1
        # Strip outer quotes for flexible quote style matching
        inner = string_lit[1:-1]
        if inner in translated:
            passed_checks += 1

    # 3. Identifiers
    for ident in item.expected_identifiers:
        total_checks += 1
        if ident in translated:
            passed_checks += 1

    return (passed_checks / total_checks) if total_checks > 0 else 1.0


def evaluate_behavioral_fidelity(item: BenchmarkItem, translated: str) -> float:
    """
    Evaluates whether bugs, logical conditions, and un-optimized behaviors were preserved.
    Penalizes model if it applied 'helpful' fixes or stripped bugs.
    """
    total_checks = 0
    passed_checks = 0

    # Must contain bug markers
    for bug in item.preserved_bug_markers:
        total_checks += 1
        if bug in translated:
            passed_checks += 1

    # Must NOT contain forbidden 'fixed' variations
    for fix in item.forbidden_fix_markers:
        total_checks += 1
        if fix not in translated:
            passed_checks += 1

    return (passed_checks / total_checks) if total_checks > 0 else 1.0


@pytest.mark.asyncio
async def test_faithful_benchmark_suite():
    """
    Executes the 20-item faithful benchmark suite against the MockTranslationProvider.
    Computes individual and aggregate scores for Content Fidelity, Behavioral Fidelity,
    and Target-Language Validity, asserting >= 90% achievement.
    """
    provider = MockTranslationProvider()

    content_scores: List[float] = []
    behavioral_scores: List[float] = []
    validity_scores: List[float] = []

    print(f"\n{'='*75}")
    print(f"MTCB STRICT FAITHFUL TRANSLATION BENCHMARK (Policy v{TRANSLATION_POLICY_VERSION})")
    print(f"{'='*75}")
    print(f"Total benchmark items: {len(BENCHMARK_SUITE)}")
    print(f"Covering: 10 required domains in both Python -> JS and JS -> Python\n")

    for idx, item in enumerate(BENCHMARK_SUITE, start=1):
        res = await provider.translate(
            source_lang=item.source_lang,
            target_lang=item.target_lang,
            code=item.source_code
        )
        translated = res.translated_code

        # Dimension 1: Content Fidelity
        c_score = evaluate_content_fidelity(item, translated)
        content_scores.append(c_score)

        # Dimension 2: Behavioral Fidelity
        b_score = evaluate_behavioral_fidelity(item, translated)
        behavioral_scores.append(b_score)

        # Dimension 3: Target-Language Validity
        is_valid = validate_target_syntax(item.target_lang, translated)
        v_score = 1.0 if is_valid else 0.0
        validity_scores.append(v_score)

        status_icon = "PASS" if (c_score >= 0.9 and b_score >= 0.9 and v_score == 1.0) else "WARN"
        print(f"[{status_icon}] Item {idx:02d}: {item.item_id:<28} | Content: {c_score*100:5.1f}% | Behavior: {b_score*100:5.1f}% | Valid: {'YES' if is_valid else 'NO'}")

    avg_content = sum(content_scores) / len(content_scores)
    avg_behavior = sum(behavioral_scores) / len(behavioral_scores)
    avg_validity = sum(validity_scores) / len(validity_scores)
    overall_score = (avg_content + avg_behavior + avg_validity) / 3.0

    print(f"\n{'-'*75}")
    print("BENCHMARK RESULTS SUMMARY:")
    print(f"  1. Content Fidelity Score:         {avg_content*100:5.1f}%  (Target: >= 90.0%)")
    print(f"  2. Behavioral Fidelity Score:      {avg_behavior*100:5.1f}%  (Target: >= 90.0%)")
    print(f"  3. Target-Language Validity Score: {avg_validity*100:5.1f}%  (Target: >= 90.0%)")
    print(f"  -------------------------------------------------------------")
    print(f"  OVERALL BENCHMARK FIDELITY SCORE:   {overall_score*100:5.1f}%  (Target: >= 90.0%)")
    print(f"{'='*75}\n")

    # Rigorous assertions enforcing >= 90% threshold
    assert avg_content >= 0.90, f"Content fidelity score {avg_content*100:.1f}% is below 90% threshold!"
    assert avg_behavior >= 0.90, f"Behavioral fidelity score {avg_behavior*100:.1f}% is below 90% threshold!"
    assert avg_validity >= 0.90, f"Target-language validity score {avg_validity*100:.1f}% is below 90% threshold!"
    assert overall_score >= 0.90, f"Overall benchmark score {overall_score*100:.1f}% is below 90% threshold!"
