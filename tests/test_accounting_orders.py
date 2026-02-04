
import unittest
import datetime
from unittest.mock import patch, MagicMock
from egi_okr.accounting_orders import OrdersAccounting

class TestOrdersAccounting(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DATE_FROM': '2024/01',
            'DATE_TO': '2024/03',
            'LOG': 'DEBUG',
            'GOOGLE_SHEET_NAME': 'dummy',
            'GOOGLE_ORDERS_WORKSHEET': 'Orders',
            'JIRA_SERVER_URL': 'http://jira',
            'JIRA_AUTH_TOKEN': 'token',
            'SERVICE_ORDERS_PROJECTKEY': 'SO'
        }
        self.app = OrdersAccounting(self.env)

    def test_parse_service_name(self):
        details = '... "service":"Cloud Compute", ...'
        name = self.app.parse_service_name(details)
        self.assertEqual(name, "Cloud Compute")

    def test_process_orders(self):
        orders = [
            {'fields': {'customfield_10711': '"service":"Cloud Compute"'}},
            {'fields': {'customfield_10711': '"service":"Online Storage"'}}
        ]
        buckets = self.app.process_orders(orders)
        self.assertEqual(buckets["Cloud Compute"], 1)
        self.assertEqual(buckets["Online Storage"], 1)

    @patch('egi_okr.base_accounting.init_GWorkSheet')
    @patch('egi_okr.accounting_orders.get_service_orders')
    def test_run_flow(self, mock_get_orders, mock_init_sheet):
        mock_ws = MagicMock()
        mock_init_sheet.return_value = mock_ws
        
        # Mock headers & values for BaseAccounting positioning logic
        mock_ws.row_values.return_value = ['Service', '2023.10-12']
        mock_ws.get_all_values.return_value = [['Service', '2023.10-12']]
        
        mock_get_orders.return_value = [{'fields': {'customfield_10711': '"service":"Cloud Compute"'}}]
        
        self.app.run()
        
        # Verify batch update
        mock_ws.update_cells.assert_called()

if __name__ == '__main__':
    unittest.main()
