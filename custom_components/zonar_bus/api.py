"""Async client for the Zonar Bus Suite guardian API.

Protocol (reverse-engineered from the Flutter parent app):
  * Login:  POST authapi.bus-suite.com/api/account/newguardiantoken
            -> {data: {accessToken, refreshToken, expiresIn ~120d}}
  * Data:   bussuite-gapi.zonar.com/api, Bearer token.
            - /ga/currentUserInfo  : POST, guardian-level, no org header.
            - org-scoped endpoints  : need header  organizationXid: <org>.
            - /ga/students          : GET, lists children + their stops/runs.
            - /ga/assetLocation/{routeMasterTypeXid} : GET, live bus position for
              one run. Returns a JSON array (empty until the driver activates the
              route). Each item: {routeMasterTypeXid, routeXid, location:{x:lat,
              y:lon}, route, routeType, assetName, heading, ...}.
Responses are wrapped: {statusCode, message, data, errors}.
"""

from __future__ import annotations

import uuid

import aiohttp

AUTH_BASE = "https://authapi.bus-suite.com/api"
API_BASE = "https://bussuite-gapi.zonar.com/api"


class ZonarAuthError(Exception):
    """Invalid credentials or expired session."""


class ZonarApiError(Exception):
    """Unexpected API response."""


class ZonarApi:
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str):
        self._session = session
        self._username = username
        self._password = password
        self._device_id = str(uuid.uuid4())
        self.token: str | None = None
        self.org_xid: str | None = None

    async def login(self) -> dict:
        body = {
            "userName": self._username,
            "password": self._password,
            "deviceId": self._device_id,
            "deviceType": "Android",
            "appVersionName": "6.9.7",
            "appVersionCode": "60907",
        }
        async with self._session.post(f"{AUTH_BASE}/account/newguardiantoken", json=body) as resp:
            status = resp.status
            payload = await resp.json(content_type=None)
        data = payload.get("data") if isinstance(payload, dict) else None
        if status != 200 or not isinstance(data, dict) or "accessToken" not in data:
            raise ZonarAuthError(f"Login failed ({status})")
        self.token = data["accessToken"]
        return data

    def _headers(self, org: bool) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if org and self.org_xid:
            headers["organizationXid"] = self.org_xid
        return headers

    async def _request(self, method: str, path: str, *, org: bool = False, json_body=None, retry: bool = True):
        if self.token is None:
            await self.login()
        async with self._session.request(
            method, f"{API_BASE}{path}", headers=self._headers(org), json=json_body
        ) as resp:
            status = resp.status
            payload = await resp.json(content_type=None)
        if status == 401 and retry:
            await self.login()
            return await self._request(method, path, org=org, json_body=json_body, retry=False)
        if status == 401:
            raise ZonarAuthError(f"{method} {path} -> 401")
        if status != 200:
            raise ZonarApiError(f"{method} {path} -> {status}: {payload}")
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    async def current_user(self) -> dict:
        """Guardian profile; caches organizationXid for org-scoped calls."""
        data = await self._request("POST", "/ga/currentUserInfo", json_body={})
        org = (data or {}).get("memberOrganization", {}).get("organizationXid")
        if org:
            self.org_xid = org
        return data

    async def students(self) -> dict:
        if not self.org_xid:
            await self.current_user()
        return await self._request("GET", "/ga/students", org=True)

    async def asset_location(self, route_master_type_xid: str) -> list:
        """Live bus position(s) for one run; empty list until the route is active."""
        if not self.org_xid:
            await self.current_user()
        result = await self._request("GET", f"/ga/assetLocation/{route_master_type_xid}", org=True)
        return result if isinstance(result, list) else []

    async def route_stops(self, route_xid: str) -> list:
        """Ordered stops for a route (static route-plan config, keyed by routeXid).

        Each item: {routeStopXid, stopNumber, pathOrder, stopName, scheduledTime,
        showOnMap, stopLocationG: {lat, lng}, ...}.
        """
        if not self.org_xid:
            await self.current_user()
        result = await self._request("GET", f"/ga/routePlan/stops/{route_xid}", org=True)
        return result if isinstance(result, list) else []

    async def route_waypoints(self, route_xid: str) -> list:
        """The drawn road path for a route, as ordered geo points (for the map line)."""
        if not self.org_xid:
            await self.current_user()
        result = await self._request("GET", f"/ga/routePlan/waypoints/{route_xid}", org=True)
        return result if isinstance(result, list) else []
