"""Modular Source Adapters Package for Agricultural Crop Yield Data."""

from app.data.adapters.base import BaseSourceAdapter, AdapterIngestionReport
from app.data.adapters.icrisat_dld_adapter import IcrisatDldAdapter
from app.data.adapters.weather_adapter import WeatherAdapter
from app.data.adapters.soil_adapter import SoilAdapter

__all__ = [
    "BaseSourceAdapter",
    "AdapterIngestionReport",
    "IcrisatDldAdapter",
    "WeatherAdapter",
    "SoilAdapter",
]
