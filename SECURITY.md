# Security Policy

## Secrets and Evidence

Do not commit provider API keys, Clerk secrets, database URLs with passwords, `.env` files, private keys, frame dumps, or evidence bundles.

Slate is designed so users bring their own provider accounts:

- Local Ollama keeps sampled frames on the user's machine.
- NVIDIA and Anthropic lanes send sampled frames to those providers through the user's own account.
- Slate Cloud stores uploaded verdict JSON only. Verdict payloads can still contain shot IDs, model observations, manifest-derived metadata, and persona reports, so treat them as user data.

## Reporting Issues

Open a private security advisory or contact the maintainers directly for suspected credential exposure, data handling bugs, or vulnerabilities that should not be public before a fix exists.

## Maintainer Checklist

Before publishing a release:

1. Run tests and linters for the affected package.
2. Run a secret scan across the working tree.
3. Confirm `.env`, private keys, local databases, frame dumps, and evidence bundles are ignored.
4. Do not publish old private repo history unless it has been reviewed for historical secrets.
