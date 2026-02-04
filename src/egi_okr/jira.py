#!/usr/bin/env python3
#
#  Copyright 2024 EGI Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import requests
import json
import logging
from .utils import colourise

def get_service_orders(env, session=None):
    ''' Return the list of Service Orders from the EOSC MarketPlace '''
    if session is None: session = requests

    start = (env['DATE_FROM'].replace("/", "-")) + "-01"
    end = (env['DATE_TO'].replace("/", "-")) + "-01"

    jql = f"project={env['SERVICE_ORDERS_PROJECTKEY']} AND created >= '{start}' AND created <= '{end}' ORDER BY key DESC, priority DESC, updated DESC"
    _url = f"{env['JIRA_SERVER_URL']}rest/api/latest/search"
    params = {
        "jql": jql,
        "maxResults": 1000
    }

    headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + env['JIRA_AUTH_TOKEN']
    }

    try:
        verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
        response = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        if response.status_code != 200:
            logging.error(f"[ERROR] Jira returned status {response.status_code}: {response.text}")
        response.raise_for_status()
        orders = response.json()
    except Exception as e:
        logging.error(f"[ERROR] Failed to fetch JIRA orders: {e}")
        return []

    if not isinstance(orders, dict) or 'issues' not in orders:
        logging.error(f"[ERROR] Invalid JIRA response: {orders}")
        return []

    return orders['issues']


def get_customers_complains(env, session=None):
    ''' Return the list of Customer Complains '''
    if session is None: session = requests

    complains = []
    _issues = []

    start = (env['DATE_FROM'].replace("/", "-")) + "-01"
    end = (env['DATE_TO'].replace("/", "-")) + "-01"

    jql = f"project={env['COMPLAINS_PROJECTKEY']} AND Complain=Yes AND created >= '{start}' AND created <= '{end}'"
    _url = f"{env['JIRA_SERVER_URL']}rest/api/latest/search"
    params = {
        "jql": jql,
        "maxResults": 10000
    }
    
    headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + env['JIRA_AUTH_TOKEN']
    }

    try:
        verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
        response = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        if response.status_code != 200:
            logging.error(f"[ERROR] Jira returned status {response.status_code}: {response.text}")
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logging.error(f"[ERROR] Failed to fetch JIRA complains: {e}")
        return []

    if 'issues' in data:
        for issue in data['issues']:
            # customfield_12409 = Complain
            # Check if field exists and value is Yes
            field = issue['fields'].get('customfield_12409')
            if field and "Yes" in field.get('value', ''):
               _issues.append(issue['key'])
    
    for issue_key in _issues:
        details = get_complain_details(env, issue_key, session=session)
        if details:
            complains.append(details)

    return complains


def get_complain_details(env, issue_key, session=None):
    ''' Retrieve the details for a given customer complain (issue) '''
    if session is None: session = requests

    _url = env['JIRA_SERVER_URL'] + "rest/api/latest/issue/" + issue_key

    headers = {
       "Accept": "Application/json",
       "Authorization": "Bearer " + env['JIRA_AUTH_TOKEN']
    }

    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    try:
        response = session.get(url=_url, headers=headers, verify=verify_ssl)
        issue_details = response.json()
    except Exception:
        return None

    status_name = issue_details['fields']['status']['name']
    if status_name:
       created_date = issue_details['fields']['created']
       _year = created_date[0:4]
       _month = created_date[5:7]

       # Check if within reporting period.
       if (int(_year) == int(env['DATE_TO'][0:4]) and \
           int(_month) <= int(env['DATE_TO'][5:7])):

           complain = {
             "Issue": issue_key,
             "URL": env['JIRA_SERVER_URL'] + "browse/" + issue_key,
             "Status": status_name.upper(),
             "Created": created_date[0:10],
             "Priority": issue_details['fields']['priority']['name'].upper(),
             "Assignee": issue_details['fields']['assignee']['displayName'] if issue_details['fields']['assignee'] else "Unassigned",
             "Email": issue_details['fields']['assignee']['emailAddress'] if issue_details['fields']['assignee'] else "N/A",
             "Complain": issue_details['fields']['customfield_12409']['value']
           }
           return complain

    return None


def get_sla_violations(env, session=None):
    ''' Retrieve the SLA violations in the reporting period ''' 
    if session is None: session = requests

    violations = []
    _issues = []
    
    start = (env['DATE_FROM'].replace("/", "-")) + "-01"
    end = (env['DATE_TO'].replace("/", "-")) + "-01"

    jql = f"project={env['VIOLATIONS_PROJECTKEY']} AND issueType='{env['ISSUETYPE']}' AND resolution=Unresolved AND created >= '{start}' AND created <= '{end}' ORDER BY priority DESC, updated DESC"
    _url = f"{env['JIRA_SERVER_URL']}rest/api/latest/search"
    params = {
        "jql": jql
    }

    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + env['JIRA_AUTH_TOKEN']
    }

    try:
        verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
        response = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        if response.status_code != 200:
            logging.error(f"[ERROR] Jira returned status {response.status_code}: {response.text}")
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    if 'issues' in data:
        for issue in data['issues']:
            if env['ISSUETYPE'] in (issue['fields']['issuetype']['name']):
               _issues.append(issue['key'])

    for issue_key in _issues:
        details = get_sla_violation_details(env, issue_key)
        if details:
            violations.append(details)

    return violations


def get_sla_violation_details(env, issue_key, session=None):
    ''' Retrieve the details for a given violation (issue) '''
    if session is None: session = requests

    _url = env['JIRA_SERVER_URL'] + "rest/api/latest/issue/" + issue_key

    headers = {
        "Accept": "Application/json",
        "Authorization": "Bearer " + env['JIRA_AUTH_TOKEN']
    }

    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    try:
        response = session.get(url=_url, headers=headers, verify=verify_ssl)
        issue_details = response.json()
    except Exception:
        return None

    status_name = issue_details['fields']['status']['name']
    if status_name:
       created_date = issue_details['fields']['created']
       _year = created_date[0:4]
       _month = created_date[5:7]

       if (int(_year) == int(env['DATE_TO'][0:4]) and \
           int(_month) <= int(env['DATE_TO'][5:7])):

           violation = {
                "Issue": issue_key,
                "URL": env['JIRA_SERVER_URL'] + "browse/" + issue_key,
                "Status": status_name.upper(),
                "Created": created_date[0:10],
                "Priority": issue_details['fields']['priority']['name'].upper()
           }
           return violation

    return None
