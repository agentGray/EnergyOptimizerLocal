# Energy Optimizer Agent — Phase 1 (Local)

**Contract:** CON-004 | **Domain:** Energy & ESG  
**Tagline:** Detects energy inefficiency by asset and links to equipment condition

## Quick Start

```bash
# From project root:
pip install fastapi uvicorn duckdb pydantic
python -m uvicorn energy_optimizer.main:app --port 8000 --reload
```

Open: http://localhost:8000/docs

## Architecture

```
energy_optimizer/
├── main.py                    # FastAPI app — 10 endpoints
├── requirements.txt           # fastapi, uvicorn, duckdb, pydantic
├── start.sh                   # One-command startup
├── data/
│   ├── db.py                  # DuckDB connection helper
│   └── loader.py              # CSV → DuckDB loader (6 tables)
├── semantic/
│   ├── models.py              # Pydantic models + ContractEnvelope
│   └── kpi_engine.py          # KPI calculations + anomaly detection
└── agents/
    └── energy/
        └── routes.py          # All API endpoints
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/energy/context` | GET | Full energy context (KPIs + anomalies + insights + charts) |
| `/agents/energy/kpis` | GET | Core energy KPIs |
| `/agents/energy/anomalies` | GET | Energy anomalies linked to equipment health |
| `/agents/energy/dispatch` | GET | Load dispatch recommendations |
| `/agents/energy/dispatch/{id}/approve` | POST | Approve a dispatch recommendation |
| `/agents/energy/dispatch/{id}/reject` | POST | Reject a dispatch recommendation |
| `/agents/energy/attribution` | GET | Per-asset energy attribution |
| `/agents/energy/esg` | GET | ESG/Carbon metrics |
| `/agents/energy/forecast` | GET | Energy forecast (24h/7d/30d) |
| `/agents/energy/insights` | GET | AI-generated energy insights |
| `/agents/energy/charts/consumers` | GET | Top 6 consumers chart data |
| `/agents/energy/charts/load-profile` | GET | 24h load profile chart data |
| `/healthz` | GET | Liveness probe |
| `/readyz` | GET | Readiness probe |
| `/reload` | POST | Reload CSV data (dev utility) |

## KPIs Computed

| KPI ID | Name | Formula | Target |
|--------|------|---------|--------|
| KPI-005 | Energy Intensity | Total kWh / Units produced | 4.1 kWh/unit |
| KPI-010 | Carbon Intensity | Total CO2e / Units produced | < 2.0 lb/unit |
| KPI-015 | Peak Demand | Max kW in billing period | < 800 kW |
| KPI-025 | Energy Cost | Total energy spend per day | Minimize |
| KPI-028 | COP | Cooling output / Electrical input | > 4.0 |

## Data Sources (CSV)

| File | What it provides |
|------|-----------------|
| `energy_assets.csv` | 6 assets with rated power, shiftable flag |
| `energy_hourly.csv` | 24-hour plant load profile (12 data points) |
| `utilities.csv` | Compressor, chiller, hydraulic, pump health |
| `machines.csv` | 8 machines with OEE, health, vibration |
| `twin_kpis.csv` | Plant energy actual vs digital twin predicted |
| `production_orders.csv` | Production orders for units produced |

## Phase Roadmap

- **Phase 1 (Current):** FastAPI + DuckDB on localhost. Synthetic CSV data. No auth.
- **Phase 2:** FastAPI on AKS + PostgreSQL + ADX. Azure AD auth.
- **Phase 3:** Live enterprise data via connectors (Modbus/BACnet, IoT Hub).
