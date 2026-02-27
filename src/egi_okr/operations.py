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
import os
import concurrent.futures
from .utils import colourise, get_checkin_access_token

def get_operations_headers(env):
    """Construct headers for Operations Portal API, supporting both X-API-Key and Bearer token."""
    access_token = get_checkin_access_token(env)
    if access_token:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
    
    api_key = env.get('OPERATIONS_API_KEY')
    if api_key:
        return {
             "Accept": "application/json",
             "X-API-Key": api_key
        }
    
    return {}

def get_VOs_report(env, session=None):
    '''
        Returns reports of the list of VOs created and deleted in the reporting period
        Endpoint:
         * `/egi-reports/vo`
    '''
    # ... (skipping some comments)
    if session is None: session = requests

    start = (env['DATE_FROM'].replace("/", "-")) + "-01"
    end = (env['DATE_TO'].replace("/", "-")) + "-01"

    headers = get_operations_headers(env)
    if not headers:
        logging.error("[ERROR] Missing credentials for Operations Portal API")
        return []

    # Use /egi-reports/vo as the correct endpoint
    _url = f"{env['OPERATIONS_SERVER_URL'].replace('/api', '')}/api/egi-reports/vo"
    params = {
        "start_date": start,
        "end_date": end,
        "format": "json"
    }

    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    try:
        curl = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        curl.raise_for_status()
        response = curl.json()
    except Exception as e:
        msg = f"{e}"
        if hasattr(e, 'response') and e.response is not None:
             msg += f"\nResponse: {e.response.text}"
        print(colourise("red", "[ERROR]"), f"Failed to fetch VO report: {msg}")
        return []

    VOs_report = []

    if response:
       for item in response.get('report', []):
            vos = []
            for vo_list in item.get('vos', []):
                # Join VO names if they are provided as a list.
                vo_name_joined = ' '.join(vo_list['vo']) if isinstance(vo_list.get('vo'), list) else str(vo_list.get('vo'))
                
                tmp = vo_name_joined
                if "Pending" in item['status']:
                    tmp += "(PE)"
                if "Deleted" in item['status']:
                    tmp += "(D)"
                if "Leaving" in item['status']:
                    tmp += "(L)"
                if "Production" in item['status']:
                    tmp += "(P)"
                vos.append(tmp)
            
            VOs_report.append({
                "status": item['status'],
                "count": item['count'],
                "vos": vos
            })

    return VOs_report
    

def get_VO_metadata(index, env, vo_name, session=None):
    '''
        Returns the 'acknowldegement' and the 'publicationUrl' metadata for a given VO
        Endpoint:
         * `/vo-idcard/{vo_name}/{_format}`
    '''
    if session is None: session = requests

    headers = get_operations_headers(env)
    # ...
    _url = f"{env['OPERATIONS_SERVER_URL']}{env['OPERATIONS_VO_ID_CARD_PREFIX']}/{vo_name}"
    params = {
        "format": env.get('OPERATIONS_FORMAT', 'json')
    }
 
    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    try:
        curl = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        curl.raise_for_status()
        response = curl.json()
    except Exception as e:
        if env.get('LOG') == "DEBUG":
            print(colourise("red", "[ERROR]"), f"Failed to fetch VO metadata for {vo_name}: {e}")
        return "N/A", "N/A", index

    if response:
       for details in response.get('data', []):
           # Fetch VO metadata using expected ID card structure.
           try:
               vo_ack_list = details['Vo'][6]['VoAcknowledgments']
               
               if vo_ack_list[1]['VoAcknowledgment'][1]['acknowledgment']:
                  statement = vo_ack_list[1]['VoAcknowledgment'][1]['acknowledgment']
               else:
                  statement = "N/A"

               if vo_ack_list[3]['VoAcknowledgment'][3]['publicationUrl']:
                  publicationsURL = vo_ack_list[3]['VoAcknowledgment'][3]['publicationUrl']
               else:
                  publicationsURL = "N/A"
           except (IndexError, KeyError):
               statement = "N/A"
               publicationsURL = "N/A"

    return statement, publicationsURL, index


