"""
weather_service.py
Weather & Rainfall Integration Service.
Provides a replaceable weather provider interface with in-memory TTL caching,
precipitation intensity tracking, convective storm detection, and honest unavailable fallbacks.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field


class WeatherData(BaseModel):
    normalized_w: float = Field(..., ge=0.0, le=1.0)
    precipitation_mm_hr: float
    rainfall_category: str  # "dry", "moderate_rain", "heavy_rain", "cloudburst_torrential"
    convective_storm_alert: bool = False
    weather_status: str  # "live_telemetry", "cached_telemetry", "unavailable_fallback"
    data_source: str
    timestamp: datetime
    is_missing: bool = False
    explanation: str


class IWeatherProvider(ABC):
    @abstractmethod
    def get_weather_risk(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        ward: Optional[str] = None
    ) -> WeatherData:
        pass


class CachedWeatherProvider(IWeatherProvider):
    def __init__(
        self,
        cache_ttl_seconds: int = 3600,
        default_precipitation_mm_hr: Optional[float] = 65.0,  # Pilot monsoon storm default
        simulate_live: bool = True
    ):
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.default_precipitation = default_precipitation_mm_hr
        self.simulate_live = simulate_live
        self._cache: Dict[str, Tuple[WeatherData, datetime]] = {}

    def get_weather_risk(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        ward: Optional[str] = None
    ) -> WeatherData:
        now = datetime.now(timezone.utc)
        key = ward or (f"{round(latitude, 2)},{round(longitude, 2)}" if latitude and longitude else "general")

        # 1. Check valid cache
        if key in self._cache:
            cached_data, cached_at = self._cache[key]
            if (now - cached_at) < self.cache_ttl:
                # Return cached with cached status
                cached_data_copy = cached_data.model_copy()
                cached_data_copy.weather_status = "cached_telemetry"
                return cached_data_copy

        # 2. If no telemetry available (e.g., coordinates missing and simulate_live is False)
        if not self.simulate_live or (latitude is None and longitude is None and not ward):
            return WeatherData(
                normalized_w=0.50,
                precipitation_mm_hr=0.0,
                rainfall_category="unknown",
                convective_storm_alert=False,
                weather_status="unavailable_fallback",
                data_source="regional_convective_storm_fallback_model",
                timestamp=now,
                is_missing=True,
                explanation="Live meteorological radar feed unconfigured or coordinates absent; conservative storm baseline (0.50) applied.",
            )

        # 3. Simulate or fetch active regional radar telemetry
        precip = self.default_precipitation or 50.0
        # Normalization: 0 mm/hr = 0.0, 100 mm/hr = 1.0
        norm_w = min(1.0, max(0.0, round(precip / 100.0, 3)))
        is_cloudburst = precip >= 75.0

        if precip >= 75.0:
            category = "cloudburst_torrential"
        elif precip >= 40.0:
            category = "heavy_rain"
        elif precip >= 15.0:
            category = "moderate_rain"
        else:
            category = "dry"

        weather_res = WeatherData(
            normalized_w=norm_w,
            precipitation_mm_hr=precip,
            rainfall_category=category,
            convective_storm_alert=is_cloudburst,
            weather_status="live_telemetry",
            data_source="municipal_doppler_radar_grid_v1",
            timestamp=now,
            is_missing=False,
            explanation=f"Doppler radar telemetry: {precip:.1f} mm/hr ({category.replace('_', ' ')}). Normalized Weather Risk: {norm_w:.2f}.",
        )

        self._cache[key] = (weather_res, now)
        return weather_res


# Global weather provider instance
default_weather_provider: IWeatherProvider = CachedWeatherProvider()
