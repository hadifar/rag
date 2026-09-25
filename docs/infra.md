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

Not provisioned: the CI service principal itself (its Azure AD app registration and GitHub OIDC
federated credential are one-time setup outside this template) and the Postgres server behind
`DATABASE_URL` — not yet decided whether that's Azure Database for PostgreSQL or something else.

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
  --parameters databaseUrl=<...> openAiApiKey=<...> pineconeApiKey=<...> \
               langfusePublicKey=<...> langfuseSecretKey=<...>
```

`main.parameters.local.json` (gitignored) holds your real, deployment-specific values —
`main.parameters.example.json` stays a placeholder template in git; copy it to create your own
local file.

**Deploy:** same command with `az deployment group create` in place of `what-if`. Pass the five
secure params on the command line or via env-var substitution — never add them to either
parameters file that's committed.

**Why `--mode Complete`:** the default (`Incremental`) only adds/updates resources — anything
removed from the template, or orphaned by renaming a resource's `name:` property (Azure can't
rename resources in place; a new `name` means a new resource), is silently left behind and keeps
billing. `Complete` mode deletes anything in `<rg>` that isn't declared in `main.bicep`, so
redeploying after a rename or removal cleans up automatically. This assumes `<rg>` is used
exclusively for this app — `Complete` mode will delete anything else in it too, including
resources created outside this template. Always run `what-if` first to see exactly what a
`Complete` deploy would remove before applying it.