def get_VOs_stats(env, session=None):
    '''
       Returns the list of productions VOs with minimal information
    '''
    # Check for cached data (valid for current reporting period)
    cache_file = f".cache/vos_stats_{env.get('DATE_FROM', '')}_{env.get('DATE_TO', '')}.json"
    
    # Ensure cache directory exists
    cache_dir = os.path.dirname(cache_file) or ".cache"
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                print(colourise("green", "\n[INFO]"), 
                      f"\tLoaded {len(cached_data)} VOs from cache (skipping API calls)")
                return cached_data
        except Exception as e:
            print(colourise("yellow", "[WARN]"), f"Failed to load cache: {e}")
            
    if session is None: session = requests
    headers = get_operations_headers(env)

    _url = f"{env['OPERATIONS_SERVER_URL']}{env['OPERATIONS_VO_LIST_PREFIX']}"
    params = {
        "format": env.get('OPERATIONS_FORMAT', 'json')
    }
    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    try:
        curl = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        curl.raise_for_status()
        response = curl.json()
    except Exception as e:
        msg = f"{e}"
        if hasattr(e, 'response') and e.response is not None:
             msg += f"\nResponse: {e.response.text}"
        print(colourise("red", "[ERROR]"), f"API failure fetching VOs list: {msg}")
        return []

    vo_details = []
    index = 0

    if response:
        print(colourise("cyan", "\n[INFO]"), \
                "\tDownloading the VOs metadata from the EGI Operations Portal in progress (Parallel)..")
        
        def fetch_worker(index, details):
            statement, publicationsURL, _ = get_VO_metadata(index, env, details['name'], session=session)
            # Fetch period-specific member counts (not current snapshot values)
            active_members, total_members = get_VO_period_members(env, details['name'], session=session)
            
            return {
                  "name": details['name'],
                  "scope": details['scope'],
                  "url": details['homeUrl'],
                  "users": get_VO_users(env, details['name'], session=session),    
                  "active_members": active_members, 
                  "total_members": total_members, 
                  "acknowledgement": statement or "N/A",
                  "publicationsURL": publicationsURL or "N/A"
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(fetch_worker, i, d) for i, d in enumerate(response.get('data', []))]
            for future in concurrent.futures.as_completed(futures):
                try:
                    vo_details.append(future.result())
                except Exception as e:
                    print(colourise("red", "[ERROR]"), f"Failed fetching VO: {e}")

    # Save to cache
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(vo_details, f)
        print(colourise("green", "\n[INFO]"), f"\tCached {len(vo_details)} VOs to {cache_file}")
    except Exception as e:
        print(colourise("yellow", "[WARN]"), f"Failed to save cache: {e}")

    return vo_details


def get_VO_period_members(env, vo_name, session=None):
    '''
       Returns period-specific active and total members for a VO.
       Aggregates the max values across the reporting period (more representative of actual usage).
       Uses the egi-reports/vo-users endpoint which provides daily/periodic snapshots.
    '''
    if session is None: 
        session = requests
    
    headers = get_operations_headers(env)
    
    start = (env['DATE_FROM'].replace("/", "-")) + "-01"
    end = (env['DATE_TO'].replace("/", "-")) + "-01"
    
    _url = f"{env['OPERATIONS_SERVER_URL'].replace('/api', '')}/api/egi-reports/vo-users"
    params = {
        "vo_name": vo_name,
        "start_date": start,
        "end_date": end,
        "format": env.get('OPERATIONS_FORMAT', 'json')
    }
    
    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    active_members_list = []
    total_members_list = []
    
    try:
        curl = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        curl.raise_for_status()
        response = curl.json()
        
        if response and isinstance(response, dict):
            # Collect all data points across the period
            if 'users' in response and isinstance(response['users'], list):
                for user_data in response['users']:
                    if user_data.get('vo') == vo_name or vo_name in str(user_data.get('vo', '')):
                        # Try to get numeric values
                        try:
                            active_val = int(user_data.get('registered', user_data.get('active', 0)))
                            total_val = int(user_data.get('total', 0))
                            active_members_list.append(active_val)
                            total_members_list.append(total_val)
                        except (ValueError, TypeError):
                            pass
        
        # Use max value from period (representative of peak usage/actual member count)
        active_members = str(max(active_members_list)) if active_members_list else "0"
        total_members = str(max(total_members_list)) if total_members_list else "0"
        
    except Exception as e:
        if env.get('LOG') == "DEBUG":
            print(colourise("yellow", "[WARN]"), f"Failed to fetch period members for {vo_name}: {e}")
        active_members = "0"
        total_members = "0"
    
    return active_members, total_members


def get_VO_users(env, vo, session=None):
    '''
       Returns the num. of users of the production VO in the specific period
    '''
    if session is None: session = requests
    headers = get_operations_headers(env)

    _url = f"{env['OPERATIONS_SERVER_URL'].replace('/api', '')}/api/egi-reports/vo-users"
    
    start = (env['DATE_FROM'].replace("/", "-")) + "-01"
    end = (env['DATE_TO'].replace("/", "-")) + "-01"
    
    params = {
        "vo_name": vo,
        "start_date": start,
        "end_date": end,
        "format": env.get('OPERATIONS_FORMAT', 'json')
    }
    
    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    users = "0"
    try:
        curl = session.get(url=_url, headers=headers, params=params, verify=verify_ssl)
        curl.raise_for_status()
        response = curl.json()
        if response.get('users') is not None and isinstance(response.get('users'), list):
              users = response['users'][0].get('total', '0')
    except Exception:
         pass
    
    return users
