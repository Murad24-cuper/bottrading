"""Project-local data and log paths with optional environment overrides."""
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv


def project_paths(root: str | Path):
    root=Path(root).resolve()
    load_dotenv(root/'.env',override=False)
    try: config=yaml.safe_load((root/'config.yaml').read_text(encoding='utf-8')) or {}
    except (OSError,yaml.YAMLError): config={}
    raw=config.get('paths',{}) if isinstance(config,dict) else {}
    def resolve(env_key,key,default):
        path=Path(os.getenv(env_key,'').strip() or raw.get(key,default))
        return path if path.is_absolute() else root/path
    return resolve('BOT_DATA_DIR','data_dir','data'),resolve('BOT_LOG_DIR','logs_dir','logs')
