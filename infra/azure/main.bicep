targetScope = 'resourceGroup'

@description('Base name used to derive resource names (e.g. "rag").')
param appName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Globally unique Key Vault name (Key Vault names are a global DNS namespace).')
param keyVaultName string

@description('Globally unique Azure Container Registry name (letters/numbers only).')
param acrName string

@description('Globally unique Storage Account name (3-24 lowercase letters/numbers) for uploaded knowledge-base zips.')
@minLength(3)
@maxLength(24)
param kbStorageAccountName string

@description('Blob container the uploaded knowledge-base zips go in.')
param kbArchiveContainerName string = 'kb-archives'

@description('Container Registry SKU.')
param acrSku string = 'Basic'

@description('Backend image repository:tag within the registry, e.g. "rag-backend:1.2.3" — resolved against the provisioned ACR\'s login server, not a full registry URL.')
param backendContainerImageName string

@description('Frontend image repository:tag within the registry, e.g. "rag-frontend:1.2.3".')
param frontendContainerImageName string

@description('Object ID (not client/app ID) of the CI service principal that builds and pushes images — grants it AcrPush on the registry. From `az ad sp show --id <appId> --query id -o tsv`.')
param ciServicePrincipalObjectId string

@description('Linux App Service Plan SKU. Private Endpoints (see backendPrivateEndpoint below) require Standard or higher — Basic/Free/Shared don\'t support them.')
param appServicePlanSku string = 'S1'

@description('Address space for the VNet that isolates the backend Web App from the public internet.')
param vnetAddressPrefix string = '10.20.0.0/16'

@description('Subnet the frontend Web App regionally VNet-integrates into (delegated to Microsoft.Web/serverFarms).')
param integrationSubnetPrefix string = '10.20.0.0/24'

@description('Subnet holding the backend\'s Private Endpoint.')
param privateEndpointSubnetPrefix string = '10.20.1.0/24'

@secure()
param databaseUrl string

@description('Works for either llmProvider — an OpenAI key for "openai", an Azure OpenAI key for "azure_openai".')
@secure()
param llmApiKey string

@secure()
param langfusePublicKey string

@secure()
param langfuseSecretKey string

@description('HMAC key for signing access/refresh tokens — generate with `openssl rand -hex 32`.')
@secure()
param jwtSecret string

@description('Selects rag/config.py:LLMConfig\'s backend — keep in sync with that Literal.')
@allowed(['openai', 'azure_openai'])
param llmProvider string = 'openai'

@description('Non-secret app config — see rag/config.py:Settings for the full field list.')
param openAiModel string = 'gpt-4o-mini'
@description('Must be a text-embedding-3-* model — see rag/config.py:OpenAILLM.EMBEDDING_MODEL.')
param openAiEmbeddingModel string = 'text-embedding-3-small'
param azureOpenAiEndpoint string = ''
param azureOpenAiDeployment string = ''
@description('A text-embedding-3-* deployment — required when llmProvider is azure_openai.')
param azureOpenAiEmbeddingDeployment string = ''
param azureOpenAiApiVersion string = '2024-05-01-preview'
param langfuseEnabled bool = true
param langfuseHost string = 'https://cloud.langfuse.com'

var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var acrPushRoleId = '8311e382-0749-4cb8-b61a-304f252e45ec'
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

var secretsToStore = [
  { name: 'database-url', value: databaseUrl }
  { name: 'llm-api-key', value: llmApiKey }
  { name: 'langfuse-public-key', value: langfusePublicKey }
  { name: 'langfuse-secret-key', value: langfuseSecretKey }
  { name: 'jwt-secret', value: jwtSecret }
]

// The largest file each upload takes, in bytes: the backend enforces them, and the
// frontend's nginx caps the request bodies from them. One set, so the two agree.
var uploadLimitAppSettings = {
  UPLOADS__KB_MAX_BYTES: '20971520'
  UPLOADS__SKILL_MAX_BYTES: '51200'
  UPLOADS__SKILL_ARCHIVE_MAX_BYTES: '524288'
  UPLOADS__ATTACHMENT_MAX_BYTES: '5242880'
}

var llmAppSettings = llmProvider == 'azure_openai'
  ? {
      LLM__BACKEND: 'azure_openai'
      LLM__ENDPOINT: azureOpenAiEndpoint
      LLM__DEPLOYMENT: azureOpenAiDeployment
      LLM__EMBEDDING_DEPLOYMENT: azureOpenAiEmbeddingDeployment
      LLM__API_VERSION: azureOpenAiApiVersion
    }
  : {
      LLM__BACKEND: 'openai'
      LLM__MODEL: openAiModel
      LLM__EMBEDDING_MODEL: openAiEmbeddingModel
    }

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

// Keeps every knowledge-base zip uploaded through the Settings page (the backend's
// KB_STORAGE__BACKEND=azure_blob), so the index can be rebuilt from them. Access is
// Entra ID only: shared keys are off, so the only way in is the backend's Managed
// Identity (role below) or a person's own RBAC role — no account key to leak.
resource kbStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: kbStorageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    // Public endpoint, RBAC-only: the backend Web App has no outbound VNet integration,
    // so a private endpoint isn't reachable from it yet (see docs/limitation.md).
    publicNetworkAccess: 'Enabled'
  }

  resource blobService 'blobServices' = {
    name: 'default'
    properties: {
      // A deleted or overwritten archive can be restored for a week.
      deleteRetentionPolicy: {
        enabled: true
        days: 7
      }
    }

    resource kbArchives 'containers' = {
      name: kbArchiveContainerName
      properties: {
        publicAccess: 'None'
      }
    }
  }
}

