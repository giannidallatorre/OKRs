#!/usr/bin/env python3
import argparse
import datetime
import os
from egi_okr.utils import get_env_settings, colourise
from egi_okr.accounting_users import UsersAccounting
from egi_okr.accounting_cpus import CPUAccounting
from egi_okr.accounting_slas import SLAsAccounting
from egi_okr.accounting_orders import OrdersAccounting

def get_quarters(start_year, end_year):
    quarters = []
    for year in range(start_year, end_year + 1):
        quarters.append({"from": f"{year}/01", "to": f"{year}/03"})
        quarters.append({"from": f"{year}/04", "to": f"{year}/06"})
        quarters.append({"from": f"{year}/07", "to": f"{year}/09"})
        quarters.append({"from": f"{year}/10", "to": f"{year}/12"})
    return quarters

def load_secrets(path):
    """Simple manual loader for KEY=VAL secret files to avoid dependencies."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.strip().split("=", 1)
                key = key.strip()
                val = val.strip()
                # Remove quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                os.environ[key] = val

def main():
    # Load secrets from local file for native run
    load_secrets("act_setup/local.secrets")
    
    parser = argparse.ArgumentParser(description="Backfill OKR data for previous years")
    parser.add_argument("--start", type=int, default=2020, help="Start year (default: 2020)")
    parser.add_argument("--end", type=int, default=2025, help="End year (default: 2025)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--module", choices=["users", "cpus-cloud", "cpus-htc", "slas-cloud", "slas-htc", "orders", "all"], default="all")
    args = parser.parse_args()

    env = get_env_settings()
    periods = get_quarters(args.start, args.end)

    print(colourise("cyan", "\n[BACKFILL-START]"), f"Years: {args.start}-{args.end} ({len(periods)} periods)")
    if args.dry_run:
        print(colourise("yellow", "[MODE]"), "DRY RUN - No writes to Google Sheets")

    # Mapping modules to classes and configurations
    modules = []
    if args.module in ["users", "all"]:
        modules.append({"name": "Users", "class": UsersAccounting, "env_mods": {}})
    
    if args.module in ["cpus-cloud", "all"]:
        modules.append({"name": "CPU-Cloud", "class": CPUAccounting, "env_mods": {"ACCOUNTING_SCOPE": "cloud", "ACCOUNTING_METRIC": "sum_elap_processors"}})
    
    if args.module in ["cpus-htc", "all"]:
        modules.append({"name": "CPU-HTC", "class": CPUAccounting, "env_mods": {"ACCOUNTING_SCOPE": "egi", "ACCOUNTING_METRIC": "elap_processors"}})

    if args.module in ["slas-cloud", "all"]:
        modules.append({"name": "SLA-Cloud", "class": SLAsAccounting, "env_mods": {"ACCOUNTING_SCOPE": "cloud", "ACCOUNTING_METRIC": "sum_elap_processors"}})
    
    if args.module in ["slas-htc", "all"]:
        modules.append({"name": "SLA-HTC", "class": SLAsAccounting, "env_mods": {"ACCOUNTING_SCOPE": "egi", "ACCOUNTING_METRIC": "elap_processors"}})

    if args.module in ["orders", "all"]:
        modules.append({"name": "Orders", "class": OrdersAccounting, "env_mods": {}})

    for period in periods:
        print(colourise("cyan", f"\n>>> Processing Period: {period['from']} to {period['to']}"))
        
        # Temporarily override environmental dates
        env['DATE_FROM'] = period['from']
        env['DATE_TO'] = period['to']

        for mod in modules:
            print(colourise("green", f"\n[*] Module: {mod['name']}"))
            
            # Apply module-specific env overrides
            current_env = env.copy()
            current_env.update(mod['env_mods'])
            
            try:
                app = mod['class'](env=current_env)
                # Check if class uses main() or run()
                run_func = getattr(app, 'run', None) or getattr(app, 'main', None)
                if run_func:
                    run_func(dry_run=args.dry_run)
                else:
                    print(colourise("red", "[ERROR]"), f"No run/main function found for {mod['name']}")
            except Exception as e:
                print(colourise("red", "[ERROR]"), f"Failed {mod['name']} for {period['from']}: {e}")

    print(colourise("cyan", "\n[BACKFILL-FINISHED]"))

if __name__ == "__main__":
    main()
