import requests

# Contain business logic, perform specific tasks, and interact with external systems.
class AccountingService:
    def __init__(self, env):
        self.env = env

    def fetch_accounting_data(self):
        ''' Fetch accounting data from the EGI Accounting Portal '''
        _url = (
            f"{self.env['ACCOUNTING_SERVER_URL']}/{self.env['ACCOUNTING_SCOPE']}/"
            f"{self.env['ACCOUNTING_METRIC']}/VO/DATE/{self.env['DATE_FROM']}/"
            f"{self.env['DATE_TO']}/{self.env['ACCOUNTING_VO_GROUP_SELECTOR']}/"
            f"{self.env['ACCOUNTING_LOCAL_JOB_SELECTOR']}/{self.env['ACCOUNTING_DATA_SELECTOR']}/"
        )

        headers = {"Accept": "application/json"}

        self.log_debug(f"Fetching accounting records from: {_url}")

        try:
            response = requests.get(url=_url, headers=headers, verify=True)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] - Failed to fetch accounting data: {e}")
            raise RuntimeError(f"[ERROR] - Failed to fetch accounting data: {e}")
        return data

    def log_debug(self, message):
        ''' Log debug messages if log level is set to DEBUG '''
        if self.env.get('LOG') == "DEBUG":
            print(f"\n[INFO] - {message}")

    def is_valid_record(self, record_id):
        ''' Check if the record ID is valid (does not contain 'Percent' or 'Total') '''
        return "Percent" not in record_id and "Total" not in record_id

    def process_accounting_data(self, data):
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
            vo_name = record.get('id', '')
            if not self.is_valid_record(vo_name):
                continue

            cpu_hours = record.get('cpu_hours', 0)
            if cpu_hours > 0:
                summary["VOs_complete_list"].append({
                    "VO name": vo_name,
                    "CPU/h": f"{cpu_hours:7,d}"
                })
                summary["total"] += 1
            elif self.env['ACCOUNTING_SCOPE'] == "cloud":
                summary["total_noVOsCPUs"] += 1

            if "Total" in vo_name:
                if "cloud" in self.env['ACCOUNTING_SCOPE']:
                    summary["total_cloud_cpu_hours"] = cpu_hours
                else:
                    summary["total_htc_cpu"] = cpu_hours
        return summary
