# Security and sensitive reports

SpoolLens is an early offline tool for a narrow fixed-width text workflow. It is not a security boundary, a compliance product, or a guarantee of semantic or business correctness.

## Data handling

- Source reports are read-only; extraction rules do not modify source bytes
- The runtime uses Python's standard library and does not require a network service, cloud account, or telemetry
- CSV exports and their audit/provenance files can contain sensitive report values and source text
- An explicit exception ZIP includes a copy of the source, saved rule, candidate rows, and supporting evidence; treat it as sensitive as the original report
- Keep reports, rules, and exported evidence in an appropriately protected local folder, and review them before sharing

Only process files you are authorized to access. Review unfamiliar rules before using them; an explicitly ignored line will not become an output row. Preserve output evidence when auditing results. The conservative export checks do not determine whether a rule reflects your intended business meaning.

## Reporting a concern

Do not include real confidential reports, credentials, personal information, or private paths in a public issue. Reproduce ordinary bugs with minimal synthetic data.

For a security-sensitive finding, use GitHub's private **Report a vulnerability** option if it is available for this repository. If it is not available, open an issue requesting a private contact channel without including exploit details or sensitive data. No response-time or supported-version guarantee is made for this initial version.
