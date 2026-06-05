"""
Energy Optimizer Agent API Routes.
Contract: CON-004 | Domain: Energy & ESG
"""

from fastapi import APIRouter, Query
from ...semantic.models import (
    ContractEnvelope,
    Metadata,
    Lineage,
    Confidence,
)
from ...semantic.kpi_engine import (
    compute_energy_intensity,
    compute_carbon_intensity,
    compute_peak_demand,
    compute_energy_cost_per_day,
    compute_cop,
    compute_iso_50001_score,
    compute_optimization_score,
    detect_anomalies,
    get_load_dispatch_recommendations,
    get_asset_energy_attribution,
    compute_esg_metrics,
    compute_energy_forecast,
    get_top_consumers,
    get_hourly_load_profile,
    generate_insights,
)

router = APIRouter(prefix="/agents/energy", tags=["Energy Optimization"])


def _build_envelope(plant_key: str, payload: dict, sources: list[str], confidence_score: float = 0.87) -> dict:
    """Build standard contract envelope for energy responses."""
    envelope = ContractEnvelope(
        metadata=Metadata(plant_key=plant_key),
        lineage=Lineage(sources=sources),
        payload=payload,
        confidence=Confidence(
            score=confidence_score,
            factors=["synthetic_data", "rule_based_engine", "historical_baseline"],
        ),
    )
    return envelope.model_dump()


@router.get("/context")
def energy_context(plant_key: str = Query(default="us", description="Plant identifier")):
    """
    Main energy agent context endpoint.
    Returns: energy KPIs, metrics, insights, chart data, anomalies, recommendations.
    FR-004.1 through FR-004.10 implementation.
    """
    # Core KPIs
    energy_kpis = {
        "energy_intensity": compute_energy_intensity(),
        "energy_intensity_target": 4.1,
        "carbon_intensity": compute_carbon_intensity(),
        "carbon_intensity_target": 2.0,
        "peak_demand_kw": compute_peak_demand(),
        "peak_demand_target": 800.0,
        "energy_cost_per_day": compute_energy_cost_per_day(),
        "cop": compute_cop(),
        "cop_target": 4.0,
        "iso_50001_score": compute_iso_50001_score(),
        "optimization_score": compute_optimization_score(),
        "autonomous_dispatch_rate": 72.4,  # % of recommendations auto-approved
    }

    # Anomalies linked to equipment health
    anomalies = detect_anomalies()

    # Load dispatch recommendations
    recommendations = get_load_dispatch_recommendations()

    # Asset-level attribution
    attributions = get_asset_energy_attribution()

    # ESG metrics
    esg = compute_esg_metrics()

    # AI insights
    insights = generate_insights()

    # Chart data
    charts = {
        "top_consumers": get_top_consumers(),
        "hourly_load_profile": get_hourly_load_profile(),
    }

    payload = {
        "energy": energy_kpis,
        "anomalies": anomalies,
        "recommendations": recommendations,
        "attributions": attributions,
        "esg": esg,
        "insights": insights,
        "charts": charts,
    }

    return _build_envelope(
        plant_key=plant_key,
        payload=payload,
        sources=[
            "energy_assets.csv",
            "energy_hourly.csv",
            "utilities.csv",
            "machines.csv",
            "twin_kpis.csv",
            "production_orders.csv",
        ],
        confidence_score=0.87,
    )


@router.get("/kpis")
def energy_kpis(plant_key: str = Query(default="us")):
    """Get all energy KPIs."""
    kpis = {
        "energy_intensity": compute_energy_intensity(),
        "energy_intensity_target": 4.1,
        "energy_intensity_unit": "kWh/unit",
        "carbon_intensity": compute_carbon_intensity(),
        "carbon_intensity_target": 2.0,
        "carbon_intensity_unit": "lb CO2/unit",
        "peak_demand_kw": compute_peak_demand(),
        "peak_demand_target": 800.0,
        "peak_demand_unit": "kW",
        "energy_cost_per_day": compute_energy_cost_per_day(),
        "energy_cost_unit": "$/day",
        "cop": compute_cop(),
        "cop_target": 4.0,
        "iso_50001_score": compute_iso_50001_score(),
        "optimization_score": compute_optimization_score(),
    }
    return _build_envelope(plant_key, kpis, ["energy_hourly.csv", "utilities.csv", "production_orders.csv"])


