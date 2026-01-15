#!/usr/bin/env python3
import sys
import argparse
import os

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from egi_okr.accounting_cpus import CPUAccounting
from egi_okr.accounting_users import UsersAccounting
from egi_okr.accounting_orders import OrdersAccounting
from egi_okr.accounting_slas import SLAsAccounting
from egi_okr.vo_reports import VOsReports
from egi_okr.utils import colourise

def main():
    parser = argparse.ArgumentParser(description='EGI OKR Accounting Tools')
    parser.add_argument('task', choices=['cpus', 'users', 'orders', 'slas', 'reports'], 
                        help='The accounting task to run')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # Apply debug flag if needed (most modules check env, but we can override)
    if args.debug:
        os.environ['LOG'] = 'DEBUG'

    print(f"Running task: {colourise('cyan', args.task)}")

    try:
        if args.task == 'cpus':
            app = CPUAccounting()
            app.run()
        elif args.task == 'users':
            app = UsersAccounting()
            app.run()
        elif args.task == 'orders':
            app = OrdersAccounting()
            app.run()
        elif args.task == 'slas':
            app = SLAsAccounting()
            app.main()
        elif args.task == 'reports':
            app = VOsReports()
            app.run()
            
        print(colourise("green", f"\nTask '{args.task}' completed successfully."))
        
    except Exception as e:
        print(colourise("red", f"\nError running task '{args.task}': {e}"))
        sys.exit(1)

if __name__ == "__main__":
    main()
