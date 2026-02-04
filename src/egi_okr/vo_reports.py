#!/usr/bin/env python3
from egi_okr.accounting_users import UsersAccounting

def main():
    """Compatibility shim for legacy vo_reports.py executions."""
    UsersAccounting().run_vo_reports_logic()

if __name__ == "__main__":
    main()
