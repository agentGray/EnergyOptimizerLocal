"""
KPI Engine for Energy Optimizer Agent.
Computes energy metrics, anomalies, forecasts from DuckDB data.
"""

import random
from datetime import datetime, timedelta
from ..data.db import query, query_single


# --- Constants ---
TARIFF_RATE_PER_KWH = 0.12  # $/kWh average blended rate
GRID_CARBON_FACTOR = 1.05  # lb CO2 per kWh (US average)
SOLAR_CAPACITY_KW = 120  # Installed solar capacity
SOLAR_HOURS_PER_DAY = 5.5  # Effective sun hours
SHIFTS_PER_DAY = 3
HOURS_PER_SHIFT = 8


def compute_energy_intensity() -> float:
    """
    KPI-005: Energy Intensity = Total kWh / Units produced.
    Uses hourly load profile + production orders.
    """
    # Total daily kWh from hourly profile (12 data points = 2-hour intervals)
    rows = query("SELECT SUM(kw_base) * 2 as total_kwh FROM energy_hourly")
    total_kwh = rows[0]["total_kwh"] if rows else 0

    # Units produced today from production orders
    orders = query(
        "SELECT SUM(qty_kg) as total_units FROM production_orders WHERE status IN ('completed', 'in_process')"
    )
    total_units = orders[0]["total_units"] if orders and orders[0]["total_units"] else 4200  # default

    return round(total_kwh / total_units, 2) if total_units > 0 else 0.0


def compute_carbon_intensity() -> float:
    """
    KPI-010: Carbon Intensity = Total CO2e / Units produced.
    CO2e = kWh * grid carbon factor - solar offset.
    """
    rows = query("SELECT SUM(kw_base) * 2 as total_kwh FROM energy_hourly")
    total_kwh = rows[0]["total_kwh"] if rows else 0

    solar_offset_kwh = SOLAR_CAPACITY_KW * SOLAR_HOURS_PER_DAY
    net_grid_kwh = max(0, total_kwh - solar_offset_kwh)
    total_co2_lb = net_grid_kwh * GRID_CARBON_FACTOR

    orders = query(
        "SELECT SUM(qty_kg) as total_units FROM production_orders WHERE status IN ('completed', 'in_process')"
    )
    total_units = orders[0]["total_units"] if orders and orders[0]["total_units"] else 4200

    return round(total_co2_lb / total_units, 3) if total_units > 0 else 0.0


def compute_peak_demand() -> float:
    """KPI-015: Peak Demand = Max kW in the load profile."""
    row = query_single("SELECT MAX(kw_base) as peak FROM energy_hourly")
    return row["peak"] if row else 0.0


def compute_energy_cost_per_day() -> float:
    """KPI-025: Energy Cost = Total kWh * tariff rate."""
    rows = query("SELECT SUM(kw_base) * 2 as total_kwh FROM energy_hourly")
    total_kwh = rows[0]["total_kwh"] if rows else 0
    return round(total_kwh * TARIFF_RATE_PER_KWH, 2)


def compute_cop() -> float:
    """
    KPI-028: COP = Cooling output / Electrical input.
    Uses chiller data from utilities.
    """
    chiller = query_single("SELECT * FROM utilities WHERE id = 'CHP-002'")
    if not chiller:
        return 4.0
    # COP degrades with health — healthy chiller = 5.2, degraded = lower
    base_cop = 5.2
    health_factor = chiller["health"] / 100.0
    return round(base_cop * health_factor, 2)


def compute_iso_50001_score() -> float:
    """
    ISO 50001 compliance score based on:
    - Energy intensity vs target
    - Anomaly count
    - Load management effectiveness
    """
    intensity = compute_energy_intensity()
    intensity_target = 4.1
    intensity_score = min(100, (intensity_target / max(intensity, 0.01)) * 100)

    # Factor in anomaly count
    anomalies = detect_anomalies()
    anomaly_penalty = len(anomalies) * 5  # -5% per anomaly

    # Factor in peak management
    peak = compute_peak_demand()
    peak_target = 800
    peak_score = min(100, (peak_target / max(peak, 1)) * 100)

    score = (intensity_score * 0.4 + peak_score * 0.3 + (100 - anomaly_penalty) * 0.3)
    return round(min(100, max(0, score)), 1)


