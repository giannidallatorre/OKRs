#!/bin/bash

# Set workdir to repository root
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "${REPO_ROOT}"

# Check if config directory exists
CONFIG_DIR="${REPO_ROOT}/.config"
if [ ! -d "${CONFIG_DIR}" ]; then
    echo "Creating config directory..."
    mkdir -p "${CONFIG_DIR}"
fi

# Read and validate service account JSON
echo "Validating service account JSON..."
SA_FILE="${CONFIG_DIR}/service_account.json"

if [ -f "${SA_FILE}" ]; then
    echo "Using real service account..."
    SERVICE_ACCOUNT_JSON=$(cat "${SA_FILE}")
else
    echo "Using test credentials fallback..."
    SERVICE_ACCOUNT_JSON='{
           "type": "service_account",
           "project_id": "PLACEHOLDER",
           "private_key": "-----BEGIN PRIVATE KEY-----\nPLACEHOLDER\n-----END PRIVATE KEY-----",
           "client_email": "PLACEHOLDER@PROJECTID.iam.gserviceaccount.com"
    }'
fi

# Run workflow using local secrets file if it exists
SECRETS_ARG=""
if [ -f "act_setup/local.secrets" ]; then
    echo "Using secrets from act_setup/local.secrets..."
    SECRETS_ARG="--secret-file act_setup/local.secrets"
else
    echo "Warning: act_setup/local.secrets not found, using command-line placeholders..."
    SECRETS_ARG="--secret SERVICE_ACCOUNT_JSON='${SERVICE_ACCOUNT_JSON}' --secret JIRA_AUTH_TOKEN=test-token --secret OPERATIONS_API_KEY=test-api-key"
fi

echo "Running workflow..."
# Since all production defaults are now in the code,
# we only need to pass secrets and the job to run.
act --job update-sheet \
    ${SECRETS_ARG} \
    --bind