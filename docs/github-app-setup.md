# GitHub App setup for Agent Company

Use a GitHub App instead of customer personal access tokens.

## Recommended repository permissions

- **Metadata:** Read-only (required by GitHub)
- **Contents:** Read & write
- **Issues:** Read-only
- **Pull requests:** Read & write
- **Checks:** Read-only (optional now; useful for CI-aware delivery)
- **Actions:** Read-only (optional now; useful for workflow diagnostics)

Do not request Administration, Secrets, Members, or Organization administration permissions for the coding MVP.

## Installation scope

Install the App only on explicitly selected repositories. For production onboarding, store the installation id and allowed repository ids on the customer/organization record. Never accept a repository solely because its owner/name was supplied by the client; verify that the repository is visible to the installation token.

## Runtime secrets

Configure the control plane with:

```text
GITHUB_APP_ID=<app id>
GITHUB_APP_INSTALLATION_ID=<installation id>
GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app.pem
```

`GITHUB_APP_PRIVATE_KEY` is supported for development, but a secret-mounted file is preferred.

The private key must never be copied into a repository workspace, model prompt, Docker sandbox environment, application log, or database row.

## Authentication flow

1. Control plane signs a short-lived GitHub App JWT using the private key.
2. Control plane exchanges that JWT for an installation access token.
3. The installation token is kept in memory only and refreshed early.
4. Git/API operations use the installation token.
5. Sandbox containers receive neither the installation token nor the App private key.

## Commercial multi-tenant follow-up

The current MVP uses one configured `GITHUB_APP_INSTALLATION_ID`. The multi-tenant version must select an installation id per job/customer, verify repository membership for that installation, and record the installation/repository ids in the audit log before dispatching work.
