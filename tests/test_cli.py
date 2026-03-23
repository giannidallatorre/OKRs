import unittest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from egi_okr.cli import app

runner = CliRunner()

class TestCLI(unittest.TestCase):
    @patch("egi_okr.cli.CPUAccounting")
    def test_cpus_command(self, mock_cpu):
        mock_instance = mock_cpu.return_value
        result = runner.invoke(app, ["cpus", "--print", "--scope", "htc"])
        self.assertEqual(result.exit_code, 0)
        mock_cpu.assert_called_once()
        # Check if PRINT_MODE was set in the env passed to Accounting
        passed_env = mock_cpu.call_args[1].get('env', {})
        self.assertEqual(passed_env.get('PRINT_MODE'), 'True')
        self.assertEqual(passed_env.get('ACCOUNTING_SCOPE'), 'htc')
    @patch("egi_okr.cli.CPUAccounting")
    def test_cpus_insecure(self, mock_cpu):
        result = runner.invoke(app, ["cpus", "--insecure"])
        self.assertEqual(result.exit_code, 0)
        passed_env = mock_cpu.call_args[1].get('env', {})
        self.assertEqual(passed_env.get('SSL_CHECK'), 'False')


    @patch("egi_okr.cli.SLAsAccounting")
    def test_slas_command(self, mock_sla):
        result = runner.invoke(app, ["slas", "--print", "--date-from", "2024/01"])
        self.assertEqual(result.exit_code, 0)
        mock_sla.assert_called_once()
        passed_env = mock_sla.call_args[1].get('env', {})
        self.assertEqual(passed_env.get('DATE_FROM'), '2024/01')

    @patch("egi_okr.cli.UsersAccounting")
    def test_users_command(self, mock_users):
        result = runner.invoke(app, ["users", "--print"])
        self.assertEqual(result.exit_code, 0)
        mock_users.assert_called_once()

    @patch("egi_okr.cli.OrdersAccounting")
    def test_orders_command(self, mock_orders):
        result = runner.invoke(app, ["orders", "--print"])
        self.assertEqual(result.exit_code, 0)
        mock_orders.assert_called_once()

    @patch("egi_okr.cli.CPUAccounting")
    @patch("egi_okr.cli.SLAsAccounting")
    @patch("egi_okr.cli.UsersAccounting")
    @patch("egi_okr.cli.OrdersAccounting")
    @patch("egi_okr.cli.TemplatesAccounting")
    def test_all_command(self, mock_templates, mock_orders, mock_users, mock_sla, mock_cpu):
        result = runner.invoke(app, ["all", "--print"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(mock_cpu.call_count, 2) # cloud + htc
        self.assertEqual(mock_sla.call_count, 2) # cloud + htc
        self.assertEqual(mock_users.call_count, 1)
        self.assertEqual(mock_orders.call_count, 1)
        self.assertEqual(mock_templates.call_count, 1)

    @patch("egi_okr.cli.TemplatesAccounting")
    def test_templates_command(self, mock_templates):
        result = runner.invoke(app, ["templates", "--print"])
        self.assertEqual(result.exit_code, 0)
        mock_templates.assert_called_once()
        passed_env = mock_templates.call_args[1].get('env', {})
        self.assertEqual(passed_env.get('PRINT_MODE'), 'True')
    @patch("egi_okr.cli.CPUAccounting")
    @patch("egi_okr.cli.get_env_settings")
    def test_cpus_env_defaults(self, mock_get_env, mock_cpu):
        # Simulate PRINT_MODE=True and SSL_CHECK=False in .env
        mock_get_env.return_value = {
            'PRINT_MODE': 'True',
            'SSL_CHECK': 'False',
            'ACCOUNTING_SCOPE': 'cloud'
        }
        # Run without flags
        result = runner.invoke(app, ["cpus"])
        self.assertEqual(result.exit_code, 0)
        passed_env = mock_cpu.call_args[1].get('env', {})
        # Should pick up defaults from mock_get_env via our default-factory functions
        self.assertEqual(passed_env.get('PRINT_MODE'), 'True')
        self.assertEqual(passed_env.get('SSL_CHECK'), 'False')

    @patch("egi_okr.accounting_users.get_VOs_stats")
    @patch("egi_okr.accounting_users.UsersAccounting.run_vo_reports_logic")
    def test_users_sum_logic(self, mock_report, mock_stats):
        # Verify the TypeError fix (summing strings/None)
        mock_stats.return_value = [
            {'name': 'vo1', 'active_members': '10'},
            {'name': 'vo2', 'active_members': None},
            {'name': 'vo3', 'active_members': 5}
        ]
        # Avoid real API calls in run_vo_reports_logic
        mock_report.return_value = None
        
        result = runner.invoke(app, ["users", "--print"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Total Registered Members: 15", result.output)

    @patch("egi_okr.jira.requests.Session.get") 
    def test_orders_no_token(self, mock_get):
        # Verify it doesn't crash without JIRA_AUTH_TOKEN
        with patch.dict('os.environ', {}, clear=True):
            result = runner.invoke(app, ["orders", "--print"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("0 orders processed", result.output)

if __name__ == "__main__":
    unittest.main()
