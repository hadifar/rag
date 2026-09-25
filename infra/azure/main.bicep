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
