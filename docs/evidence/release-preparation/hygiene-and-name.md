# Hygiene, dependency licenses, and name review

Checked 2026-10-07. This is a bounded repository review and naming screen, not a security guarantee or trademark/legal clearance.

## Current tree and history

Tracked source, documentation, evidence archives, synthetic reports and actual demo assets were reviewed. No credential/token/private-key, private-service URL, personal-email or real-business-data finding was identified. No virtual environment, cache, package-build junk, or unrelated generated file is intentionally tracked.

Historical anonymous cloud execution paths and internal process notes remain in older commits. Current copies were cleaned or explicitly redacted; history was not rewritten. There is no finding of leaked credentials. A future public-visibility decision must separately address whether to expose that historical metadata or use an authorized clean publication strategy. Preparation does not authorize either action.

The original fixtures, new unseen oracle, and demo reports are synthetic. The demo's ten PNGs have no metadata entries; its GIF has standard animation metadata only. Screen content derives from actual PTY output, with timing compression and captions disclosed. Recorded hashes and source-immutability/CSV checks match the captured runtime.

## Licenses

- Project and original synthetic fixtures: MIT
- Runtime: Python standard library only; no third-party Python runtime dependencies
- Build: setuptools, MIT
- Tests: standard-library unittest
- CI: official actions/checkout and actions/setup-python, MIT
- External capture tools: pexpect 4.9.0 (ISC), pyte 0.8.2 (LGPLv3), wcwidth 0.9.2 (MIT), Pillow 12.3.0 (MIT-CMU)
- Installed DejaVu Sans/Mono fonts: compatible Bitstream Vera/Arev notices and public-domain DejaVu changes

Capture tools and font files are not vendored or distributed as SpoolLens runtime. No asset/dependency licensing conflict was identified.

Sources: [setuptools](https://github.com/pypa/setuptools/blob/main/LICENSE), [Python](https://docs.python.org/3/license.html), [checkout](https://raw.githubusercontent.com/actions/checkout/v4/LICENSE), [setup-python](https://raw.githubusercontent.com/actions/setup-python/v5/LICENSE), [pexpect](https://pypi.org/pypi/pexpect/4.9.0/json), [pyte](https://pypi.org/pypi/pyte/0.8.2/json), [wcwidth](https://pypi.org/pypi/wcwidth/0.9.2/json), [Pillow](https://pypi.org/pypi/Pillow/12.3.0/json), [DejaVu](https://dejavu-fonts.github.io/License.html).

## Recommended repository name: spoollens

The short name matches the package and purpose. Current exact-name checks found no notable GitHub project or software/product collision; official PyPI JSON and simple-index endpoints returned 404. Indexed exact-name checks on USPTO/EUIPO/WIPO domains found no result, but this was not a full trademark-database, class, or jurisdiction search. No alternative name is needed on this bounded evidence, and no name has been reserved or changed.

Sources: [GitHub repository search API](https://api.github.com/search/repositories?q=spoollens+in:name&per_page=100), [PyPI metadata endpoint](https://pypi.org/pypi/spoollens/json), [PyPI simple endpoint](https://pypi.org/simple/spoollens/).
