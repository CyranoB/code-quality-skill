// Default ESLint configuration for the code-quality skill
// Used when no project-level ESLint config is found
// Inspired by SonarQube "Sonar way" quality profile
//
// To override: create an eslint.config.js in your project
//
// Uses only core ESLint rules (no plugins required)

export default [
  {
    files: ["**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx"],
    rules: {
      // --- Possible errors ---
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

      // --- Best practices ---
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

      // --- Cyclomatic complexity ---
      "complexity": ["warn", 10],

      // --- Debug artifacts ---
      "no-console": "warn",
      "no-debugger": "error",
      "no-alert": "warn",
    },
  },
];
