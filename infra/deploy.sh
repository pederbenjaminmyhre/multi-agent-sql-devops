#!/bin/bash
set -euo pipefail

RESOURCE_GROUP="rg-sql-devops-portfolio"
LOCATION="eastus"

echo "==> Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

echo "==> Deploying Bicep template..."
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters infra/parameters.json \
  --output none

echo "==> Getting ACR name..."
ACR_NAME=$(az acr list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv)
ACR_SERVER=$(az acr show -n "$ACR_NAME" --query "loginServer" -o tsv)

echo "==> Building and pushing container image..."
az acr build --registry "$ACR_NAME" --image sql-review-agent:latest .

echo "==> Updating container app with new image..."
az containerapp update \
  --name ca-sql-review \
  --resource-group "$RESOURCE_GROUP" \
  --image "${ACR_SERVER}/sql-review-agent:latest" \
  --output none

APP_URL=$(az containerapp show -n ca-sql-review -g "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)
echo ""
echo "==> Deployment complete!"
echo "    API URL: https://${APP_URL}"
echo "    Health:  https://${APP_URL}/health"
