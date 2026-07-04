# trading-lab

Proyecto separado para construir un sistema **ético** de trading cripto por fases:
- Fase 1: CEX spot (Bitso → Binance), **sin apalancamiento**, semi-automático (propuestas + aprobación humana)
- Validación obligatoria: **backtest + paper trading** antes de live
- Seguridad: API keys **trade-only**, **sin withdraw**, whitelist de IP si se puede

> Nota: No existe “profit siempre”. El objetivo es construir un sistema con **expectativa positiva** y **control de riesgo**.

## Quickstart (Windows)
```powershell
cd .\trading-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m trading_lab.cli.main init-db
python -m trading_lab.cli.main scan --exchange binance
python -m trading_lab.cli.main list-proposals
```

## Comandos
- `init-db`: crea tablas SQLite
- `scan`: baja velas diarias (OHLCV) y crea propuestas (solo señales por ahora)
- `list-proposals`: lista propuestas pendientes

## Próximo
- Aprobación/rechazo desde CLI
- Paper broker (fills simulados)
- Conector live (trade-only) con guardrails
