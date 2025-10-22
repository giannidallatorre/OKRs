#!/usr/bin/env python3
#
#  Copyright 2024 EGI Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import argparse
import logging
import warnings
try:
    from pyOKR_VOs_CPUs_Accounting.utils.utils import handle_exception, get_env_settings
    from pyOKR_VOs_CPUs_Accounting.controllers.controller import Controller
except ImportError as e:
    print(f"Error importing modules: {e}")
    exit(1)

__author__    = "Giuseppe LA ROCCA"
__email__     = "giuseppe.larocca@egi.eu"
__version__   = "$Revision: 0.6"
__date__      = "$Date: 02/06/2024 10:50:22"
__copyright__ = "Copyright (c) 2024 EGI Foundation"
__license__   = "Apache Licence v2.0"

warnings.filterwarnings("ignore")

def configure_logging(env, verbose):
    # Override with -v CLI option if set
    if verbose:
        log_level = "DEBUG"
    else:
        log_level = env['LOG'].upper()
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    parser = argparse.ArgumentParser(description="Run the OKR VOs CPUs Accounting script.")
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose logging")
    parser.add_argument('--dry-run', action='store_true', help="Run without writing to Google Sheets")
    args = parser.parse_args()

    env = get_env_settings()
    configure_logging(env, args.verbose)

    try:
        controller = Controller(env, dry_run=args.dry_run)
        controller.run()
    except Exception as e:
        handle_exception(e, env)

if __name__ == "__main__":
    main()