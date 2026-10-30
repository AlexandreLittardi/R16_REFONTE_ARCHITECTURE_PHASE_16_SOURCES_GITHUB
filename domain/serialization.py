"""Pure serialization of project-native structures and stable SHA-256 IDs."""
import datetime as dt
import hashlib
import json

def serial(value):
    if isinstance(value,dict):
        return {(','.join(map(str,k)) if isinstance(k,tuple) else str(k)):serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,set)):return [serial(v) for v in value]
    if isinstance(value,(dt.datetime,dt.date)):return value.isoformat()
    return value

def fingerprint(value):
    return hashlib.sha256(json.dumps(serial(value),sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()

