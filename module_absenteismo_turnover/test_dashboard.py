import traceback
from data_processor import get_dashboard_data
try:
    get_dashboard_data()
except Exception as e:
    traceback.print_exc()