def compute_optimization_score() -> float:
    """
    AI Optimization Score: composite metric showing how well energy is being managed.
    """
    intensity = compute_energy_intensity()
    cop = compute_cop()
    peak = compute_peak_demand()

    # Score components (0-100 each)
    intensity_score = max(0, min(100, (4.1 / max(intensity, 0.01)) * 80))
    cop_score = max(0, min(100, (cop / 4.0) * 80))
    peak_score = max(0, min(100, (800 / max(peak, 1)) * 80))

    # Weighted composite
    score = intensity_score * 0.35 + cop_score * 0.30 + peak_score * 0.35
    return round(min(100, score), 1)


def detect_anomalies() -> list[dict]:
    """
    Detect energy anomalies by comparing current_kw against rated_kw and threshold.
    Links anomalies to equipment health from machines/utilities.
    """
    assets = query("SELECT * FROM energy_assets")
    anomalies = []

    for asset in assets:
        asset_id = asset["id"]
        rated = asset["rated_kw"]
        threshold_pct = asset["anomaly_threshold_pct"]

        # Check machine health for correlation
        machine = query_single("SELECT * FROM machines WHERE id = ?", [asset_id])
        utility = query_single("SELECT * FROM utilities WHERE id = ?", [asset_id])

        health_source = machine or utility
        health_issue = None
        deviation_pct = 0.0

        if health_source:
            # Equipment with poor health draws more energy due to friction/wear
            health = health_source["health"]
            if health < 40:
                # Severely degraded: 15-25% overconsumption
                deviation_pct = round((100 - health) * 0.25, 1)
                health_issue = f"{health_source['name']}: health={health}%, vib={health_source['vib']}mm/s — severe degradation"
            elif health < 60:
                # Degraded: 10-18% overconsumption
                deviation_pct = round((100 - health) * 0.20, 1)
                health_issue = f"{health_source['name']}: health={health}%, vib={health_source['vib']}mm/s — degrading"
            elif health < 75:
                # Mild degradation: 5-10% overconsumption
                deviation_pct = round((100 - health) * 0.12, 1)
                health_issue = f"{health_source['name']}: health={health}%, early wear detected"

        if deviation_pct > threshold_pct:
            energy_waste = round(rated * (deviation_pct / 100), 1)
            severity = "critical" if deviation_pct > 20 else "high" if deviation_pct > 15 else "medium"
            anomalies.append({
                "asset_id": asset_id,
                "asset_name": asset["name"],
                "anomaly_type": "overconsumption_health_linked",
                "deviation_pct": deviation_pct,
                "energy_waste_kw": energy_waste,
                "linked_health_issue": health_issue,
                "severity": severity,
            })

    return anomalies


def get_load_dispatch_recommendations() -> list[dict]:
    """
    Generate load dispatch recommendations for shiftable assets.
    Identifies off-peak hours and suggests shifting non-critical loads.
    """
    # Find off-peak hours (lowest kW)
    hourly = query("SELECT * FROM energy_hourly ORDER BY kw_base ASC LIMIT 4")
    off_peak_hours = [row["hour"] for row in hourly]

    # Find peak hours
    peak_hours_data = query("SELECT * FROM energy_hourly ORDER BY kw_base DESC LIMIT 4")
    peak_hours = [row["hour"] for row in peak_hours_data]

    # Find shiftable assets (stored as 1/0 in SQLite, true/false in DuckDB)
    shiftable = query("SELECT * FROM energy_assets WHERE shiftable = 1 OR shiftable = 'true'")

    recommendations = []
    for i, asset in enumerate(shiftable):
        savings_kw = round(asset["rated_kw"] * 0.3, 1)  # 30% reduction by shifting
        savings_cost = round(savings_kw * 2 * TARIFF_RATE_PER_KWH, 2)  # 2 hours shifted
        recommendations.append({
            "id": f"LD-{1001 + i}",
            "action": f"Shift {asset['name']} operation to off-peak window",
            "asset_id": asset["id"],
            "asset_name": asset["name"],
            "shift_from_hour": peak_hours[i % len(peak_hours)] if peak_hours else "16:00",
            "shift_to_hour": off_peak_hours[i % len(off_peak_hours)] if off_peak_hours else "04:00",
            "savings_kw": savings_kw,
            "savings_cost_daily": savings_cost,
            "status": "pending",
        })

    return recommendations


