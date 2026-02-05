
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

    @patch('egi_okr.base_accounting.init_GWorkSheet')
    @patch('egi_okr.accounting_orders.get_service_orders')
    def test_orders_data_not_empty_regression(self, mock_get_orders, mock_init_sheet):
        """
        Regression test: Ensure Orders module reports service counts correctly.
        
        This catches bugs where header initialization or sheet updates 
        fail to commit the order bucket counts.
        """
        mock_ws = MagicMock()
        mock_init_sheet.return_value = mock_ws
        
        # Mock realistic orders from JIRA
        mock_get_orders.return_value = [
            {'fields': {'customfield_10711': '"service":"Cloud Compute"'}},
            {'fields': {'customfield_10711': '"service":"Cloud Compute"'}},
            {'fields': {'customfield_10711': '"service":"Online Storage"'}},
            {'fields': {'customfield_10711': '"service":"Archive Storage"'}},
        ]
        
        # Mock worksheet state - simulate needing header initialization
        call_count = {'count': 0}
        def mock_get_all_values():
            call_count['count'] += 1
            if call_count['count'] == 1:
                return [[]]  # Empty, needs header init
            else:
                return [['Service', '2024.01-03']]
        
        mock_ws.get_all_values.side_effect = mock_get_all_values
        mock_ws.cell.return_value.value = None
        
        self.app.run()
        
        # REGRESSION CHECKS:
        # 1. Header should be initialized
        mock_ws.update.assert_called()
        
        # 2. Data should be written for service buckets
        mock_ws.update_cells.assert_called()
        cells = mock_ws.update_cells.call_args[0][0]
        
        # 3. Should have data for multiple service types
        # Cloud Compute: 2, Online Storage: 1, Archive Storage: 1 (at least 4 cells: 3 services + values)
        self.assertGreaterEqual(len(cells), 4,
                               "Should have cells for at least service names and counts")
        
        # 4. Verify we have non-zero counts
        values = [cell.value for cell in cells if cell.value is not None]
        # Should have service names and count values (2, 1, 1, etc.)
        self.assertGreater(len(values), 0,
                          "Should have written service order data")

