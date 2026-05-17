## Description
Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

## Type of change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactor (code cleanup or optimization)

## How Has This Been Tested?
Please describe the tests that you ran to verify your changes.

- [ ] **Unit Tests**: Ran `pytest tests/` and all passed.
- [ ] **Coverage**: Ensured coverage did not decrease (run `pytest --cov`).
- [ ] **Manual Verification**: Verified on local machine (Windows).

## Portability and Hardening
- [ ] **No Hardcoded Paths**: Confirmed no absolute paths (C:\, etc.) are in code.
- [ ] **No Hardcoded URLs**: Confirmed all URLs are in `config/endpoints.yaml`.
- [ ] **Secrets Redacted**: Verified no API keys or tokens are in logs or code.

## Checklist:
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] Any dependent changes have been merged and published in downstream modules
