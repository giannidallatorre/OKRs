import requests
import logging

class AccountingService:
    def __init__(self, env):
        self.env = env

    def fetch_accounting_data(self):
        ''' Fetch accounting data from the EGI Accounting Portal '''
        _url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/custom_cloud.php?"
            f"query={self.env['ACCOUNTING_METRIC']}&option=REGION&"
            f"sYear={self.env['DATE_FROM'][:4]}&sMonth={self.env['DATE_FROM'][-2:]}&"
            f"eYear={self.env['DATE_TO'][:4]}&eMonth={self.env['DATE_TO'][-2:]}&"
            f"yrange=VO&xrange=DATE&localJobs={self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}&"
            f"groupVO={self.env['ACCOUNTING_VO_GROUP_SELECTOR']}&tree=cloud&optval=&json=API"
        )

        headers = {"Accept": "application/json"}

        self.log_debug(f"Fetching accounting records from: {_url}")

        try:
            response = requests.get(url=_url, headers=headers, verify=True)
            response.raise_for_status()
            data = response.json()
            self.log_debug(f"Response content: {data}")
        except requests.exceptions.RequestException as e:
            logging.error(f"[ERROR] - Failed to fetch accounting data: {e}")
            raise RuntimeError(f"[ERROR] - Failed to fetch accounting data: {e}")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise RuntimeError(f"[ERROR] - Failed to fetch accounting data: {e}")
        return data

    def log_debug(self, message):
        ''' Log debug messages if log level is set to DEBUG '''
        if self.env.get('LOG') == "DEBUG":
            logging.debug(f"\n[INFO] - {message}")

    def is_valid_record(self, record):
        ''' Check if the record is valid (does not contain 'Percent' or 'Total' in the id and has 'Total' key) '''
        return "Percent" not in record['id'] and "Total" not in record['id'] and 'Total' in record

    def process_accounting_data(self, data):
        ''' Process the fetched accounting data '''
        self.log_debug("Starting to process accounting data")

        summary = {
            "total": 0,
            "total_noVOsCPUs": 0,
            "total_cloud_cpu_hours": 0,
            "total_htc_cpu": 0,
            "noVOsCPUs": [],
            "VOs_complete_list": []
        }

        for record in data:
            self.log_debug(f"Processing record: {record}")
            if not self.is_valid_record(record):
                self.log_debug(f"Invalid record skipped: {record}")
                continue

            total_cpu_hours = record['Total']
            if total_cpu_hours > 0:
                summary["VOs_complete_list"].append({
                    "VO name": record['id'],
                    "CPU/h": f"{total_cpu_hours:7,d}"
                })
                summary["total"] += 1
                self.log_debug(f"Added valid record: {record['id']} with CPU/h: {total_cpu_hours}")
            elif self.env['ACCOUNTING_SCOPE'] == "cloud":
                summary["total_noVOsCPUs"] += 1
                self.log_debug(f"Record with no VO CPUs: {record['id']}")

            if "Total" in record['id']:
                if "cloud" in self.env['ACCOUNTING_SCOPE']:
                    summary["total_cloud_cpu_hours"] = total_cpu_hours
                    self.log_debug(f"Total cloud CPU hours updated: {total_cpu_hours}")
                else:
                    summary["total_htc_cpu"] = total_cpu_hours
                    self.log_debug(f"Total HTC CPU hours updated: {total_cpu_hours}")

        self.log_debug(f"Processing summary: {summary}")
        return summary
        ''' Process the fetched accounting data '''
        summary = {
            "total": 0,
            "total_noVOsCPUs": 0,
            "total_cloud_cpu_hours": 0,
            "total_htc_cpu": 0,
            "noVOsCPUs": [],
            "VOs_complete_list": []
        }

        for record in data:
            if not self.is_valid_record(record):
                continue

            total_cpu_hours = record['Total']
            if total_cpu_hours > 0:
                summary["VOs_complete_list"].append({
                    "VO name": record['id'],
                    "CPU/h": f"{total_cpu_hours:7,d}"
                })
                summary["total"] += 1
            elif self.env['ACCOUNTING_SCOPE'] == "cloud":
                summary["total_noVOsCPUs"] += 1

            if "Total" in record['id']:
                if "cloud" in self.env['ACCOUNTING_SCOPE']:
                    summary["total_cloud_cpu_hours"] = total_cpu_hours
                else:
                    summary["total_htc_cpu"] = total_cpu_hours
        return summary