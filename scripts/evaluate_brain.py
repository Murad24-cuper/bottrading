"""Run the frozen brain acceptance gate on a prepared final-test Parquet file."""
from pathlib import Path
import sys
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.config import load_settings
from src.brain.evaluation import evaluate_test_period,render_report
from src.parquet_compat import read_parquet

def main():
    settings=load_settings(require_credentials=False); root=settings.root
    source=settings.data_dir/'brain'/'test_predictions.parquet'
    if not source.exists(): raise SystemExit(f'No final test predictions at {source}; build/train/validate first. Brain remains shadow-only.')
    result=evaluate_test_period(read_parquet(source),settings.config.get('brain',{}))
    report_dir=root/'reports'; report_dir.mkdir(parents=True,exist_ok=True)
    target=report_dir/f"brain_eval_{pd.Timestamp.now(tz='UTC').date().isoformat()}.md"
    target.write_text(render_report(result),encoding='utf-8')
    gate_path=settings.data_dir/'brain'/'gate.json'; gate_path.parent.mkdir(parents=True,exist_ok=True)
    gate_path.write_text(json.dumps({'status':'PASS' if result['passed'] else 'FAIL','evaluated_at':pd.Timestamp.now(tz='UTC').isoformat(),'reasons':result['reasons'],'metrics':result},indent=2,default=str),encoding='utf-8')
    print(f"Gate={'PASS' if result['passed'] else 'FAIL'}; report={target}")
    print('Reasons: '+('; '.join(result['reasons']) if result['reasons'] else 'all criteria passed'))
    return 0 if result['passed'] else 2

if __name__=='__main__': raise SystemExit(main())
