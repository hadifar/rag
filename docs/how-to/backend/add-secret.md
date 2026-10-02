# Add a secret

## Description

Add a credential the backend reads. Use for API keys, passwords and signing keys.

## Steps

1. Add the field as `SecretStr` to the section module in `rag/config/`.
2. Read the value with `.get_secret_value()` only where the adapter needs it.
3. Add a placeholder to `.example.env`.
4. Add the real value to your `.env`.
5. Add a `@secure()` parameter and a Key Vault secret to `infra/azure/main.bicep`.
6. Reference the secret from the backend App Settings as a Key Vault reference.
7. Pass the value at deploy time on the command line. See [Deploy to Azure](../infra/deploy-azure.md).

## Rules

* Do not commit a secret value.
* Do not put a secret in `infra/azure/main.parameters.example.json`.
* In GitHub Actions, read a secret from `secrets`, not from the workflow file.
* After you rotate a Key Vault secret, restart the Web App. App Service caches resolved references.