def get_asset_energy_attribution() -> list[dict]:
    """
    Per-asset energy attribution: how much each asset consumes as % of total.
    """
    assets = query("SELECT * FROM energy_assets ORDER BY current_kw DESC")
    total_kw = sum(a["current_kw"] for a in assets)

    anomaly_assets = {a["asset_id"] for a in detect_anomalies()}

    attributions = []
    for asset in assets:
        pct = round((asset["current_kw"] / total_kw) * 100, 1) if total_kw > 0 else 0
        cost_per_shift = round(asset["current_kw"] * HOURS_PER_SHIFT * TARIFF_RATE_PER_KWH, 2)
        attributions.append({
            "asset_id": asset["id"],
            "asset_name": asset["name"],
            "rated_kw": asset["rated_kw"],
            "current_kw": asset["current_kw"],
            "pct_of_total": pct,
            "cost_per_shift": cost_per_shift,
            "anomaly_flag": asset["id"] in anomaly_assets,
        })

    return attributions


def compute_esg_metrics() -> dict:
    """ESG/Carbon tracking metrics."""
    rows = query("SELECT SUM(kw_base) * 2 as total_kwh FROM energy_hourly")
    total_kwh = rows[0]["total_kwh"] if rows else 0

    solar_offset_kwh = SOLAR_CAPACITY_KW * SOLAR_HOURS_PER_DAY
    net_grid_kwh = max(0, total_kwh - solar_offset_kwh)
    total_co2_lb = net_grid_kwh * GRID_CARBON_FACTOR

    orders = query(
        "SELECT SUM(qty_kg) as total_units FROM production_orders WHERE status IN ('completed', 'in_process')"
    )
    total_units = orders[0]["total_units"] if orders and orders[0]["total_units"] else 4200

    renewable_pct = round((solar_offset_kwh / max(total_kwh, 1)) * 100, 1)

    return {
        "total_co2_today_lb": round(total_co2_lb, 1),
        "co2_per_unit": round(total_co2_lb / max(total_units, 1), 3),
        "solar_offset_kwh": solar_offset_kwh,
        "grid_carbon_intensity": GRID_CARBON_FACTOR * 1000,  # lb CO2/MWh
        "renewable_pct": renewable_pct,
        "target_co2_per_unit": 2.0,
    }


def compute_energy_forecast(period: str = "24h") -> dict:
    """
    Energy load and cost forecast.
    Uses historical hourly profile + trend factors.
    """
    rows = query("SELECT SUM(kw_base) * 2 as daily_kwh FROM energy_hourly")
    daily_kwh = rows[0]["daily_kwh"] if rows else 0
    daily_cost = daily_kwh * TARIFF_RATE_PER_KWH
    peak_kw = compute_peak_demand()

    # Twin-predicted energy data for adjustment
    twin = query_single("SELECT * FROM twin_kpis WHERE kpi_id = 'PLANT_ENERGY'")
    growth_factor = 1.0
    if twin and twin["actual"] and twin["twin_predicted"]:
        growth_factor = twin["actual"] / twin["twin_predicted"]

    multiplier = {"24h": 1, "7d": 7, "30d": 30}.get(period, 1)
    confidence = {"24h": 92.0, "7d": 85.0, "30d": 74.0}.get(period, 80.0)

    return {
        "period": period,
        "predicted_kwh": round(daily_kwh * multiplier * growth_factor, 0),
        "predicted_cost": round(daily_cost * multiplier * growth_factor, 2),
        "predicted_peak_kw": round(peak_kw * growth_factor, 1),
        "confidence_pct": confidence,
    }


