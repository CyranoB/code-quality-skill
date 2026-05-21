# Smoke tests for arch_review

Manual smoke tests to run before shipping. Unit tests cover correctness on synthetic data; these verify the workflow works on real repos.

## 1. Self-dogfood

The skill itself is a Python project. Run Workflow I on it.

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root . \
  --language python \
  --framework none \
  --skip-section dead_code \
  --skip-section complex_functions \
  | python3 -m json.tool | head -80
```

Expected:
- Exits 0
- Reports `files_scanned > 0`
- `cycles` section is `ok` (the skill has no circular deps)

## 2. Clean Python fixture

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/clean-py \
  --language python --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool
```

Expected: cycles `ok`, layering `ok`, hubs/gods/etc. all `ok`.

## 3. Violations Python fixture

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/violations-py \
  --language python --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool
```

Expected: cycles `found` (a↔b), layering `found` (domain → infrastructure), oversized_files `found` (oversized.py > 500 LoC).

## 4. Clean JS fixture (requires npm/npx)

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/clean-js \
  --language javascript --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool | head -60
```

Expected: cycles `ok`, layering `ok`.

## 5. Violations JS fixture

```bash
bash skills/code-quality/scripts/arch-review.sh \
  --project-root skills/code-quality/scripts/arch_review/fixtures/violations-js \
  --language javascript --framework none \
  --skip-section dead_code --skip-section complex_functions \
  | python3 -m json.tool | head -80
```

Expected: cycles `found` (a↔b), layering `found` (domain → infrastructure).

## 6. Performance check on a medium repo

Pick any local repo with ~300-1000 source files. Run with all sections including dead_code and complex_functions. Verify total elapsed time under 30 seconds (excluding cold-start npx download of knip).

## 7. Backward-compat check on Workflow F

After implementing Workflow I, run Workflow F against `fixtures/violations-py` and `fixtures/violations-js` exactly as before. Behavior must be unchanged. Workflow I MUST NOT regress Workflow F.
