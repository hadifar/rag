# Deploy to Azure

## Description

Provision or update the Azure environment with `infra/azure/main.bicep`. Diagram: [Azure deployment](../../diagrams/azure-deployment.md).

## Prerequisites

* A resource group used only by this app.
* A Postgres server with the `vector` extension allowed. On Azure Database for PostgreSQL, add `VECTOR` to `azure.extensions`.
* The CI service principal with a GitHub OIDC federated credential.

## Steps

1. Copy `infra/azure/main.parameters.example.json` to `infra/azure/main.parameters.local.json`.
2. Fill `main.parameters.local.json` with environment values.
3. If `llmProvider` is `azure_openai`, set `azureOpenAiEndpoint` and `azureOpenAiApiVersion`. The resource needs one chat deployment per model a user can pick, named after it (`gpt-6-luna`, `gpt-6-astra`, `gpt-6-sol`).
4. Validate: `az bicep build --file infra/azure/main.bicep --stdout > /dev/null`.
5. Lint: `az bicep lint --file infra/azure/main.bicep`.
6. Preview:

    ```bash
    az deployment group what-if \
      --resource-group <rg> \
      --mode Complete \
      --template-file infra/azure/main.bicep \
      --parameters infra/azure/main.parameters.local.json \
      --parameters databaseUrl=<...> llmApiKey=<...> \
                   langfusePublicKey=<...> langfuseSecretKey=<...> \
                   jwtSecret=<...>
    ```

7. Read the `what-if` output. Check every deletion.
8. Deploy: run the same command with `az deployment group create`.
9. Run `alembic upgrade head` against the production database.
10. Build and push images. See [Build and push images](../ci-cd/build-push-images.md).
11. Restart both Web Apps: `az webapp restart`.
12. Create an admin. See [Manage users](manage-users.md).
13. Load the knowledge base. See [Load the knowledge base](load-knowledge-base.md).

## Rules

* Always run `what-if` before `create`. `--mode Complete` deletes every resource in the group that `main.bicep` does not declare.
* Pass the five secure parameters on the command line. Do not commit them.
* Generate `jwtSecret` with `openssl rand -hex 32`.
* The App Service Plan must be Standard (`S1`) or higher. Private Endpoints need it.
