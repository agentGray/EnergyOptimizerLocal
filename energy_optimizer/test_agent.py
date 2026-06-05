"""
Energy Optimizer Agent — Integration Test
Validates all KPI calculations, anomaly detection, and data flows.
Runs without FastAPI/uvicorn (uses only stdlib + db layer).

Usage: python -m energy_optimizer.test_agent
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from energy_optimizer.data.db import reset_db, query, query_single, get_engine_info
from energy_optimizer.data.loader import load_all
from energy_optimizer.semantic import kpi_engine


def test_data_loading():
    """Test all CSV data loads correctly."""
    print("TEST: Data Loading")
    
    assets = query("SELECT COUNT(*) as cnt FROM energy_assets")
    assert assets[0]["cnt"] == 6, f"Expected 6 energy assets, got {assets[0]['cnt']}"
    
    hourly = query("SELECT COUNT(*) as cnt FROM energy_hourly")
    assert hourly[0]["cnt"] == 12, f"Expected 12 hourly records, got {hourly[0]['cnt']}"
    
    utilities = query("SELECT COUNT(*) as cnt FROM utilities")
    assert utilities[0]["cnt"] == 4, f"Expected 4 utilities, got {utilities[0]['cnt']}"
    
    machines = query("SELECT COUNT(*) as cnt FROM machines")
    assert machines[0]["cnt"] == 8, f"Expected 8 machines, got {machines[0]['cnt']}"
    
    twin = query("SELECT COUNT(*) as cnt FROM twin_kpis")
    assert twin[0]["cnt"] == 8, f"Expected 8 twin KPIs, got {twin[0]['cnt']}"
    
    orders = query("SELECT COUNT(*) as cnt FROM production_orders")
    assert orders[0]["cnt"] == 4, f"Expected 4 production orders, got {orders[0]['cnt']}"
    
    print("  PASS: All 6 tables loaded with correct row counts")


def test_energy_intensity():
    """Test KPI-005: Energy Intensity."""
    print("TEST: Energy Intensity (KPI-005)")
    intensity = kpi_engine.compute_energy_intensity()
    assert 3.0 < intensity < 10.0, f"Energy intensity {intensity} out of expected range"
    print(f"  PASS: Energy Intensity = {intensity} kWh/unit (target: 4.1)")


def test_carbon_intensity():
    """Test KPI-010: Carbon Intensity."""
    print("TEST: Carbon Intensity (KPI-010)")
    carbon = kpi_engine.compute_carbon_intensity()
    assert carbon > 0, f"Carbon intensity should be positive, got {carbon}"
    print(f"  PASS: Carbon Intensity = {carbon} lb CO2/unit (target: <2.0)")


def test_peak_demand():
    """Test KPI-015: Peak Demand."""
    print("TEST: Peak Demand (KPI-015)")
    peak = kpi_engine.compute_peak_demand()
    assert peak == 1612.0, f"Expected peak 1612 kW, got {peak}"
    print(f"  PASS: Peak Demand = {peak} kW (target: <800)")


def test_energy_cost():
    """Test KPI-025: Energy Cost."""
    print("TEST: Energy Cost per Day (KPI-025)")
    cost = kpi_engine.compute_energy_cost_per_day()
    assert cost > 0, f"Cost should be positive, got {cost}"
    # 29066 kWh * $0.12 = ~$3487.92
    assert 3000 < cost < 4000, f"Cost {cost} out of expected range"
    print(f"  PASS: Energy Cost = ${cost}/day")


def test_cop():
    """Test KPI-028: COP."""
    print("TEST: COP (KPI-028)")
    cop = kpi_engine.compute_cop()
    assert 2.0 < cop < 6.0, f"COP {cop} out of expected range"
    # Chiller health=67%, so COP = 5.2 * 0.67 = ~3.48
    print(f"  PASS: COP = {cop} (target: >4.0)")


def test_iso_50001():
    """Test ISO 50001 compliance score."""
    print("TEST: ISO 50001 Score")
    score = kpi_engine.compute_iso_50001_score()
    assert 0 <= score <= 100, f"ISO score {score} out of range"
    print(f"  PASS: ISO 50001 Score = {score}%")


def test_optimization_score():
    """Test AI Optimization Score."""
    print("TEST: Optimization Score")
    score = kpi_engine.compute_optimization_score()
    assert 0 <= score <= 100, f"Optimization score {score} out of range"
    print(f"  PASS: Optimization Score = {score}")


def test_anomaly_detection():
    """Test anomaly detection linked to equipment health."""
    print("TEST: Anomaly Detection (FR-004.3)")
    anomalies = kpi_engine.detect_anomalies()
    assert len(anomalies) >= 1, "Expected at least 1 anomaly"
    
    for a in anomalies:
        assert "asset_id" in a
        assert "deviation_pct" in a
        assert "linked_health_issue" in a
        assert a["severity"] in ("low", "medium", "high", "critical")
        assert a["deviation_pct"] > 0
    
    # MCH-03 (health=38) and MCH-06 (health=32) and CMP-001 (health=34) should be flagged
    flagged_ids = {a["asset_id"] for a in anomalies}
    assert "MCH-03" in flagged_ids, "MCH-03 (CNC, health=38%) should have anomaly"
    assert "MCH-06" in flagged_ids, "MCH-06 (Welding Robot B, health=32%) should have anomaly"
    
    print(f"  PASS: {len(anomalies)} anomalies detected, all linked to equipment health")
    for a in anomalies:
        print(f"    - {a['asset_name']}: +{a['deviation_pct']}% waste={a['energy_waste_kw']}kW [{a['severity']}]")


def test_load_dispatch():
    """Test load dispatch recommendations."""
    print("TEST: Load Dispatch (FR-004.4)")
    recs = kpi_engine.get_load_dispatch_recommendations()
    assert len(recs) == 3, f"Expected 3 recommendations (3 shiftable assets), got {len(recs)}"
    
    for r in recs:
        assert r["savings_kw"] > 0
        assert r["savings_cost_daily"] > 0
        assert r["status"] == "pending"
    
    total_savings = sum(r["savings_cost_daily"] for r in recs)
    print(f"  PASS: {len(recs)} dispatch recommendations, total savings: ${total_savings:.2f}/day")


def test_asset_attribution():
    """Test per-asset energy attribution."""
    print("TEST: Asset Attribution (FR-004.5)")
    attrs = kpi_engine.get_asset_energy_attribution()
    assert len(attrs) == 6, f"Expected 6 assets, got {len(attrs)}"
    
    total_pct = sum(a["pct_of_total"] for a in attrs)
    assert 99.0 <= total_pct <= 101.0, f"Attribution percentages should sum to ~100%, got {total_pct}"
    
    # Check anomaly flags are set
    flagged = [a for a in attrs if a["anomaly_flag"]]
    assert len(flagged) >= 1, "At least 1 asset should be flagged"
    
    print(f"  PASS: {len(attrs)} assets attributed, {len(flagged)} with anomaly flag, total={total_pct:.1f}%")


def test_esg_metrics():
    """Test ESG/Carbon tracking."""
    print("TEST: ESG Metrics (FR-004.6)")
    esg = kpi_engine.compute_esg_metrics()
    
    assert esg["total_co2_today_lb"] > 0
    assert esg["co2_per_unit"] > 0
    assert esg["solar_offset_kwh"] == 660.0  # 120kW * 5.5h
    assert esg["grid_carbon_intensity"] > 0
    assert 0 < esg["renewable_pct"] < 100
    
    print(f"  PASS: CO2={esg['total_co2_today_lb']:.0f}lb, solar={esg['solar_offset_kwh']}kWh, renewable={esg['renewable_pct']}%")


def test_forecast():
    """Test energy forecasting."""
    print("TEST: Energy Forecast (FR-004.7)")
    
    for period in ["24h", "7d", "30d"]:
        fc = kpi_engine.compute_energy_forecast(period)
        assert fc["period"] == period
        assert fc["predicted_kwh"] > 0
        assert fc["predicted_cost"] > 0
        assert fc["predicted_peak_kw"] > 0
        assert 50 <= fc["confidence_pct"] <= 100
    
    fc_24h = kpi_engine.compute_energy_forecast("24h")
    fc_7d = kpi_engine.compute_energy_forecast("7d")
    assert fc_7d["predicted_kwh"] > fc_24h["predicted_kwh"], "7d forecast should exceed 24h"
    
    print(f"  PASS: All forecast periods valid (24h/7d/30d)")


def test_top_consumers():
    """Test top consumers chart data."""
    print("TEST: Top Consumers Chart (FR-004.9)")
    consumers = kpi_engine.get_top_consumers()
    assert len(consumers) == 6, f"Expected 6 consumers, got {len(consumers)}"
    
    # Should be sorted by kW descending
    values = [c["value"] for c in consumers]
    assert values == sorted(values, reverse=True), "Should be sorted descending"
    assert consumers[0]["label"] == "Welding Robot B"  # 164kW is highest
    
    print(f"  PASS: {len(consumers)} consumers, top={consumers[0]['label']} ({consumers[0]['value']}kW)")


def test_hourly_profile():
    """Test hourly load profile chart data."""
    print("TEST: Hourly Load Profile")
    profile = kpi_engine.get_hourly_load_profile()
    assert len(profile) == 12, f"Expected 12 data points, got {len(profile)}"
    
    print(f"  PASS: {len(profile)} hourly data points")


def test_insights():
    """Test AI insight generation."""
    print("TEST: AI Insights")
    insights = kpi_engine.generate_insights()
    assert len(insights) >= 3, f"Expected at least 3 insights, got {len(insights)}"
    
    categories = {i["category"] for i in insights}
    priorities = {i["priority"] for i in insights}
    
    print(f"  PASS: {len(insights)} insights generated")
    print(f"    Categories: {categories}")
    print(f"    Priorities: {priorities}")


def main():
    print("=" * 70)
    print("  ENERGY OPTIMIZER AGENT — INTEGRATION TEST SUITE")
    print(f"  DB Engine: {get_engine_info()}")
    print("=" * 70)
    print()
    
    # Setup
    reset_db()
    load_all()
    print()
    
    # Run tests
    tests = [
        test_data_loading,
        test_energy_intensity,
        test_carbon_intensity,
        test_peak_demand,
        test_energy_cost,
        test_cop,
        test_iso_50001,
        test_optimization_score,
        test_anomaly_detection,
        test_load_dispatch,
        test_asset_attribution,
        test_esg_metrics,
        test_forecast,
        test_top_consumers,
        test_hourly_profile,
        test_insights,
    ]
    
    passed = 0
    failed = 0
    
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1
        print()
    
    print("=" * 70)
    print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
