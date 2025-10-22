#!/bin/bash

###################################################
# E G I ** A C C O U N T I N G ** S E T T I N G S #
###################################################

# Server URL
export ACCOUNTING_SERVER_URL="https://accounting.egi.eu"

# Scope: 'cloud' for Cloud Compute, 'egi' for High-Throughput Compute
export ACCOUNTING_SCOPE="egi"

# Metrics for scope=cloud: 'sum_elap_processors', 'mem-GByte', 'vm_num', 'sum_elap', 'cost', 'net_in', 'net_out', 'disk', 'processors'
# Metrics for scope=grid: 'elap_processors', 'njobs', 'normcpu', 'sumcpu', 'normelap', 'normelap_processors', 'sumelap', 'cpueff'
export ACCOUNTING_METRIC="elap_processors"

# Local Job Selector: 'onlyinfrajobs', 'localinfrajobs', 'onlylocaljobs'
export ACCOUNTING_LOCAL_JOB_SELECTOR="onlyinfrajobs"

# VO Group Selector: 'egi'
export ACCOUNTING_VO_GROUP_SELECTOR="egi"

# Data Selector: 'JSON', 'CSV'
export ACCOUNTING_DATA_SELECTOR="JSON"

# Date range
export DATE_FROM="2022/07"
export DATE_TO="2022/09"

###########################################################
# G O O G L E ** S P R E A D S H E E T ** S E T T I N G S #
###########################################################

# Service account configuration
# export SERVICE_ACCOUNT_FILE="${PWD}/.config/service_account.json"

# Google Sheets settings
#export "SERVICE_ACCOUNT_PATH": "${workspaceFolder}/",
#export "SERVICE_ACCOUNT_FILE": "${workspaceFolder}/.config/service_account.json",
export SERVICE_ACCOUNT_PATH="${PWD}/.config"
export SERVICE_ACCOUNT_FILE="${SERVICE_ACCOUNT_PATH}/service_account.json"
export GOOGLE_SHEET_NAME="OKR_Reports_test"
export GOOGLE_CLOUD_WORKSHEET="OKR-integration-test"
export GOOGLE_HTC_WORKSHEET="OKR-integration-test-2"

# Logging level: INFO for no verbose logging, DEBUG for verbose logging
export LOG="INFO"
#export LOG="DEBUG"

# SSL check: True to enable, False to disable
export SSL_CHECK="True"
