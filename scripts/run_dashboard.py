"""Launch the local SQLite-only Streamlit dashboard."""
from pathlib import Path
import subprocess,sys

def main():
    root=Path(__file__).resolve().parents[1]
    app=root/'src'/'dashboard'/'app.py'
    return subprocess.call([sys.executable,'-m','streamlit','run',str(app),'--server.address','127.0.0.1','--server.port','8501','--server.headless','true'],cwd=root)

if __name__=='__main__': raise SystemExit(main())
