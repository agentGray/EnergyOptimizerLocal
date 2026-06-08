"""
Pydantic models for Energy Optimizer Agent.
Contract Envelope pattern: every API response wrapped in metadata + lineage + payload + confidence.
"""

from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class Metadata(BaseModel):
    """Response metadata."""
    agent: str = "energy"
    contract: str = "CON-004"
    domain: str = "Energy & ESG"
    version: str = "1.0.0"
    timestamp: str = ""
    plant_key: str = "us"

    def model_post_init(self, __context) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.utcnow().isoformat() + "Z")


class Lineage(BaseModel):
    """Data lineage tracking."""
    sources: list[str] = []
    refresh_cadence: str = "real-time"
    last_refresh: str = ""

    def model_post_init(self, __context) -> None:
        if not self.last_refresh:
            object.__setattr__(self, "last_refresh", datetime.utcnow().isoformat() + "Z")


class Confidence(BaseModel):
    """Confidence scoring for AI outputs."""
    score: float = 0.0
    factors: list[str] = []


class ContractEnvelope(BaseModel):
    """Standard contract envelope wrapping all API responses."""
    metadata: Metadata
    lineage: Lineage
    payload: Any
    confidence: Confidence


class EnergyKPIs(BaseModel):
    """Core energy KPIs."""
    energy_intensity: float  # kWh/unit
    energy_intensity_target: float = 4.1
    carbon_intensity: float  # lb CO2/unit
    carbon_intensity_target: float = 2.0
    peak_demand_kw: float  # kW
    peak_demand_target: float = 800.0
    energy_cost_per_day: float  # $/day
    cop: float  # coefficient of performance
    cop_target: float = 4.0
    iso_50001_score: float  # %


class EnergyAnomaly(BaseModel):
    """Energy anomaly detected on an asset."""
    asset_id: str
    asset_name: str
    anomaly_type: str
    deviation_pct: float
    energy_waste_kw: float
    linked_health_issue: Optional[str] = None
    severity: str  # low, medium, high, critical


class LoadDispatchRecommendation(BaseModel):
    """Load dispatch optimization recommendation."""
    id: str
    action: str
    asset_id: str
    asset_name: str
    shift_from_hour: str
    shift_to_hour: str
    savings_kw: float
    savings_cost_daily: float
    status: str = "pending"  # pending, approved, rejected


class AssetEnergyAttribution(BaseModel):
    """Per-asset energy attribution."""
    asset_id: str
    asset_name: str
    rated_kw: float
    current_kw: float
    pct_of_total: float
    cost_per_shift: float
    anomaly_flag: bool = False


class ESGMetrics(BaseModel):
    """ESG/Carbon tracking metrics."""
    total_co2_today_lb: float
    co2_per_unit: float
    solar_offset_kwh: float
    grid_carbon_intensity: float  # lb CO2/MWh
    renewable_pct: float
    target_co2_per_unit: float = 2.0


class EnergyForecast(BaseModel):
    """Energy load and cost forecast."""
    period: str  # 24h, 7d, 30d
    predicted_kwh: float
    predicted_cost: float
    predicted_peak_kw: float
    confidence_pct: float


class EnergyInsight(BaseModel):
    """AI-generated energy insight."""
    id: str
    category: str
    title: str
    description: str
    impact: str
    priority: str  # low, medium, high, critical
    action_required: bool = False


class ChartDataPoint(BaseModel):
    """A point for energy chart visualization."""
    label: str
    value: float
    unit: str = "kW"
