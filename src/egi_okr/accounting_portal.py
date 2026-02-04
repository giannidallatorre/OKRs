#!/usr/bin/env python3
from egi_okr.accounting_cpus import CPUAccounting

def main():
    """Compatibility shim for legacy accounting_portal.py executions."""
    CPUAccounting().run()

if __name__ == "__main__":
    main()
