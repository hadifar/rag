# Infra

## `infra/docker/`

`Dockerfile.backend`, `Dockerfile.frontend`, and `nginx.conf` — built by `docker-compose.yml`
for local dev. Not yet built/pushed anywhere by CI (see [limitation.md](limitation.md)).

## `infra/azure/`

`main.bicep` provisions the "Prod (Azure App Service)" setup described in
[engineering_design.md](engineering_design.md#secrets-management): a Key Vault, an Azure
Container Registry, an App Service for Containers with a system-assigned Managed Identity, RBAC
role assignments granting that identity read access to the vault (`Key Vault Secrets User`) and
pull access to the registry (`AcrPull`), and App Settings wired through Key Vault references —
no credentials stored on the resource itself, registry pulls included.

Not provisioned: actually building and pushing an image to the registry (nothing in CI does that
yet) and the Postgres server behind `DATABASE_URL`.

**Validate locally, without deploying:**

```bash
az bicep build --file infra/azure/main.bicep --stdout > /dev/null   # syntax/type check
az bicep lint --file infra/azure/main.bicep                          # static analysis
```

**Preview a real deployment** (talks to Azure, creates nothing):

```bash
az deployment group what-if \
  --resource-group <rg> \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/main.parameters.example.json \
  --parameters databaseUrl=<...> openAiApiKey=<...> pineconeApiKey=<...> \
               langfusePublicKey=<...> langfuseSecretKey=<...>
```

**Deploy:** same command with `az deployment group create` in place of `what-if`. Pass the five
secure params on the command line or via env-var substitution — never add them to
`infra/azure/main.parameters.example.json`, since that file is committed.
