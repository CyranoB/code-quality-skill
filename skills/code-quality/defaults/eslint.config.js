// Default ESLint configuration for the code-quality skill.
// Used by Lint and Architecture Review complexity checks on JS/TS targets via
// scripts/eslint-defaults.sh.
//
// NOTE: This config is NOT the general JS/TS fallback. Biome remains the
// fallback there (faster, native TS, no parser plugins needed).
// See SKILL.md "Default Configs" for the rationale.
//
// To override: create an eslint.config.js in your project.
//
// Inspired by SonarQube "Sonar way" quality profile. Core ESLint rules cover
// the common errors and style; eslint-plugin-sonarjs adds cognitive complexity
// and a small curated set of high-signal code smells.
//
// Security hotspots are intentionally NOT covered here; Security Scan's Semgrep
// pass owns that surface with deeper, cross-language coverage.

import sonarjs from 'eslint-plugin-sonarjs';
import tsParser from '@typescript-eslint/parser';

export default [
  // TS/TSX files: route through @typescript-eslint/parser so type annotations,
  // generics, interface declarations, etc. don't trigger a fatal parse error.
  // Without this, ESLint uses Espree and silently emits `{ruleId: null,
  // fatal: true}` messages — the skill's complexity parser ignores those by
  // ruleId, which would mean complexity checks report "clean" on real TS code.
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
  },
  {
    files: ["**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx", "**/*.ts", "**/*.tsx"],
    plugins: {
      sonarjs,
    },
    rules: {
      // --- Possible errors (core ESLint) ---
      "no-constant-condition": "error",
      "no-duplicate-case": "error",
      "no-empty": "warn",
      "no-extra-semi": "warn",
      "no-func-assign": "error",
      "no-inner-declarations": "error",
      "no-irregular-whitespace": "error",
      "no-unreachable": "error",
      "no-unsafe-finally": "error",
      "no-unused-vars": "warn",

      // --- Best practices (core ESLint) ---
      "eqeqeq": "warn",
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-wrappers": "error",
      "no-self-assign": "error",
      "no-self-compare": "error",
      "no-unused-expressions": "warn",
      "no-useless-catch": "warn",
      "no-with": "error",
      "prefer-const": "warn",
      "no-var": "warn",

      // --- Cyclomatic complexity (core ESLint) ---
      "complexity": ["warn", 10],

      // --- Cognitive complexity & code smells (sonarjs) ---
      // Threshold 15 matches SonarQube's "Sonar way" default. Severity in the
      // skill report is driven by the measured value (16-25 MAJOR, 26+ CRITICAL),
      // not by the "warn" level here. See references/severity-map.md.
      "sonarjs/cognitive-complexity": ["warn", 15],
      "sonarjs/no-duplicate-string": ["warn", { "threshold": 5 }],
      "sonarjs/no-identical-functions": "warn",
      "sonarjs/no-collapsible-if": "warn",
      "sonarjs/no-redundant-boolean": "warn",
      "sonarjs/prefer-immediate-return": "warn",

      // --- Debug artifacts ---
      "no-console": "warn",
      "no-debugger": "error",
      "no-alert": "warn",
    },
  },
];
