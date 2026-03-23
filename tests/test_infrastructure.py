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

import unittest
from unittest.mock import patch, MagicMock
import json
from egi_okr.infrastructure import InfrastructureManager

class TestInfrastructure(unittest.TestCase):
    def setUp(self):
        self.env = {
            'SSL_CHECK': 'False',
            'LOG': 'DEBUG'
        }
        self.im = InfrastructureManager(env=self.env)

    @patch('egi_okr.infrastructure.requests.get')
    def test_get_sites_success(self, mock_get):
        # Mocking the JSON response from /sites/
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "1", "name": "SITE1"}]
        mock_get.return_value = mock_response
        
        sites = self.im.get_sites()
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]['name'], "SITE1")
        mock_get.assert_called_with("https://is.cloud.egi.eu/sites/", params=None, verify=False, timeout=30)

    @patch('egi_okr.infrastructure.requests.get')
    def test_get_site_images_success(self, mock_get):
        # Mocking the JSON response from /site/{site}/images
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"egi_id": "image1"}]
        mock_get.return_value = mock_response
        
        images = self.im.get_site_images("SITE1")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['egi_id'], "image1")
        mock_get.assert_called_with("https://is.cloud.egi.eu/site/SITE1/images", params=None, verify=False, timeout=30)

    @patch('egi_okr.infrastructure.requests.get')
    def test_get_all_images_with_params(self, mock_get):
        # Mocking the JSON response from /images/
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "img1"}]
        mock_get.return_value = mock_response
        
        images = self.im.get_all_images(vo_name="ops", only_egi_images=True)
        self.assertEqual(len(images), 1)
        mock_get.assert_called_with(
            "https://is.cloud.egi.eu/images/", 
            params={"only_egi_images": "true", "vo_name": "ops"}, 
            verify=False, 
            timeout=30
        )

    @patch('egi_okr.infrastructure.requests.get')
    def test_api_failure_logging(self, mock_get):
        # Mocking a connection error
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection Failed")
        
        # This should return an empty list and log/print error due to LOG=DEBUG
        sites = self.im.get_sites()
        self.assertEqual(sites, [])

    @patch('egi_okr.infrastructure.InfrastructureManager.get_site_images')
    @patch('egi_okr.infrastructure.InfrastructureManager.get_sites')
    def test_run_discovery(self, mock_sites, mock_images):
        # Setup mocks
        mock_sites.return_value = [{"name": "SITE1"}]
        mock_images.return_value = [{"egi_id": "IMG1"}]
        
        with patch('builtins.open', unittest.mock.mock_open()) as mocked_file:
            results = self.im.run_discovery(output_file="test.json")
            
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['images'][0]['egi_id'], "IMG1")
            mocked_file.assert_called()

if __name__ == '__main__':
    unittest.main()
