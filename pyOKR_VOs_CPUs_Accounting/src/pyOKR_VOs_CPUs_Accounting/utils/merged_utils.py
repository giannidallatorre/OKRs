import os

def find_difference(activeVOs_1, activeVOs_2, detailed=False):
    """Find difference between two sets of VOs.
    If detailed=True, return arriving and leaving VOs separately.
    """
    activeVOs_1 = set(activeVOs_1.split(", ")) if activeVOs_1 else set()
    activeVOs_2 = set(activeVOs_2.split(", ")) if activeVOs_2 else set()
    
    str_diff = activeVOs_1.symmetric_difference(activeVOs_2)
    
    if not str_diff:
        return ("-", "-") if detailed else ""

    if detailed:
        arrivingVOs = {vo for vo in str_diff if vo in activeVOs_2}
        leavingVOs = {vo for vo in str_diff if vo in activeVOs_1}
        return ", ".join(arrivingVOs) or "-", ", ".join(leavingVOs) or "-"
    
    return ", ".join(str_diff)

def colourise(colour, text):
    """Colour text in shell output."""
    colours = {
        "black": "1;30", "red": "1;31", "green": "1;32", "yellow": "1;33",
        "blue": "1;34", "magenta": "1;35", "cyan": "1;36", "gray": "1;37"
    }
    return f"\033[{colours.get(colour, '0')}m{text}\033[0m"

def highlight(colour, text):
    """Highlight text in shell output."""
    highlights = {
        "black": "1;40", "red": "1;41", "green": "1;42", "yellow": "1;43",
        "blue": "1;44", "magenta": "1;45", "cyan": "1;46", "gray": "1;47"
    }
    return f"\033[{highlights.get(colour, '0')}m{text}\033[0m"

def get_env_settings(context="default"):
    """Read environment variables based on context (users, cpus, slas, service_orders, vos_report)."""
    env_mappings = {
        "users": ["OPERATIONS_SERVER_URL", "OPERATIONS_API_KEY", "OPERATIONS_FORMAT"],
        "cpus": ["ACCOUNTING_SERVER_URL", "ACCOUNTING_SCOPE", "ACCOUNTING_METRIC"],
        "slas": ["ACCOUNTING_SERVER_URL", "ACCOUNTING_SCOPE", "GOOGLE_SLAs_SHEET_NAME"],
        "service_orders": ["JIRA_SERVER_URL", "JIRA_AUTH_TOKEN", "SERVICE_ORDERS_PROJECTKEY"],
        "vos_report": ["OPERATIONS_SERVER_URL", "OPERATIONS_API_KEY", "OPERATIONS_VO_LIST_PREFIX", "OPERATIONS_VO_ID_CARD_PREFIX", "OPERATIONS_VOS_REPORT_PREFIX"]
    }
    
    keys = env_mappings.get(context, []) + ["SERVICE_ACCOUNT_PATH", "SERVICE_ACCOUNT_FILE", "GOOGLE_SHEET_NAME", "LOG", "DATE_FROM", "DATE_TO", "SSL_CHECK"]
    
    settings = {key: os.environ[key] for key in keys if key in os.environ}
    
    return settings
