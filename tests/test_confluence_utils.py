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

import unittest
from unittest.mock import patch, MagicMock

from egi_okr.utils import (
    _normalize_confluence_vo_name,
    _parse_confluence_customer_page,
    get_confluence_sla_vos,
)


class TestNormalizeConfluenceVoName(unittest.TestCase):
    """Unit tests for the VO name normalization helper."""

    def test_plain_vo_name_unchanged(self):
        self.assertEqual(_normalize_confluence_vo_name("vo.pangeo.eu"), "vo.pangeo.eu")

    def test_url_format_extracted(self):
        url = "https://operations-portal.egi.eu/vo/view/voname/youreact.vo.egi.eu"
        self.assertEqual(_normalize_confluence_vo_name(url), "youreact.vo.egi.eu")

    def test_url_format_extracted_simple(self):
        url = "https://operations-portal.egi.eu/vo/view/voname/vo.aneris.eu"
        self.assertEqual(_normalize_confluence_vo_name(url), "vo.aneris.eu")

    def test_placeholder_na_returns_none(self):
        self.assertIsNone(_normalize_confluence_vo_name("N/A"))

    def test_placeholder_see_table_returns_none(self):
        self.assertIsNone(_normalize_confluence_vo_name("See the table"))

    def test_placeholder_as_in_sla_returns_none(self):
        self.assertIsNone(_normalize_confluence_vo_name("As in the SLA agreement"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(_normalize_confluence_vo_name(""))

    def test_none_input_returns_none(self):
        self.assertIsNone(_normalize_confluence_vo_name(None))

    def test_sentence_with_spaces_returns_none(self):
        self.assertIsNone(_normalize_confluence_vo_name("See full table above"))

    def test_non_portal_url_returns_none(self):
        self.assertIsNone(_normalize_confluence_vo_name("https://example.com/some-vo"))


class TestParseConfluenceCustomerPage(unittest.TestCase):
    """Unit tests for the Confluence page body parser."""

    def _make_page_html(self, vo_name, sla_status):
        """Build a minimal Confluence Storage Format HTML body."""
        return f"""
        <ac:structured-macro ac:name="details">
          <ac:rich-text-body>
            <table class="wrapped">
              <tbody>
                <tr><th>Virtual Organization</th><td>{vo_name}</td></tr>
                <tr><th>SLA status</th>
                    <td><ac:structured-macro ac:name="status">
                          <ac:parameter ac:name="title">{sla_status}</ac:parameter>
                        </ac:structured-macro>
                    </td>
                </tr>
              </tbody>
            </table>
          </ac:rich-text-body>
        </ac:structured-macro>
        """

    def test_parses_finalized_plain_name(self):
        html = self._make_page_html("vo.pangeo.eu", "FINALIZED")
        vo, status = _parse_confluence_customer_page(html)
        self.assertEqual(vo, "vo.pangeo.eu")
        self.assertIn("FINALIZED", status)

    def test_parses_url_format_vo_name(self):
        url = "https://operations-portal.egi.eu/vo/view/voname/youreact.vo.egi.eu"
        html = self._make_page_html(url, "FINALIZED")
        vo, status = _parse_confluence_customer_page(html)
        self.assertEqual(vo, "youreact.vo.egi.eu")

    def test_parses_not_finalized_status(self):
        html = self._make_page_html("vo.test.eu", "STARTED")
        vo, status = _parse_confluence_customer_page(html)
        self.assertEqual(vo, "vo.test.eu")
        self.assertEqual(status, "STARTED")

    def test_placeholder_vo_yields_none(self):
        html = self._make_page_html("N/A", "FINALIZED")
        vo, _ = _parse_confluence_customer_page(html)
        self.assertIsNone(vo)

    def test_empty_body_yields_none(self):
        vo, status = _parse_confluence_customer_page("")
        self.assertIsNone(vo)
        self.assertIsNone(status)


class TestGetConfluenceSlaVos(unittest.TestCase):
    """Integration-level tests for get_confluence_sla_vos()."""

    BASE_ENV = {
        "CONFLUENCE_SERVER_URL": "https://confluence.example.com/",
        "CONFLUENCE_AUTH_TOKEN": "fake-token",
        "SSL_CHECK": "False",
    }

    def _make_page_html(self, vo_name, sla_status):
        return f"""
        <table><tr><th>Virtual Organization</th><td>{vo_name}</td></tr>
                   <tr><th>SLA status</th><td>{sla_status}</td></tr></table>"""

    @patch("egi_okr.utils.requests.get")
    def test_returns_finalized_vos(self, mock_get):
        # Mock 1: CQL search -> 2 customer pages
        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {
            "results": [{"id": "100", "title": "Customer: ALICE"},
                        {"id": "200", "title": "Customer: BOB"}],
        }
        # Mock 2+3: page bodies
        page1_resp = MagicMock()
        page1_resp.raise_for_status = MagicMock()
        page1_resp.json.return_value = {
            "body": {"storage": {"value": self._make_page_html("vo.alice.eu", "FINALIZED")}}
        }
        page2_resp = MagicMock()
        page2_resp.raise_for_status = MagicMock()
        page2_resp.json.return_value = {
            "body": {"storage": {"value": self._make_page_html("vo.bob.eu", "STARTED")}}
        }
        mock_get.side_effect = [search_resp, page1_resp, page2_resp]

        result = get_confluence_sla_vos(self.BASE_ENV)

        self.assertEqual(result, ["vo.alice.eu"])  # only FINALIZED

    @patch("egi_okr.utils.requests.get")
    def test_returns_empty_when_no_token(self, mock_get):
        env = {**self.BASE_ENV, "CONFLUENCE_AUTH_TOKEN": ""}
        result = get_confluence_sla_vos(env)
        self.assertEqual(result, [])
        mock_get.assert_not_called()

    @patch("egi_okr.utils.requests.get")
    def test_returns_empty_on_api_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        result = get_confluence_sla_vos(self.BASE_ENV)
        self.assertEqual(result, [])

    @patch("egi_okr.utils.requests.get")
    def test_normalizes_url_format_vo_names(self, mock_get):
        url_vo = "https://operations-portal.egi.eu/vo/view/voname/youreact.vo.egi.eu"
        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {"results": [{"id": "300", "title": "Customer: YouReact"}]}
        page_resp = MagicMock()
        page_resp.raise_for_status = MagicMock()
        page_resp.json.return_value = {
            "body": {"storage": {"value": self._make_page_html(url_vo, "FINALIZED")}}
        }
        mock_get.side_effect = [search_resp, page_resp]

        result = get_confluence_sla_vos(self.BASE_ENV)
        self.assertEqual(result, ["youreact.vo.egi.eu"])


if __name__ == "__main__":
    unittest.main()
