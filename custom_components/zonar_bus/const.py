"""Constants for the Zonar Bus Suite integration."""

from datetime import timedelta

DOMAIN = "zonar_bus"

# assetLocation is a live GPS feed; poll often during run windows (see schedule.py).
SCAN_INTERVAL = timedelta(seconds=15)

# Re-fetch the student/route mapping at most once a day.
STUDENTS_MAX_AGE = 86400

# Cap the route-line geojson so the sensor attribute stays small (a route has
# ~1000+ waypoints; a few hundred draw the same line and stay under HA's
# per-state attribute size limit).
MAX_ROUTE_POINTS = 500
