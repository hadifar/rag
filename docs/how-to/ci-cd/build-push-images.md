# Build and push images

## Description

Build the backend and frontend images and push them to Azure Container Registry.

## Steps

1. Open **Actions → build-push** on GitHub.
2. Run the workflow on `master`.
3. Wait for both images: `rag-backend:<version>` and `rag-frontend:<version>`, plus `latest`.
4. Restart both Web Apps: `az webapp restart`. The Web Apps do not pull new images automatically.

## Rules

* The image tag is the `version` in `pyproject.toml`.
* The workflow needs `secrets.AZURE_CLIENT_ID`, `secrets.AZURE_TENANT_ID`, `secrets.AZURE_SUBSCRIPTION_ID` and `vars.ACR_NAME`.