@router.get("/anomalies")
def energy_anomalies(plant_key: str = Query(default="us")):
    """
    FR-004.3: Detect energy anomalies and link root cause to equipment health.
    """
    anomalies = detect_anomalies()
    return _build_envelope(
        plant_key,
        {"anomalies": anomalies, "count": len(anomalies)},
        ["energy_assets.csv", "machines.csv", "utilities.csv"],
        confidence_score=0.82,
    )


@router.get("/dispatch")
def load_dispatch(plant_key: str = Query(default="us")):
    """
    FR-004.4: Load dispatch recommendations with approve/reject workflow.
    """
    recommendations = get_load_dispatch_recommendations()
    total_savings = sum(r["savings_cost_daily"] for r in recommendations)
    return _build_envelope(
        plant_key,
        {
            "recommendations": recommendations,
            "count": len(recommendations),
            "total_daily_savings": round(total_savings, 2),
        },
        ["energy_assets.csv", "energy_hourly.csv"],
        confidence_score=0.79,
    )


@router.post("/dispatch/{recommendation_id}/approve")
def approve_dispatch(recommendation_id: str, plant_key: str = Query(default="us")):
    """Approve a load dispatch recommendation."""
    recommendations = get_load_dispatch_recommendations()
    for rec in recommendations:
        if rec["id"] == recommendation_id:
            rec["status"] = "approved"
            return _build_envelope(
                plant_key,
                {"recommendation": rec, "action": "approved"},
                ["energy_assets.csv"],
            )
    return {"error": f"Recommendation {recommendation_id} not found"}


@router.post("/dispatch/{recommendation_id}/reject")
def reject_dispatch(recommendation_id: str, plant_key: str = Query(default="us")):
    """Reject a load dispatch recommendation."""
    recommendations = get_load_dispatch_recommendations()
    for rec in recommendations:
        if rec["id"] == recommendation_id:
            rec["status"] = "rejected"
            return _build_envelope(
                plant_key,
                {"recommendation": rec, "action": "rejected"},
                ["energy_assets.csv"],
            )
    return {"error": f"Recommendation {recommendation_id} not found"}


@router.get("/attribution")
def asset_attribution(plant_key: str = Query(default="us")):
    """
    FR-004.5: Asset-level energy attribution and cost allocation.
    """
    attributions = get_asset_energy_attribution()
    total_kw = sum(a["current_kw"] for a in attributions)
    return _build_envelope(
        plant_key,
        {
            "attributions": attributions,
            "total_plant_kw": total_kw,
            "total_daily_cost": round(total_kw * 24 * 0.12, 2),
        },
        ["energy_assets.csv", "machines.csv", "utilities.csv"],
    )


@router.get("/esg")
def esg_metrics(plant_key: str = Query(default="us")):
    """
    FR-004.6: ESG metrics — CO2 tracking, solar offset, grid carbon.
    """
    esg = compute_esg_metrics()
    return _build_envelope(
        plant_key,
        esg,
        ["energy_hourly.csv", "production_orders.csv"],
        confidence_score=0.91,
    )


@router.get("/forecast")
def energy_forecast(
    plant_key: str = Query(default="us"),
    period: str = Query(default="24h", description="Forecast period: 24h, 7d, or 30d"),
):
    """
    FR-004.7: Forecast lab — 24h/7d/30d load and cost forecasting.
    """
    forecast = compute_energy_forecast(period)
    return _build_envelope(
        plant_key,
        forecast,
        ["energy_hourly.csv", "twin_kpis.csv"],
        confidence_score=forecast["confidence_pct"] / 100,
    )


@router.get("/insights")
def energy_insights(plant_key: str = Query(default="us")):
    """
    AI-generated energy insights based on current data analysis.
    """
    insights = generate_insights()
    return _build_envelope(
        plant_key,
        {"insights": insights, "count": len(insights)},
        ["energy_assets.csv", "energy_hourly.csv", "utilities.csv", "machines.csv"],
        confidence_score=0.84,
    )


@router.get("/charts/consumers")
def chart_top_consumers(plant_key: str = Query(default="us")):
    """
    FR-004.9: Top 6 energy consumers by asset in bar chart data.
    """
    consumers = get_top_consumers()
    return _build_envelope(plant_key, {"chart_data": consumers}, ["energy_assets.csv"])


@router.get("/charts/load-profile")
def chart_load_profile(plant_key: str = Query(default="us")):
    """24-hour load profile chart data."""
    profile = get_hourly_load_profile()
    return _build_envelope(plant_key, {"chart_data": profile}, ["energy_hourly.csv"])
