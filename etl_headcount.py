import sys
import os

# Adds module_sst to path and runs etl_headcount
current_dir = os.path.dirname(os.path.abspath(__file__))
module_sst_dir = os.path.join(current_dir, 'module_sst')
if module_sst_dir not in sys.path:
    sys.path.insert(0, module_sst_dir)

import etl_headcount

if __name__ == '__main__':
    etl_headcount.run_etl()
