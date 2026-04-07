import typer
import os
from typing import Optional
from .utils import get_env_settings, colourise
from .accounting_cpus import CPUAccounting
from .accounting_slas import SLAsAccounting
from .accounting_users import UsersAccounting
from .accounting_orders import OrdersAccounting
from .infrastructure import TemplatesAccounting

app = typer.Typer(help="EGI OKRs Accounting CLI Tool")

def get_default_print():

    """Check if PRINT_MODE is enabled in environment."""
    # We call get_env_settings to ensure .env is loaded
    env = get_env_settings()
    return env.get('PRINT_MODE', 'False') == 'True'

def get_default_insecure():
    """Check if SSL_CHECK is disabled in environment."""
    env = get_env_settings()
    return env.get('SSL_CHECK', 'True') == 'False'

def get_scope_env(scope: str, env: dict):
    new_env = env.copy()
    new_env['ACCOUNTING_SCOPE'] = scope.lower()
    return new_env

def run_module(module_class, print_mode: bool, scope: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None, insecure: bool = False):
    env = get_env_settings()
    if print_mode:
        env['PRINT_MODE'] = 'True'
    if insecure:
        env['SSL_CHECK'] = 'False'
    if scope:
        env['ACCOUNTING_SCOPE'] = scope.lower()
    if date_from:
        env['DATE_FROM'] = date_from
    if date_to:
        env['DATE_TO'] = date_to
        
    module = module_class(env=env)
    
    # Snapshot Logic: Warning & Labeling
    if module.is_snapshot:
        from .utils import get_current_month_period
        current_period = get_current_month_period()
        # If user provided a date_to that doesn't match current month, warn them
        if date_to and date_to != current_period:
             print(colourise("yellow", f"Warning: The data for {module_class.__name__} is a live snapshot and does not reflect the requested period ({date_to})."))
        
        if print_mode:
            os.environ['IS_SNAPSHOT_RUN'] = 'True'
            
    module.run()

@app.command()
def templates(
    print_mode: bool = typer.Option(get_default_print, "--print", help="Print results to terminal instead of Google Sheets"),
    insecure: bool = typer.Option(get_default_insecure, "--insecure", help="Skip SSL certificate verification"),
    date_from: Optional[str] = typer.Option(None, help="Start date (YYYY/MM)"),
    date_to: Optional[str] = typer.Option(None, help="End date (YYYY/MM)")
):
    """Fetch available VM templates (images) from the EGI Cloud Info API."""
    run_module(TemplatesAccounting, print_mode, None, date_from, date_to, insecure)

@app.command()

def cpus(
    scope: str = typer.Option("cloud", help="Accounting scope (cloud/htc)"),
    print_mode: bool = typer.Option(get_default_print, "--print", help="Print results to terminal instead of Google Sheets"),
    insecure: bool = typer.Option(get_default_insecure, "--insecure", help="Skip SSL certificate verification"),
    date_from: Optional[str] = typer.Option(None, help="Start date (YYYY/MM)"),
    date_to: Optional[str] = typer.Option(None, help="End date (YYYY/MM)")
):
    """Run CPU accounting (Cloud or HTC)."""
    run_module(CPUAccounting, print_mode, scope, date_from, date_to, insecure)

@app.command()
def slas(
    scope: str = typer.Option("cloud", help="Accounting scope (cloud/htc)"),
    print_mode: bool = typer.Option(get_default_print, "--print", help="Print results to terminal instead of Google Sheets"),
    insecure: bool = typer.Option(get_default_insecure, "--insecure", help="Skip SSL certificate verification"),
    date_from: Optional[str] = typer.Option(None, help="Start date (YYYY/MM)"),
    date_to: Optional[str] = typer.Option(None, help="End date (YYYY/MM)")
):
    """Run SLA accounting."""
    run_module(SLAsAccounting, print_mode, scope, date_from, date_to, insecure)

@app.command()
def users(
    print_mode: bool = typer.Option(get_default_print, "--print", help="Print results to terminal instead of Google Sheets"),
    insecure: bool = typer.Option(get_default_insecure, "--insecure", help="Skip SSL certificate verification"),
    date_from: Optional[str] = typer.Option(None, help="Start date (YYYY/MM)"),
    date_to: Optional[str] = typer.Option(None, help="End date (YYYY/MM)")
):
    """Run Users accounting and reports."""
    run_module(UsersAccounting, print_mode, None, date_from, date_to, insecure)

@app.command()
def orders(
    print_mode: bool = typer.Option(get_default_print, "--print", help="Print results to terminal instead of Google Sheets"),
    insecure: bool = typer.Option(get_default_insecure, "--insecure", help="Skip SSL certificate verification"),
    date_from: Optional[str] = typer.Option(None, help="Start date (YYYY/MM)"),
    date_to: Optional[str] = typer.Option(None, help="End date (YYYY/MM)")
):
    """Run Service Orders accounting."""
    run_module(OrdersAccounting, print_mode, None, date_from, date_to, insecure)

@app.command()
def all(
    print_mode: bool = typer.Option(get_default_print, "--print", help="Print all results to terminal instead of Google Sheets"),
    insecure: bool = typer.Option(get_default_insecure, "--insecure", help="Skip SSL certificate verification"),
    date_from: Optional[str] = typer.Option(None, help="Start date (YYYY/MM)"),
    date_to: Optional[str] = typer.Option(None, help="End date (YYYY/MM)")
):
    """Run all accounting modules sequentially."""
    print(colourise("bold", "\n>>> Running ALL OKR modules..."))
    # CPUs
    for s in ["cloud", "htc"]:
        run_module(CPUAccounting, print_mode, s, date_from, date_to, insecure)
    # SLAs
    for s in ["cloud", "htc"]:
        run_module(SLAsAccounting, print_mode, s, date_from, date_to, insecure)
    # Users
    run_module(UsersAccounting, print_mode, None, date_from, date_to, insecure)
    # Orders
    run_module(OrdersAccounting, print_mode, None, date_from, date_to, insecure)
    # Templates
    run_module(TemplatesAccounting, print_mode, None, date_from, date_to, insecure)

if __name__ == "__main__":
    app()
