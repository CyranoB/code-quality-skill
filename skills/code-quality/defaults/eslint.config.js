// Default ESLint configuration for the code-quality skill.
// Used by Workflow E (cognitive complexity) and Workflow I (complex_functions)
// on JS/TS targets via scripts/eslint-defaults.sh.
//
// NOTE: This config is NOT the JS/TS fallback for Workflows A/C/D — Biome
// remains the fallback there (faster, native TS, no parser plugins needed).
// See SKILL.md "Default Configs" for the rationale.
//
// To override: create an eslint.config.js in your project.
//
// Inspired by SonarQube "Sonar way" quality profile. Core ESLint rules cover
// the common errors and style; eslint-plugin-sonarjs adds cognitive complexity
// and a small curated set of high-signal code smells.
//
// Security hotspots are intentionally NOT covered here — Workflow J's Semgrep
// pass owns that surface with deeper, cross-language coverage.

import sonarjs from 'eslint-plugin-sonarjs';

export default [
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
