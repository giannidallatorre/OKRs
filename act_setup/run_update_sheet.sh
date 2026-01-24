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
           "project_id": "PLACEHOLDER_PROJECT_ID",
           "private_key_id": "PLACEHOLDER_KEY_ID",
           "private_key": "-----BEGIN PRIVATE KEY-----\nPLACEHOLDER_PRIVATE_KEY\n-----END PRIVATE KEY-----",
           "client_email": "PLACEHOLDER@PROJECTID.iam.gserviceaccount.com",
           "client_id": "PLACEHOLDER_CLIENT_ID",
           "auth_uri": "https://accounts.google.com/o/oauth2/auth",
           "token_uri": "https://oauth2.googleapis.com/token",
           "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
           "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/PLACEHOLDER@PROJECTID.iam.gserviceaccount.com",
           "universe_domain": "googleapis.com"
    }'
fi
# Run workflow using local secrets file if it exists, otherwise use placeholders
SECRETS_ARG=""
if [ -f "act_setup/local.secrets" ]; then
    echo "Using secrets from act_setup/local.secrets..."
    SECRETS_ARG="--secret-file act_setup/local.secrets"
else
    echo "Warning: act_setup/local.secrets not found, using placeholders..."
    SECRETS_ARG="--secret SERVICE_ACCOUNT_JSON=${SERVICE_ACCOUNT_JSON} --secret JIRA_AUTH_TOKEN=test-token --secret OPERATIONS_API_KEY=test-api-key"
fi

echo "Running workflow..."
act --job update-sheet \
    ${SECRETS_ARG} \
    --secret GOOGLE_SHEET_NAME="EGI_OKR_Test_Verify" \
    --var JIRA_PROJECT="EGISO" \
    --var SERVICE_ORDERS_PROJECTKEY="EGISO" \
    --var COMPLAINS_PROJECTKEY="IMSCC" \
    --var VIOLATIONS_PROJECTKEY="IMSSLA" \
    --var DATE_FROM="2024/01" \
    --var DATE_TO="2024/03" \
    --bind