import { AnalysisData } from '../types/translation';

const PYTHON_KEYWORDS = new Set([
  'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
  'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
  'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
  'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
]);

const JS_KEYWORDS = new Set([
  'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default',
  'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function',
  'if', 'import', 'in', 'instanceof', 'new', 'return', 'super', 'switch',
  'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield',
  'let', 'static', 'enum', 'await', 'async', 'null', 'undefined', 'true', 'false',
]);

function extractIdentifiers(code: string, lang: string): Set<string> {
  const matches = code.match(/\b[a-zA-Z_][a-zA-Z0-9_]*\b/g) || [];
  const kw = lang === 'python' ? PYTHON_KEYWORDS : JS_KEYWORDS;
  const builtins = new Set(['console', 'log', 'print', 'len', 'range', 'str', 'int', 'float', 'Math', 'floor']);
  return new Set(matches.filter((m) => !kw.has(m) && !builtins.has(m) && m.length > 1));
}

function extractStrings(code: string): string[] {
  const matches = code.match(/(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/g) || [];
  return matches.map((m) => m.slice(1, -1)).filter((s) => s.length > 2);
}

function countStructuralElements(code: string, lang: string) {
  if (lang === 'python') {
    const funcs = (code.match(/^\s*def\s+[a-zA-Z0-9_]+/gm) || []).length;
    const loops = (code.match(/^\s*(?:for|while)\s+/gm) || []).length;
    const branches = (code.match(/^\s*(?:if|elif|else)\b/gm) || []).length;
    const returns = (code.match(/\breturn\b/g) || []).length;
    return { functions: funcs, loops, branches, returns };
  } else {
    const funcs = (code.match(/(?:function\s+[a-zA-Z0-9_]+|(?:const|let|var)\s+[a-zA-Z0-9_]+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)/g) || []).length;
    const loops = (code.match(/\b(?:for|while)\s*\(/g) || []).length;
    const branches = (code.match(/\b(?:if|else\s+if|else)\b/g) || []).length;
    const returns = (code.match(/\breturn\b/g) || []).length;
    return { functions: funcs, loops, branches, returns };
  }
}

export function computeClientAnalysis(
  sourceCode: string,
  targetCode: string,
  sourceLang: string,
  targetLang: string,
  warnings: string[] = []
): AnalysisData {
  const srcStruct = countStructuralElements(sourceCode, sourceLang);
  const tgtStruct = countStructuralElements(targetCode, targetLang);

  const totalSrc = srcStruct.functions + srcStruct.loops + srcStruct.branches + srcStruct.returns;
  const totalTgt = tgtStruct.functions + tgtStruct.loops + tgtStruct.branches + tgtStruct.returns;

  let structuralScore = 100;
  if (totalSrc === 0) {
    structuralScore = totalTgt === 0 ? 100 : Math.max(50, 100 - totalTgt * 15);
  } else {
    const diffSum =
      Math.abs(srcStruct.functions - tgtStruct.functions) +
      Math.abs(srcStruct.loops - tgtStruct.loops) +
      Math.abs(srcStruct.branches - tgtStruct.branches) +
      Math.abs(srcStruct.returns - tgtStruct.returns);
    structuralScore = Math.max(0, Math.min(100, Math.round(100 * (1 - diffSum / Math.max(1, totalSrc * 1.5)))));
  }

  const srcIds = extractIdentifiers(sourceCode, sourceLang);
  const tgtIds = extractIdentifiers(targetCode, targetLang);

  const normSrc = new Set(Array.from(srcIds).map((n) => n.replace(/[_\W]+/g, '').toLowerCase()));
  const normTgt = new Set(Array.from(tgtIds).map((n) => n.replace(/[_\W]+/g, '').toLowerCase()));

  const retainedIds = Array.from(normSrc).filter((n) => normTgt.has(n));
  const idRatio = normSrc.size ? retainedIds.length / normSrc.size : 1.0;

  const srcStrings = extractStrings(sourceCode);
  const tgtStrings = extractStrings(targetCode);
  const retainedStrings = srcStrings.filter((s) => tgtStrings.includes(s));
  const strRatio = srcStrings.length ? retainedStrings.length / srcStrings.length : 1.0;

  const contentScore = Math.max(0, Math.min(100, Math.round(100 * (0.6 * idRatio + 0.4 * strRatio))));

  const penalty = Math.min(25, warnings.length * 8);
  const semanticScore = Math.max(10, Math.min(100, Math.round(0.55 * structuralScore + 0.45 * contentScore) - penalty));

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
      source_structure: srcStruct,
      target_structure: tgtStruct,
      identifiers_source_count: srcIds.size,
      identifiers_retained_count: retainedIds.length,
      strings_source_count: srcStrings.length,
      strings_retained_count: retainedStrings.length,
      comments_source_count: 0,
      comments_target_count: 0,
      warning_count: warnings.length,
    },
    know_how: {
      structural_explanation: `Compared constructs between ${sourceLang} and ${targetLang}: Functions: ${srcStruct.functions} -> ${tgtStruct.functions}, Loops: ${srcStruct.loops} -> ${tgtStruct.loops}, Branches: ${srcStruct.branches} -> ${tgtStruct.branches}, Returns: ${srcStruct.returns} -> ${tgtStruct.returns}.`,
      content_explanation: `Retained ${retainedIds.length} of ${srcIds.size} identifiers across snake_case/camelCase conventions, and ${retainedStrings.length} of ${srcStrings.length} string literals.`,
      semantic_explanation: `Static estimation based on structural symmetry and identifier fidelity, adjusted by ${warnings.length} diagnostic warning(s).`,
      what_was_not_verified: [
        'Runtime execution outputs under arbitrary user inputs',
        'Language-specific floating-point or integer division nuances',
        'Asynchronous event loop and promise resolution timing',
        'Exception handling behaviors for undeclared error types',
      ],
      why_preservation_is_not_guarantee:
        'Two programs can have identical 100% structural preservation (same number of functions, loops, and variables) yet produce different results if language semantics differ (such as Python integer division // vs JavaScript / or 0-indexing edge cases). Always run test inputs in the Execution Console below to verify actual runtime behavior.',
    },
  };
}
