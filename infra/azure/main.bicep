// Codifies the "Prod (Azure App Service)" setup steps from docs/engineering_design.md's
// Secrets management section: Key Vault + Managed Identity + RBAC + App Service for
// Containers, with app config wired through Key Vault references instead of stored
// credentials. Provisions the App Service itself too, since a Managed Identity has
// nothing to attach to otherwise. Also provisions an Azure Container Registry and
// grants the Web App's identity AcrPull — no registry admin credentials stored
// anywhere, same pattern as Key Vault access.
//
// Out of scope, supplied as inputs rather than provisioned here: actually building
// and pushing an image to the registry (not wired into CI yet — see
// docs/limitation.md) and the Postgres server behind DATABASE_URL (not yet decided
// whether that's Azure Database for PostgreSQL or something else).

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

@description('Image repository:tag within the registry, e.g. "rag-backend:1.2.3" — resolved against the provisioned ACR\'s login server, not a full registry URL.')
param containerImageName string

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

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerRegistry.properties.loginServer}/${containerImageName}'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
    }
  }
}

// "Key Vault Secrets User" — read-only access to secret values, granted to the
// Web App's system-assigned identity (no credentials stored anywhere).
resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, webApp.id, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      keyVaultSecretsUserRoleId
    )
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// "AcrPull" — lets the Web App pull images from the registry via its identity,
// same no-stored-credentials pattern as Key Vault access above.
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, webApp.id, acrPullRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// App Service resolves "@Microsoft.KeyVault(...)" references into plain env vars
// before the container starts, via the identity granted above — Settings needs no
// code changes, it already reads config from os.environ.
resource appSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: webApp
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

output webAppName string = webApp.name
output webAppHostName string = webApp.properties.defaultHostName
output keyVaultUri string = keyVault.properties.vaultUri
output acrLoginServer string = containerRegistry.properties.loginServer
