# Backend

Server-side code for the SBC (Single-Board Computer, e.g. Raspberry Pi, Odroid) server.

**Status:** planned — Phase 4 (data pipeline + dashboard) and Phase 6 (ML models).

## Structure (planned)

```
backend/
├── api/
│   ├── main.py           ← FastAPI app
│   ├── ingest.py         ← CSV upload + deduplication
│   └── predict.py        ← ML inference endpoints
├── models/
│   ├── watering_rf.py    ← Random Forest training
│   └── forecast_lstm.py  ← LSTM training + TFLite export
├── data/                 ← gitignored — CSV files, databases
├── pyproject.toml
└── README.md
```

## Stack

- **API:** FastAPI (Python)
- **Database:** TinyDB (prototype) → InfluxDB v1 (production)
- **Dashboard:** Grafana
- **ML:** scikit-learn (Random Forest), PyTorch (LSTM)

## See also

Full backend and ML design: [docs/](../docs/)
