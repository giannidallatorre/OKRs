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
    # Read the real service account file
    SERVICE_ACCOUNT_JSON=$(cat "${SA_FILE}")
else
    echo "Using test credentials..."
    # Use test credentials if file not found
    SERVICE_ACCOUNT_JSON='{
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nTEST_PRIVATE_KEY\n-----END PRIVATE KEY-----",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "test-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test@test-project.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }'
fi
# Run workflow
echo "Running workflow..."
act --job update-sheet \
    --secret SERVICE_ACCOUNT_JSON="${SERVICE_ACCOUNT_JSON}" \
    --secret GOOGLE_SHEET_NAME="test-sheet" \
    --secret JIRA_AUTH_TOKEN="test-token" \
    --bind