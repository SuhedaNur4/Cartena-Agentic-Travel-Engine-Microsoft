"""
Online adapters: WeatherAdapter (Open-Meteo) and POIAdapter stub.

Open-Meteo is free, requires no API key, and provides OpenAPI-compatible REST endpoints.
Docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx

from backend.application.ports.online_adapter_port import IOnlineAdapter

logger = logging.getLogger(__name__)

# ── Weather code → human-readable description ──────────────────────────────────
_WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm with hail",
}

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL  = "https://api.open-meteo.com/v1/forecast"

_TIMEOUT = 8.0  # seconds — fail fast rather than block the pipeline


class WeatherAdapter(IOnlineAdapter):
    """
    Fetches daily weather forecasts from Open-Meteo (free, no API key).

    The adapter reads `start_date` and `duration_days` from the fetch() context dict,
    which is populated by the use case from the TripRequest.

    Open-Meteo supports up to 16 days forecast from today.
    If start_date is None or beyond forecast window, returns [].
    """

    @property
    def name(self) -> str:
        return "weather"

    async def is_available(self) -> bool:
        """
        Always True — actual availability is determined per-request via start_date.
        The use_case's online_context loop checks context before calling fetch().
        """
        return True

    async def fetch(self, query: str, context: dict) -> list[str]:
        """
        Fetch daily weather for the destination and trip duration.

        Expects context keys:
            start_date:    date | None
            duration_days: int
            destination:   str

        Returns a list of strings like:
            "Weather forecast for Paris, France (5 days):"
            "Day 1 (Mon Aug 14): High 24°C / Low 18°C, Partly cloudy."
        """
        start_date: date | None = context.get("start_date")
        duration_days: int = context.get("duration_days", 0)
        destination: str = context.get("destination", query.split()[0])

        if start_date is None or duration_days == 0:
            return []

        try:
            lat, lon, resolved_name = await self._geocode(destination)
        except Exception as exc:
            logger.warning("Weather geocoding failed for '%s': %s", destination, exc)
            return []

        try:
            forecasts = await self._fetch_forecast(lat, lon, start_date)
        except Exception as exc:
            logger.warning("Weather forecast fetch failed: %s", exc)
            return []

        if not forecasts:
            return []

        lines: list[str] = []
        for i in range(duration_days):
            trip_date = start_date + timedelta(days=i)
            date_str = trip_date.strftime("%a %b %d")
            if i < len(forecasts):
                f = forecasts[i]
                weather_desc = _WMO_CODES.get(int(f.get("weathercode") or 0), "Unknown")
                max_temp = f.get("temperature_2m_max")
                min_temp = f.get("temperature_2m_min")
                rain_mm  = f.get("precipitation_sum") or 0
                rain_note = f" Rain: {rain_mm}mm." if rain_mm and rain_mm > 1 else ""
                lines.append(
                    f"Day {i + 1} ({date_str}): "
                    f"High {max_temp}°C / Low {min_temp}°C, "
                    f"{weather_desc}.{rain_note}"
                )
            else:
                lines.append(f"Day {i + 1} ({date_str}): Forecast not available.")

        if lines:
            header = f"Weather forecast for {resolved_name} ({duration_days} days):"
            return [header] + lines

        return []

    async def _geocode(self, destination: str) -> tuple[float, float, str]:
        """Resolve city name to (lat, lon, display_name) using Open-Meteo Geocoding."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _GEOCODING_URL,
                params={"name": destination, "count": 1, "language": "en", "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results")
        if not results:
            raise ValueError(f"No geocoding result for '{destination}'")

        r = results[0]
        name    = r.get("name", destination)
        country = r.get("country", "")
        display = f"{name}, {country}" if country else name
        return float(r["latitude"]), float(r["longitude"]), display

    async def _fetch_forecast(
        self, lat: float, lon: float, start_date: date
    ) -> list[dict]:
        """Fetch daily forecast from Open-Meteo forecast API."""
        params = {
            "latitude":  lat,
            "longitude": lon,
            "daily": [
                "weathercode",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
            ],
            "timezone":     "auto",
            "forecast_days": 16,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_FORECAST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily     = data.get("daily", {})
        dates     = daily.get("time", [])
        codes     = daily.get("weathercode", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip    = daily.get("precipitation_sum", [])

        start_str = start_date.isoformat()
        forecasts = []
        for i, d in enumerate(dates):
            if d >= start_str:
                forecasts.append({
                    "date":               d,
                    "weathercode":        codes[i]     if i < len(codes)     else 0,
                    "temperature_2m_max": max_temps[i] if i < len(max_temps) else None,
                    "temperature_2m_min": min_temps[i] if i < len(min_temps) else None,
                    "precipitation_sum":  precip[i]    if i < len(precip)    else 0,
                })

        return forecasts


class POIAdapter(IOnlineAdapter):
    """
    Stub: Always returns empty context.
    Future implementation: Overpass API (OpenStreetMap data).
    """

    @property
    def name(self) -> str:
        return "poi"

    async def is_available(self) -> bool:
        return False

    async def fetch(self, query: str, context: dict) -> list[str]:
        return []
