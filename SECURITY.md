# Security Policy

## Supported versions

`pskreporter-local` is currently maintained as a single evolving release. Security fixes are applied to the latest version on the `main` branch. Older commits and independently modified copies are not supported.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue, discussion, or pull request.

Use GitHub's private vulnerability reporting instead:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability**.
4. Describe the affected version or commit, environment, reproduction steps, potential impact, and any suggested mitigation.

The maintainers will review the report privately, request more information when needed, and coordinate disclosure after a fix is available. Reporters may be credited in a published GitHub security advisory if they wish.

If the private reporting button is unavailable, open a public issue asking for a private security contact, but do not include vulnerability details in that issue.

## Deployment security boundary

This application has no built-in authentication and listens only on `127.0.0.1` by default. If its launcher is changed to accept network connections, restrict access to a trusted network with the host firewall. Add appropriate authentication and HTTPS controls before exposing it to the public internet.

Reports about unintended data exposure, unsafe request handling, dependency vulnerabilities, or ways to bypass the documented deployment boundary are welcome. The intentional absence of built-in authentication is documented behavior rather than an undisclosed vulnerability.