// Isolates the backend from the public internet: the frontend reaches it only over
// this VNet (via regional VNet integration + the Private Endpoint below), so the
// backend's own public hostname stops resolving to anything and nginx's rate
// limiter — the only rate limiting in this stack — can't be bypassed by hitting the
// backend directly. See docs/limitation.md "Backend and frontend Web Apps talk to
// each other over their public hostnames".
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${appName}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
  }

  resource integrationSubnet 'subnets' = {
    name: 'integration'
    properties: {
      addressPrefix: integrationSubnetPrefix
      delegations: [
        {
          name: 'webapp-delegation'
          properties: {
            serviceName: 'Microsoft.Web/serverFarms'
          }
        }
      ]
    }
  }

  resource privateEndpointSubnet 'subnets' = {
    name: 'private-endpoints'
    properties: {
      addressPrefix: privateEndpointSubnetPrefix
      // Private Endpoint NICs land directly in the subnet — no delegation, but
      // network policies (NSGs/route tables) must be enabled for them to apply.
      privateEndpointNetworkPolicies: 'Enabled'
    }
    dependsOn: [
      integrationSubnet
    ]
  }
}

// Lets anything integrated into (or linked to) the VNet resolve the backend's
// defaultHostName to its private endpoint IP instead of the public one.
resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.azurewebsites.net'
  location: 'global'
}

resource privateDnsZoneVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZone
  name: '${appName}-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
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
    // No public inbound path at all — the Private Endpoint below is the only way in.
    publicNetworkAccess: 'Disabled'
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerRegistry.properties.loginServer}/${backendContainerImageName}'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
    }
  }
}

// Gives the backend a private IP inside the VNet's private-endpoints subnet; combined
// with publicNetworkAccess: 'Disabled' above, this is the only network path to it.
resource backendPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: '${appName}-backend-pe'
  location: location
  properties: {
    subnet: {
      id: vnet::privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: '${appName}-backend-plsc'
        properties: {
          privateLinkServiceId: backendWebApp.id
          groupIds: ['sites']
        }
      }
    ]
  }
}

resource backendPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: backendPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-azurewebsites-net'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
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
    // Regional VNet integration for outbound calls to the now-private backend.
    virtualNetworkSubnetId: vnet::integrationSubnet.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerRegistry.properties.loginServer}/${frontendContainerImageName}'
      // Without this, only RFC1918-destined traffic routes through the VNet, and
      // the backend's private endpoint IP (10.20.1.x, inside our own RFC1918 range)
      // would actually still match that — but relying on the address happening to
      // be private is fragile, so route everything through the VNet explicitly.
      vnetRouteAllEnabled: true
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

// "Storage Blob Data Contributor" on just the archive container (not the whole
// account) — the backend stores and reads uploaded zips with its own identity.
resource kbArchivesContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kbStorage::blobService::kbArchives.id, backendWebApp.id, storageBlobDataContributorRoleId)
  scope: kbStorage::blobService::kbArchives
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataContributorRoleId
    )
    principalId: backendWebApp.identity.principalId
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
  properties: union(
    {
      // Must match the port rag.config.Settings.PORT defaults to / the app binds.
      WEBSITES_PORT: '8000'

      DATABASE_URL: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/database-url/)'
      LLM__API_KEY: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/llm-api-key/)'
      OBSERVABILITY__PUBLIC_KEY: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/langfuse-public-key/)'
      OBSERVABILITY__SECRET_KEY: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/langfuse-secret-key/)'
      AUTH__JWT_SECRET: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/jwt-secret/)'

      // Previously wired to an unused LANGFUSE_ENABLED app setting Settings never read, so
      // this flag had no actual effect — it now genuinely selects the backend.
      OBSERVABILITY__BACKEND: langfuseEnabled ? 'langfuse' : 'logging'
      OBSERVABILITY__HOST: langfuseHost

      // Not secrets: DefaultAzureCredential picks up the Web App's Managed Identity.
      KB_STORAGE__BACKEND: 'azure_blob'
      KB_STORAGE__ACCOUNT_URL: kbStorage.properties.primaryEndpoints.blob
      KB_STORAGE__CONTAINER: kbArchiveContainerName
    },
    llmAppSettings,
    uploadLimitAppSettings
  )
  dependsOn: [
    keyVaultSecretsUserRoleAssignment
    keyVaultSecrets
  ]
}

// Tells nginx.conf.template where to proxy /api/*, and how large an upload's body may
// be (upload-limits.envsh) — no Key Vault access needed,
// the frontend has no secrets of its own. WEBSITES_PORT is omitted: nginx already
// listens on 80, App Service's default assumption for Linux containers.
resource frontendAppSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: frontendWebApp
  name: 'appsettings'
  properties: union(
    {
      BACKEND_URL: 'https://${backendWebApp.properties.defaultHostName}'
    },
    uploadLimitAppSettings
  )
}

output backendWebAppName string = backendWebApp.name
output backendWebAppHostName string = backendWebApp.properties.defaultHostName
output frontendWebAppName string = frontendWebApp.name
output frontendWebAppHostName string = frontendWebApp.properties.defaultHostName
output keyVaultUri string = keyVault.properties.vaultUri
output acrLoginServer string = containerRegistry.properties.loginServer
output kbStorageAccountName string = kbStorage.name
