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
from .utils import colourise

class InfrastructureManager:
    """Manager for EGI Infrastructure discovery using the new Cloud Info API."""
    
    DEFAULT_BASE_URL = "https://is.cloud.egi.eu"
    
    def __init__(self, env=None):
        self.env = env or {}
        self.base_url = self.env.get('INFRASTRUCTURE_API_URL', self.DEFAULT_BASE_URL).rstrip('/')
        self.verify_ssl = self.env.get('SSL_CHECK', 'True') != 'False'
        
    def _get(self, endpoint, params=None):
        """Helper for GET requests with error handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params, verify=self.verify_ssl, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if self.env.get('LOG') == "DEBUG":
                print(colourise("red", "[ERROR]"), f"API request failed to {url}: {e}")
            return None

    def get_sites(self):
        """Fetch the list of active sites."""
        return self._get("/sites/") or []

    def get_site_images(self, site_name):
        """Fetch images (templates) for a specific site."""
        endpoint = f"/site/{site_name}/images"
        return self._get(endpoint) or []

    def get_all_images(self, vo_name=None, only_egi_images=True):
        """Fetch all available images, optionally filtered by VO."""
        params = {"only_egi_images": str(only_egi_images).lower()}
        if vo_name:
            params["vo_name"] = vo_name
        return self._get("/images/", params=params) or []

    def run_discovery(self, output_file=None):
        """
        Runs a full discovery of sites and their images.
        If output_file is provided, saves results to JSON.
        """
        print(colourise("cyan", "[INFO]"), "Discovering active EGI FedCloud sites...")
        sites = self.get_sites()
        
        results = []
        for site in sites:
            name = site.get('name')
            print(colourise("gray", f"\tFetching images for {name}..."))
            images = self.get_site_images(name)
            site['images'] = images
            results.append(site)
            
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(colourise("green", "[SUCCESS]"), f"Infrastructure data saved to {output_file}")
            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Failed to save results: {e}")
                
        return results

from .base_accounting import BaseAccounting

class TemplatesAccounting(BaseAccounting):
    """Module for VM templates (images) accounting and reporting."""
    
    def __init__(self, env=None):
        super().__init__(env)
        self.inf_manager = InfrastructureManager(env=self.env)

    def run(self, dry_run=False):
        print("\n[*] Module: Infrastructure Templates")
        
        worksheet_key = 'GOOGLE_TEMPLATES_WORKSHEET'
        worksheet = self.init_worksheet(worksheet_key)
        
        # 1. Fetch data
        try:
            print(colourise("cyan", "[INFO]"), "Discovering active EGI FedCloud sites and images...")
            sites = self.inf_manager.get_sites()
            results = []
            site_metrics = {}
            total_images = 0
            
            for site in sites:
                name = site.get('name')
                images = self.inf_manager.get_site_images(name)
                total_images += len(images)
                site_metrics[name] = len(images)
                results.append({"name": name, "count": len(images)})
                
        except Exception as e:
            if dry_run or self.print_mode:
                 status = "(Print Mode)" if self.print_mode else "(Dry Run)"
                 print(colourise("red", f"\t{status}: ABORTED (Data fetch failed: {e})"))
            return

        # 2. Print or Write
        if dry_run or self.print_mode:
            status = "(Print Mode)" if self.print_mode else "(Dry Run)"
            print(colourise("green", f"\t{status}: Found {total_images} images across {len(sites)} sites"))
            for res in results:
                print(f"\t- {res['name']}: {res['count']} images")
            return
            
        if not worksheet:
            print(colourise("red", "[ABORT]"), f"Worksheet {worksheet_key} not found.")
            return

        # Setup Data for GSheet
        # We'll list each site as a row and the number of images as the value for the period
        labels = sorted(site_metrics.keys())
        data_map = site_metrics
        # Add a TOTAL row
        if labels:
            labels.append("TOTAL")
            data_map["TOTAL"] = total_images

        print(f"\tUpdating worksheet '{worksheet.title}'...")
        self.update_worksheet_data(
            worksheet, 
            row_labels=labels, 
            data_map=data_map, 
            first_col_label="Site"
        )

if __name__ == "__main__":
    TemplatesAccounting().run()
