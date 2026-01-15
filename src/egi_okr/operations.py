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
from .utils import colourise

def get_VOs_report(env):
    '''
        Returns reports of the list of VOs created and deleted in the reporting period
        Endpoint:
         * `/egi-reports/vo`
    '''

    start = (env['DATE_FROM'].replace("/", "-")) + "-01"
    end = (env['DATE_TO'].replace("/", "-")) + "-01"

    headers = {
         "Accept": "Application/json",
         "X-API-Key": env['OPERATIONS_API_KEY']
    }

    _url = env['OPERATIONS_SERVER_URL'] \
        + env['OPERATIONS_VOS_REPORT_PREFIX'] \
        + "/vo?" \
        + "start_date=" + start \
        + "&end_date=" + end \
        + "&format=json"

    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    curl = requests.get(url=_url, headers=headers, verify=verify_ssl)

    response = curl.json()
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
    

def get_VO_metadata(index, env, vo_name):
    '''
        Returns the 'acknowldegement' and the 'publicationUrl' metadata for a given VO
        Endpoint:
         * `/vo-idcard/{vo_name}/{_format}`
    '''

    headers = {
         "Accept": "Application/json",
         "X-API-Key": env['OPERATIONS_API_KEY']
    }

    publicationsURL = ""
    statement = ""

    _url = env['OPERATIONS_SERVER_URL'] \
            + env['OPERATIONS_VO_ID_CARD_PREFIX'] \
            + "/" + vo_name + "/" + env['OPERATIONS_FORMAT']
 
    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    curl = requests.get(url=_url, headers=headers, verify=verify_ssl)
    
    try:
        response = curl.json()
    except Exception:
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


def get_VO_stats(env, vo):
    '''
       Returns the statistics of the production VO with minimal information
    '''
    headers = {
         "Accept": "Application/json",
         "X-API-Key": env['OPERATIONS_API_KEY']
    }

    _url = env['OPERATIONS_SERVER_URL'] \
            + env['OPERATIONS_VO_LIST_PREFIX'] \
            + "/" + env['OPERATIONS_FORMAT']

    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    curl = requests.get(url=_url, headers=headers, verify=verify_ssl)

    try:
        response = curl.json()
    except Exception:
        return []

    vo_stats = []
    index = 0

    if response:
        for details in response.get('data', []):
            if vo in details['name']:
               statement, publicationsURL, index = get_VO_metadata(index, env, details['name']) 
              
               members = details.get('members', "0")
               if members == "0.0": members = "0"
               
               membersTotal = details.get('membersTotal', "0")
               if membersTotal == "0.0": membersTotal = "0"

               vo_stats.append(
                    {"name": details['name'],
                     "scope": details['scope'],
                     "url": details['homeUrl'],
                     "users": get_VO_users(env, details['name']), 
                     "active_members": members,
                     "total_members" : membersTotal, 
                     "acknowledgement": statement,
                     "publicationsURL": publicationsURL})

            index = index + 1 

    return vo_stats


def get_VOs_stats(env):
    '''
       Returns the list of productions VOs with minimal information
    '''
    headers = {
         "Accept": "Application/json",
         "X-API-Key": env['OPERATIONS_API_KEY']
    }

    _url = env['OPERATIONS_SERVER_URL'] \
            + env['OPERATIONS_VO_LIST_PREFIX'] \
            + "/" + env['OPERATIONS_FORMAT']

    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    curl = requests.get(url=_url, headers=headers, verify=verify_ssl)

    try:
        response = curl.json()
    except Exception:
        return []

    vo_details = []
    index = 0

    if response:
        print(colourise("cyan", "\n[INFO]"), \
                "\tDownloading the VOs metadata from the EGI Operations Portal in progress..")
        print("\tThis operation may take few minutes. Please wait!\n")

        for details in response.get('data', []):
            print(colourise("green", "\n[LOG]"), \
            "[%d] Fetching metadata for the VO [%s] in progress.." %(index, details['name']))

            statement, publicationsURL, index = get_VO_metadata(index, env, details['name'])

            members = details.get('members', "0")
            if members == "0.0": members = "0"
            
            membersTotal = details.get('membersTotal', "0")
            if membersTotal == "0.0": membersTotal = "0"
            
            # Helper to create vo_detail dict
            vo_detail = {
                  "name": details['name'],
                  "scope": details['scope'],
                  "url": details['homeUrl'],
                  "users": get_VO_users(env, details['name']),    
                  "active_members": members, 
                  "total_members" : membersTotal, 
                  "acknowledgement": statement or "N/A",
                  "publicationsURL": publicationsURL or "N/A"
            }

            if env.get('LOG') == "DEBUG":
                print(json.dumps(vo_detail, indent=4))

            vo_details.append(vo_detail)    
            index = index + 1 

    return vo_details


def get_VO_users(env, vo):
    '''
       Returns the num. of users of the production VO in the specific period
    '''
    headers = {
         "Accept": "Application/json",
         "X-API-Key": env['OPERATIONS_API_KEY']
    }

    _url = env['OPERATIONS_SERVER_URL'] \
            + env['OPERATIONS_VOS_REPORT_PREFIX'] \
            + "/vo-users?start_date=" + env['DATE_FROM'].replace("/","-") \
            + "&end_date=" + env['DATE_TO'].replace("/","-") \
            + "&format=" + env['OPERATIONS_FORMAT'] \
            + "&vo=" + vo

    verify_ssl = env.get('SSL_CHECK', 'True') != 'False'
    curl = requests.get(url=_url, headers=headers, verify=verify_ssl)

    users = "0"
    if (curl.status_code == 200):
        try:
           response = curl.json()
           if response.get('users') is not None:
              users = response['users'][0]['total']
              # Logging omitted for brevity unless DEBUG
        except (requests.exceptions.JSONDecodeError, KeyError):
             pass
    
    return users
