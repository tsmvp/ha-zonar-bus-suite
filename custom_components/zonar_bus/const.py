"""Constants for the Zonar Bus Suite integration."""

from datetime import timedelta

DOMAIN = "zonar_bus"

# assetLocation is a live GPS feed; poll often during run windows (see schedule.py).
SCAN_INTERVAL = timedelta(seconds=15)

# Re-fetch the student/route mapping at most once a day.
STUDENTS_MAX_AGE = 86400
