"""Print and save observational feature outcome evidence."""
from __future__ import annotations
import argparse,csv,sqlite3,sys
from datetime import datetime,timezone
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.analysis.feature_impact import analyze_feature_impact,closed_trade_features

def main():
    parser=argparse.ArgumentParser(description='Analyze stored feature outcomes; no trading decisions are changed.')
    parser.add_argument('--db',default=None); parser.add_argument('--output',default=None); args=parser.parse_args()
    config=yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))
    db=Path(args.db) if args.db else Path(config.get('db_path','data/bot.db'))
    if not db.is_absolute(): db=ROOT/db
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=5) as conn:
        conn.execute('PRAGMA busy_timeout=5000'); trades=closed_trade_features(conn)
    report=analyze_feature_impact(trades)
    output=Path(args.output) if args.output else ROOT/'reports'/f"feature_impact_{datetime.now(timezone.utc).date().isoformat()}.csv"
    output.parent.mkdir(parents=True,exist_ok=True)
    fields=['feature','trades','win_rate','expectancy','baseline_win_rate','baseline_expectancy','win_rate_difference','ci90_low','ci90_high','meaningful']
    with output.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader(); writer.writerows(report)
    print(f'Closed trades: {len(trades)} · features: {len(report)} · CSV: {output}')
    for row in report[:30]:
        proven='yes' if row['meaningful'] else 'not enough evidence' if row['trades']<30 else 'no'
        print(f"{row['feature']} | n={row['trades']} | win={row['win_rate']:.1%} | expectancy={row['expectancy']:.4f} | delta={row['win_rate_difference']:+.1%} | CI90=({row['ci90_low']},{row['ci90_high']}) | {proven}")
    return 0

if __name__=='__main__': raise SystemExit(main())
