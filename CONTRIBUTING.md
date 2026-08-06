# Contributing

Thank you for helping improve `pskreporter-local`. Bug reports, feature ideas, documentation corrections, and focused code contributions are welcome.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report suspected vulnerabilities through the private process in [SECURITY.md](SECURITY.md), not through a public issue.

## Before opening an issue

- Search existing issues to avoid duplicates.
- Use the bug or feature issue form and provide the requested context.
- Remove callsigns, contact addresses, ADIF records, and other information you do not want to publish.
- Keep each issue focused on one problem or proposal.

For a substantial behavior or design change, open an issue before investing in an implementation so the approach can be discussed first.

## Development setup

Python 3.11 or newer is required. On macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
cp config.example.json config.json
.venv/bin/pytest
./run.sh
```

On Windows Command Prompt, create and activate the equivalent environment, then use:

```bat
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
copy config.example.json config.json
.venv\Scripts\python -m pytest
run.cmd
```

Replace the example callsign in your local `config.json`. That file is ignored by Git and must not be committed.

## Making a change

1. Create a focused branch from the latest `main`.
2. Keep the change small enough to review and avoid unrelated cleanup.
3. Add or update tests when behavior changes.
4. Update documentation when commands, configuration, or visible behavior changes.
5. Run the complete test suite with `.venv/bin/pytest` or `.venv\Scripts\python -m pytest`.
6. Open a pull request and complete its checklist.

The project favors a local-first design, a single application worker, bounded upstream requests, and clear failures over silent recovery. Preserve those constraints unless a proposed change explicitly revisits them.

## Pull requests

Explain what changed, why it changed, how it was tested, and any user-visible or security implications. Link related issues when applicable. Do not commit personal `config.json` values, ADIF logs, credentials, generated environments, or unrelated files.