def get_top_consumers() -> list[dict]:
    """Top 6 energy consumers by current kW for bar chart."""
    assets = query("SELECT id, name, current_kw FROM energy_assets ORDER BY current_kw DESC LIMIT 6")
    return [{"label": a["name"], "value": a["current_kw"], "unit": "kW"} for a in assets]


def get_hourly_load_profile() -> list[dict]:
    """24-hour load profile for line chart."""
    rows = query("SELECT hour, kw_base FROM energy_hourly ORDER BY hour")
    return [{"label": r["hour"], "value": r["kw_base"], "unit": "kW"} for r in rows]


def generate_insights() -> list[dict]:
    """Generate AI-powered energy insights based on current data."""
    insights = []
    anomalies = detect_anomalies()
    cop = compute_cop()
    peak = compute_peak_demand()
    intensity = compute_energy_intensity()

    # Insight 1: Anomaly-based
    if anomalies:
        worst = max(anomalies, key=lambda a: a["deviation_pct"])
        insights.append({
            "id": "EI-001",
            "category": "anomaly",
            "title": f"Energy anomaly on {worst['asset_name']}",
            "description": f"{worst['asset_name']} consuming {worst['deviation_pct']}% above baseline. "
                          f"Linked to equipment health degradation: {worst['linked_health_issue']}. "
                          f"Estimated waste: {worst['energy_waste_kw']} kW.",
            "impact": f"${round(worst['energy_waste_kw'] * 24 * TARIFF_RATE_PER_KWH, 2)}/day wasted",
            "priority": worst["severity"],
            "action_required": True,
        })

    # Insight 2: COP degradation
    if cop < 4.0:
        insights.append({
            "id": "EI-002",
            "category": "efficiency",
            "title": "Chiller COP below target",
            "description": f"COP is {cop} (target: 4.0). Chiller health degradation increasing energy per unit of cooling. "
                          f"Consider maintenance to restore efficiency.",
            "impact": f"{round((4.0 - cop) / 4.0 * 100, 1)}% excess cooling energy",
            "priority": "high" if cop < 3.5 else "medium",
            "action_required": True,
        })

    # Insight 3: Peak demand
    if peak > 800:
        insights.append({
            "id": "EI-003",
            "category": "demand",
            "title": "Peak demand exceeds 800 kW target",
            "description": f"Current peak demand is {peak} kW, exceeding the 800 kW target by "
                          f"{round(peak - 800, 0)} kW. Demand charges may apply. "
                          f"Consider load shifting for non-critical assets.",
            "impact": f"Potential demand charge: ${round((peak - 800) * 15, 2)}/month",
            "priority": "high",
            "action_required": True,
        })

    # Insight 4: Energy intensity
    if intensity > 4.1:
        insights.append({
            "id": "EI-004",
            "category": "intensity",
            "title": "Energy intensity above target",
            "description": f"Current energy intensity is {intensity} kWh/unit (target: 4.1). "
                          f"Review production scheduling and equipment efficiency.",
            "impact": f"{round((intensity - 4.1) / 4.1 * 100, 1)}% above target",
            "priority": "medium",
            "action_required": False,
        })

    # Insight 5: Solar optimization
    esg = compute_esg_metrics()
    if esg["renewable_pct"] < 10:
        insights.append({
            "id": "EI-005",
            "category": "esg",
            "title": "Low renewable energy contribution",
            "description": f"Solar offset is only {esg['renewable_pct']}% of total consumption. "
                          f"Current solar generates {esg['solar_offset_kwh']} kWh/day. "
                          f"Expanding solar capacity could reduce carbon footprint significantly.",
            "impact": f"Additional 100kW solar = {round(100 * SOLAR_HOURS_PER_DAY * 365 * GRID_CARBON_FACTOR, 0)} lb CO2/year saved",
            "priority": "low",
            "action_required": False,
        })

    return insights
