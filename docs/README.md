# Documentation

## How-to guides

### Git

* [Create a branch](how-to/git/create-branch.md)
* [Write commits](how-to/git/write-commits.md)
* [Open a pull request](how-to/git/open-pull-request.md)

### Backend

* [Add or update a router](how-to/backend/add-router.md)
* [Add or update a service](how-to/backend/add-service.md)
* [Add or update an adapter](how-to/backend/add-adapter.md)
* [Add or update a repository](how-to/backend/add-repository.md)
* [Add or update a migration](how-to/backend/add-migration.md)
* [Add or update an SSE event](how-to/backend/add-sse-event.md)
* [Add or update configuration](how-to/backend/add-configuration.md)
* [Add or update  a secret](how-to/backend/add-secret.md)
* [Add or update an agent capability](how-to/backend/add-agent-capability.md)
* [Add or update an ingestion source](how-to/backend/add-ingestion-source.md)
* [Run backend tests](how-to/backend/run-tests.md)

### Frontend

* [Add a feature](how-to/frontend/add-feature.md)
* [Add a page](how-to/frontend/add-page.md)
* [Add a component](how-to/frontend/add-component.md)
* [Call a backend endpoint](how-to/frontend/call-backend-endpoint.md)
* [Load server data](how-to/frontend/load-server-data.md)
* [Add a type](how-to/frontend/add-type.md)
* [Run frontend tests](how-to/frontend/run-tests.md)

### Infrastructure

* [Run the local stack](how-to/infra/run-local-stack.md)
* [Manage users](how-to/infra/manage-users.md)
* [Load the knowledge base](how-to/infra/load-knowledge-base.md)
* [Deploy to Azure](how-to/infra/deploy-azure.md)

### CI/CD

* [Modify a workflow](how-to/ci-cd/modify-workflow.md)
* [Release the application](how-to/ci-cd/release.md)
* [Build and push images](how-to/ci-cd/build-push-images.md)
* [Run integration tests](how-to/ci-cd/run-integration-tests.md)

## Architecture

* [System overview](architecture/overview.md): request path, data, auth
* [Backend](architecture/backend.md): layers, agent, streaming, errors, config
* [Frontend](architecture/frontend.md): layers, state, types
* [Enforcement](architecture/enforcement.md): what is checked and where

## Limitations

* [Known gaps](limitations.md): what is not addressed yet

## Decisions

* [Architecture decisions](decisions/README.md)

## For humans

* [Local development tutorial](tutorials/local-development.md)
* [Contributing](../CONTRIBUTING.md)
* Visual diagrams:
  * [Architecture diagrams](diagrams/architecture.md): system overview, backend layers, frontend layers
  * [Agent graph](diagrams/agent-graph.md)
  * [Chat flow](diagrams/chat-turn.md)
  * [Auth flow](diagrams/auth-flow.md)
  * [Schema sync](diagrams/schema-sync.md)
  * [Azure deployment](diagrams/azure-deployment.md)
