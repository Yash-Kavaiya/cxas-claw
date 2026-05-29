# Changelog

## [0.3.0] — 2026-05-29

### Added
- `cxclaw doctor` — health-check command: verifies cxas CLI, active profile,
  credentials (SA key / ADC), CXAS_OAUTH_TOKEN, dfcx_scrapi install, Python version.
- `cxclaw eval` — batch utterance evaluation from a YAML/JSON file.
  Supports `expected_contains` and `expected_intent` assertions per test case.
  `--fail-on-error` exits 1 on any failure (CI-friendly).
- `.github/workflows/ci.yml` — GitHub Actions CI across Python 3.10–3.13 + Ruff lint.
- `.github/workflows/publish.yml` — Trusted PyPI publish on GitHub release.
- `PyYAML>=6.0` added to runtime deps.

### Changed
- Version bumped to 0.3.0.
- Test suite expanded from 19 → 22 tests (doctor, eval_passes, eval_fails_on_error).

## [0.2.0] — 2026-05-28

### Added
- Full coverage of all 19 official `cxas` CLI commands via subprocess delegation.
- Entry point renamed `claw` → `cxclaw`.
- `invoke_without_command=True` — bare `cxclaw` shows ASCII banner + help.
- Profile system (`~/.cxas-claw/profiles/`), `cxclaw profile` subcommands.
- `cxclaw chat` — interactive multi-turn REPL.
- `cxclaw scratchpad` — single-turn test.
- `cxclaw mcp` — tools/invoke for Playbook MCP server.
- `cxclaw apps list/get`, `cxclaw insights` scorecard management.
- `cxclaw migrate dfcx`, `cxclaw trace` passthrough.

### Fixed
- `--display-name_prefix` underscore/hyphen bug in `cxclaw run` delegation.

## [0.1.0] — 2026-05-27

### Added
- Initial release: Click CLI skeleton, Rich renderer, Profile system,
  CXASClient with lazy dfcx_scrapi imports, ScratchpadSession, REPL, MCPClient.
  13 unit tests, all passing.
