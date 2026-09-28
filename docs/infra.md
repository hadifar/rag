# Infra

## `infra/docker/`

`Dockerfile.backend`, `Dockerfile.frontend`, and `nginx.conf.template` — built by
`docker-compose.yml` for local dev. `nginx.conf.template`'s `proxy_pass` target is env-substituted
at container start from `BACKEND_URL` (nginx:alpine's built-in `/etc/nginx/templates/*.template`
handling), so the same image works against `docker-compose`'s `backend:8000` and against the
backend Web App's real hostname in Azure.

## `infra/azure/`

`main.bicep` provisions the "Prod (Azure App Service)" setup described in
[reference.md](reference.md#secrets-management): a Key Vault, an Azure
Container Registry, and two App Service for Containers Web Apps (backend + frontend, sharing one
Linux App Service Plan), each with its own system-assigned Managed Identity. RBAC role
assignments grant the backend's identity read access to the vault (`Key Vault Secrets User`),
both Web Apps' identities pull access to the registry (`AcrPull`), and a separate `AcrPush` grant
for a CI service principal (`ciServicePrincipalObjectId`). The backend's App Settings are wired
through Key Vault references — no credentials stored anywhere, registry pulls/pushes included.

**Network isolation:** the backend has `publicNetworkAccess: 'Disabled'` and is reachable only
through a Private Endpoint on a `private-endpoints` subnet; the frontend regionally VNet-integrates
into a separate `integration` subnet (`vnetRouteAllEnabled: true` so *all* its outbound traffic,
not just RFC1918-destined, routes through the VNet) and resolves the backend's
`defaultHostName` to that private IP via a `privatelink.azurewebsites.net` Private DNS Zone linked
to the VNet. Net effect: the backend's public hostname doesn't resolve to anything from the
internet — the only way to it is through the frontend's nginx. This requires the App Service Plan to be Standard tier or higher
(`appServicePlanSku` default bumped from `B1` to `S1` — Private Endpoints aren't supported on
Basic/Free/Shared).

**Knowledge-base archives:** a Storage Account (`kbStorageAccountName`, globally unique) with a
`kb-archives` blob container keeps every zip uploaded from the Settings page, so the index can be
rebuilt from them. Shared-key access is disabled, so it's Entra ID only: the backend's identity
gets `Storage Blob Data Contributor` on that one container, and its App Settings point
`KB_STORAGE__*` at it (no secret involved, `DefaultAzureCredential` uses the Managed Identity).
Blob soft delete keeps a deleted archive restorable for 7 days. The account keeps a public
endpoint (RBAC still applies) because the backend Web App has no outbound VNet integration yet —
see [limitation.md](limitation.md#infra--deployment).

Loading the knowledge base after a deploy: sign in as an admin (create one with
`rag create-user <email> --admin`, run where `DATABASE_URL` points at the production database)
and upload the zip under **Settings → Knowledge base**. To rebuild the index from the last upload
instead, run `rag ingest --latest` in the backend container (App Service SSH console).

Not provisioned: the CI service principal itself (its Azure AD app registration and GitHub OIDC
federated credential are one-time setup outside this template) and the Postgres server behind
`DATABASE_URL` (Key Vault secret `database-url`) — not yet decided whether that's Azure Database
for PostgreSQL or something else.

Not wired yet: `AUTH__JWT_SECRET` isn't in the backend's App Settings, and it's required, so a backend deployed from this template currently fails at boot. Whatever
Postgres gets provisioned also needs the `vector` extension allowed (on Azure Database for
PostgreSQL: add `VECTOR` to the `azure.extensions` server parameter) before `alembic upgrade head`. Nothing
runs `alembic upgrade head` on deploy either — see [limitation.md](limitation.md#infra--deployment).

**Validate locally, without deploying:**

```bash
az bicep build --file infra/azure/main.bicep --stdout > /dev/null   # syntax/type check
az bicep lint --file infra/azure/main.bicep                          # static analysis
```

**Preview a real deployment** (talks to Azure, creates nothing):

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

`main.parameters.local.json` (gitignored) holds your real, deployment-specific values —
`main.parameters.example.json` stays a placeholder template in git; copy it to create your own
local file. `llmApiKey` works for either `llmProvider` — an OpenAI key for `"openai"`, an Azure
OpenAI key for `"azure_openai"` (which also needs `azureOpenAiEndpoint`/`azureOpenAiDeployment`/
`azureOpenAiApiVersion` set in your parameters file).

**Deploy:** same command with `az deployment group create` in place of `what-if`. Pass the five
secure params on the command line or via env-var substitution — never add them to either
parameters file that's committed. Generate `jwtSecret` with `openssl rand -hex 32`; rotating it
invalidates every issued token, logging all users out.

**Why `--mode Complete`:** the default (`Incremental`) only adds/updates resources — anything
removed from the template, or orphaned by renaming a resource's `name:` property (Azure can't
rename resources in place; a new `name` means a new resource), is silently left behind and keeps
billing. `Complete` mode deletes anything in `<rg>` that isn't declared in `main.bicep`, so
redeploying after a rename or removal cleans up automatically. This assumes `<rg>` is used
exclusively for this app — `Complete` mode will delete anything else in it too, including
resources created outside this template. Always run `what-if` first to see exactly what a
`Complete` deploy would remove before applying it.
