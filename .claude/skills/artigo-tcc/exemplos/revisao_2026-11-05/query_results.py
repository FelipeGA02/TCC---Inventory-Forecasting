# -*- coding: utf-8 -*-
"""Extrai do SQLite local o resultado do último treino concluído (solução definitiva, E10)."""
import json
import sqlite3
import sys

db = sys.argv[1]
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
job = con.execute("select * from forecast_jobs where status='done' order by id desc limit 1").fetchone()
print("JOB", dict((k, job[k]) for k in job.keys() if k not in ("config",)))
print("CONFIG", job["config"])
rows = con.execute("""
  select sm.*, p.name as pname, c.name as cname
  from series_models sm
  left join products p on p.code = sm.product_code
  left join categories c on c.id = sm.category_id
  where sm.job_id = ? order by sm.unit_id, sm.level, sm.series_key""", (job["id"],)).fetchall()
for r in rows:
    m = json.loads(r["metrics"]) if r["metrics"] else {}
    print("----", r["unit_id"], r["level"], r["cname"] or "", r["pname"] or "", r["product_code"] or "")
    print("   status", r["status"], "ordem", r["sarimax_order"], r["seasonal_order"], "aic", r["aic"],
          "mase", r["mase"], "cob", r["ci95_coverage_pct"], "treino", r["train_start"], r["train_end"])
    print("   metrics", json.dumps(m, ensure_ascii=False)[:900])
    if r["message"]:
        print("   msg", r["message"][:300])
bt = con.execute("""select min(origin_date), max(origin_date), min(day), max(day), count(*)
  from series_backtest_points b join series_models s on s.id=b.model_id where s.job_id=?""", (job["id"],)).fetchone()
print("BACKTEST", tuple(bt))
fc = con.execute("""select min(forecast_date), max(forecast_date) from series_forecasts f
  join series_models s on s.id=f.model_id where s.job_id=?""", (job["id"],)).fetchone()
print("FORECAST", tuple(fc))
