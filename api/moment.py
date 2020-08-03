"""Get current EST time."""
import pytz
from datetime import datetime, timedelta


def get_current_time() -> str:
	"""Get current EST time"""
	now = datetime.now(pytz.utc)
	return now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-6] + '000Z'


def get_current_time_algolia(timeframe) -> str:
	"""Get current EST time"""
	now = datetime.now(pytz.utc)
	start_date = now - timedelta(days=timeframe)
	return start_date.strftime("%Y-%m-%d")
