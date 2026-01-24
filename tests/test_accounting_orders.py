
import unittest
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
            'SERVICE_ORDERS_ISSUETYPE': 'Service Order',
            'JIRA_SERVER_URL': 'http://jira',
            'SERVICE_ACCOUNT_FILE': 'dummy.json'
        }
        self.app = OrdersAccounting(self.env)

    def test_parse_service_name(self):
        # Logic expects no space after colon or strict match structure
        details = 'customfield... "service":"EGI Cloud Compute", ...'
        name = self.app.parse_service_name(details)
        self.assertEqual(name, "EGI Cloud Compute")
        
        details2 = '"service":"Sofware Distribution",'
        name2 = self.app.parse_service_name(details2)
        self.assertEqual(name2, "Sofware Distribution")

    def test_process_orders(self):
        orders = [
            {
                'key': 'SO-1',
                'fields': {
                    'issuetype': {'name': 'Service Order'},
                    'customfield_10711': '... "service":"EGI Cloud Compute", ...'
                }
            },
            {
                'key': 'SO-2',
                'fields': {
                    'issuetype': {'name': 'Service Order'},
                    'customfield_10711': '... "service":"Sofware Distribution", ...'
                }
            },
            {
                'key': 'SO-3',
                'fields': {
                    'issuetype': {'name': 'Bug'},
                    'customfield_10711': '... "service":"EGI Cloud Compute", ...'
                }
            }
        ]
        
        buckets = self.app.process_orders(orders)
        
        self.assertIn('SO-1', buckets['EGI Cloud Compute'])
        self.assertIn('SO-2', buckets['EGI Software Distribution'])
        self.assertNotIn('SO-3', buckets['EGI Cloud Compute'])

    @patch('egi_okr.accounting_orders.init_GWorkSheet')
    @patch('egi_okr.accounting_orders.get_service_orders')
    def test_run_flow(self, mock_get_orders, mock_init_sheet):
        mock_worksheet = MagicMock()
        mock_init_sheet.return_value = mock_worksheet
        
        mock_worksheet.get_all_records.return_value = [{'Services': 'Header', '2023.10-12': 'Old'}]
        
        # mock findall
        def findall_side_effect(arg):
             if arg == '2024.01-03':
                 m = MagicMock()
                 m.row = 1 # Header
                 m.col = 3
                 return [m]
             elif arg == 'EGI Cloud Compute':
                 m = MagicMock()
                 m.row = 2
                 m.col = 1
                 return [m]
             return []
        mock_worksheet.findall.side_effect = findall_side_effect
        
        mock_get_orders.return_value = [
            {
                'key': 'SO-1',
                'fields': {
                    'issuetype': {'name': 'Service Order'},
                    'customfield_10711': '... "service":"EGI Cloud Compute", ...'
                }
            }
        ]
        
        self.app.run()
        
        # Assert updated
        mock_worksheet.update_cells.assert_called()

if __name__ == '__main__':
    unittest.main()
