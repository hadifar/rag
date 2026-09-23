// Codifies the "Prod (Azure App Service)" setup steps from docs/engineering_design.md's
// Secrets management section: Key Vault + Managed Identity + RBAC + App Service for
// Containers, with app config wired through Key Vault references instead of stored
// credentials. Provisions two Web Apps (backend + frontend, sharing one Linux App
// Service Plan) since a Managed Identity has nothing to attach to otherwise. Also
// provisions an Azure Container Registry, grants both Web Apps' identities AcrPull,
// and grants a CI service principal AcrPush (see ciServicePrincipalObjectId) — no
// registry admin credentials stored anywhere, same pattern as Key Vault access.
//
// Out of scope, supplied as inputs rather than provisioned here: the CI service
// principal itself (its Azure AD app registration + GitHub OIDC federated
// credential are set up once, outside this template) and the Postgres server
// behind DATABASE_URL (not yet decided whether that's Azure Database for
// PostgreSQL or something else).
//
// Known gap: infra/docker/nginx.conf hardcodes `proxy_pass http://backend:8000`,
// which only resolves inside the docker-compose network. The frontend Web App
// provisioned here won't be able to reach the backend Web App until nginx.conf's
// upstream is made configurable (e.g. env-substituted at container start) and
// pointed at the backend's actual hostname — not yet done.

targetScope = 'resourceGroup'

@description('Base name used to derive resource names (e.g. "rag-chatbot").')
param appName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Globally unique Key Vault name (Key Vault names are a global DNS namespace).')
param keyVaultName string

@description('Globally unique Azure Container Registry name (letters/numbers only).')
param acrName string

@description('Container Registry SKU.')
param acrSku string = 'Basic'

@description('Backend image repository:tag within the registry, e.g. "rag-backend:1.2.3" — resolved against the provisioned ACR\'s login server, not a full registry URL.')
param backendContainerImageName string

@description('Frontend image repository:tag within the registry, e.g. "rag-frontend:1.2.3".')
param frontendContainerImageName string

@description('Object ID (not client/app ID) of the CI service principal that builds and pushes images — grants it AcrPush on the registry. From `az ad sp show --id <appId> --query id -o tsv`.')
param ciServicePrincipalObjectId string

@description('Linux App Service Plan SKU.')
param appServicePlanSku string = 'B1'

@secure()
param databaseUrl string

@secure()
param openAiApiKey string

@secure()
param pineconeApiKey string

@secure()
param langfusePublicKey string

@secure()
param langfuseSecretKey string

@description('Non-secret app config — see rag/config.py:Settings for the full field list.')
param openAiModel string = 'gpt-4o-mini'
param pineconeDenseIndexName string
param pineconeSparseIndexName string
param pineconeCloud string
param pineconeRegion string
param pineconeDenseModel string
param pineconeSparseModel string
param pineconeNamespace string
param langfuseEnabled bool = true
param langfuseHost string = 'https://cloud.langfuse.com'

var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var acrPushRoleId = '8311e382-0749-4cb8-b61a-304f252e45ec'

var secretsToStore = [
  { name: 'database-url', value: databaseUrl }
  { name: 'openai-api-key', value: openAiApiKey }
  { name: 'pinecone-api-key', value: pineconeApiKey }
  { name: 'langfuse-public-key', value: langfusePublicKey }
  { name: 'langfuse-secret-key', value: langfuseSecretKey }
]

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
  }
}

resource keyVaultSecrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [
  for secret in secretsToStore: {
    parent: keyVault
    name: secret.name
    properties: {
      value: secret.value
    }
  }
]

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: acrSku
  }
  properties: {
    // Pulls authenticate via the Web App's Managed Identity (AcrPull role, below),
    // not registry admin credentials.
    adminUserEnabled: false
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${appName}-plan'
  location: location
  kind: 'linux'
  sku: {
    name: appServicePlanSku
  }
  properties: {
    reserved: true
  }
}

resource backendWebApp 'Microsoft.Web/sites@2023-12-01' = {
  name: '${appName}-backend'
  location: location
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerRegistry.properties.loginServer}/${backendContainerImageName}'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
    }
  }
}

resource frontendWebApp 'Microsoft.Web/sites@2023-12-01' = {
  name: '${appName}-frontend'
  location: location
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerRegistry.properties.loginServer}/${frontendContainerImageName}'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
    }
  }
}

// "Key Vault Secrets User" — read-only access to secret values, granted to the
// backend Web App's system-assigned identity (no credentials stored anywhere).
// Only the backend reads Key Vault secrets — the frontend is a static/nginx
// container with no config of its own.
resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, backendWebApp.id, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      keyVaultSecretsUserRoleId
    )
    principalId: backendWebApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// "AcrPull" — lets each Web App pull its image from the registry via its own
// identity, same no-stored-credentials pattern as Key Vault access above.
resource backendAcrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, backendWebApp.id, acrPullRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
    principalId: backendWebApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource frontendAcrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, frontendWebApp.id, acrPullRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
    principalId: frontendWebApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// "AcrPush" — lets the CI service principal (GitHub OIDC identity) push images it
// builds, without a registry admin password.
resource acrPushRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, ciServicePrincipalObjectId, acrPushRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPushRoleId
    )
    principalId: ciServicePrincipalObjectId
    principalType: 'ServicePrincipal'
  }
}

// App Service resolves "@Microsoft.KeyVault(...)" references into plain env vars
// before the container starts, via the identity granted above — Settings needs no
// code changes, it already reads config from os.environ.
resource appSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: backendWebApp
  name: 'appsettings'
  properties: {
    // Must match the port rag.config.Settings.PORT defaults to / the app binds.
    WEBSITES_PORT: '8000'
    CHECKPOINTER_BACKEND: 'postgres'

    DATABASE_URL: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/database-url/)'
    OPENAI_API_KEY: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/openai-api-key/)'
    PINECONE_API_KEY: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/pinecone-api-key/)'
    LANGFUSE_PUBLIC_KEY: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/langfuse-public-key/)'
    LANGFUSE_SECRET_KEY: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/langfuse-secret-key/)'

    OPENAI_MODEL: openAiModel
    PINECONE_DENSE_INDEX_NAME: pineconeDenseIndexName
    PINECONE_SPARSE_INDEX_NAME: pineconeSparseIndexName
    PINECONE_CLOUD: pineconeCloud
    PINECONE_REGION: pineconeRegion
    PINECONE_DENSE_MODEL: pineconeDenseModel
    PINECONE_SPARSE_MODEL: pineconeSparseModel
    PINECONE_NAMESPACE: pineconeNamespace
    LANGFUSE_ENABLED: string(langfuseEnabled)
    LANGFUSE_HOST: langfuseHost
  }
  dependsOn: [
    keyVaultSecretsUserRoleAssignment
    keyVaultSecrets
  ]
}

// Tells nginx.conf.template where to proxy /api/* — no Key Vault access needed,
// the frontend has no secrets of its own. WEBSITES_PORT is omitted: nginx already
// listens on 80, App Service's default assumption for Linux containers.
resource frontendAppSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: frontendWebApp
  name: 'appsettings'
  properties: {
    BACKEND_URL: 'https://${backendWebApp.properties.defaultHostName}'
  }
}

output backendWebAppName string = backendWebApp.name
output backendWebAppHostName string = backendWebApp.properties.defaultHostName
output frontendWebAppName string = frontendWebApp.name
output frontendWebAppHostName string = frontendWebApp.properties.defaultHostName
output keyVaultUri string = keyVault.properties.vaultUri
output acrLoginServer string = containerRegistry.properties.loginServer
