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
    def test_all_command(self, mock_orders, mock_users, mock_sla, mock_cpu):
        result = runner.invoke(app, ["all", "--print"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(mock_cpu.call_count, 2) # cloud + htc
        self.assertEqual(mock_sla.call_count, 2) # cloud + htc
        self.assertEqual(mock_users.call_count, 1)
        self.assertEqual(mock_orders.call_count, 1)

if __name__ == "__main__":
    unittest.main()
