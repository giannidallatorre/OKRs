import json
import logging
#from pyOKR_VOs_CPUs_Accounting.services.accounting_service import AccountingService
from pyOKR_VOs_CPUs_Accounting.services.google_sheets_service import GoogleSheetsService
from pyOKR_VOs_CPUs_Accounting.utils.utils import handle_exception
from pyOKR_VOs_CPUs_Accounting.services.service import AccountingService

class Controller:
    def __init__(self, env, dry_run=False):
        self.env = env
        self.dry_run = dry_run
        self.accounting_service = AccountingService(env)
        self.google_sheets_service = GoogleSheetsService(env) if not dry_run else None

    def run(self):
        env = self.env
        log = env['LOG']
        logging.info(f"Log Level = {log}")

        if log == "DEBUG":
            logging.debug("\n- Environment settings:")
            logging.debug(json.dumps(env, indent=4))

        try:
            data = self.accounting_service.fetch_accounting_data()
            logging.debug(f"Fetched accounting data: {json.dumps(data, indent=4)}")
        except Exception as e:
            handle_exception(e, env)
            return

        accounting_period = f"{env['DATE_FROM'][0:4]}.{env['DATE_FROM'][-2:]}-{env['DATE_TO'][-2:]}"
        logging.info(f"[INFO] Reporting Period: {accounting_period}")

        try:
            summary = self.accounting_service.process_accounting_data(data)
            logging.debug(f"Processed summary: {json.dumps(summary, indent=4)}")
            if self.dry_run:
                self.pretty_print_summary(accounting_period, summary)
            else:
                try:
                    worksheet = self.google_sheets_service.init_GWorkSheet()
                    self.google_sheets_service.update_GWorkSheet(worksheet, accounting_period, summary)
                except FileNotFoundError as e:
                    handle_exception(e, env)
        except Exception as e:
            handle_exception(e, env)

    def pretty_print_summary(self, accounting_period, summary):
        print(f"Reporting Period: {accounting_period}")
        print(f"Total VOs with accounting records: {summary['total']}")
        print(f"Total VOs with no accounting records: {summary['total_noVOsCPUs']}")
        print(f"Total Cloud CPU/h: {summary['total_cloud_cpu_hours']}")
        print(f"Total HTC CPU/h: {summary['total_htc_cpu']}")
        print("VOs with accounting records:")
        for vo in summary["VOs_complete_list"]:
            print(f"  - {vo['VO name']}: {vo['CPU/h']}")
        print("VOs with no accounting records:")
        for vo in summary["noVOsCPUs"]:
            print(f"  - {vo}")