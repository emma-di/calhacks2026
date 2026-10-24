"""Bounded JSONL logs of recognition decisions, never raw audio or transcripts."""
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
import uuid

class DecisionLog:
    def __init__(self,path,max_bytes=5_000_000,backups=2):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.session_id=str(uuid.uuid4())
        self.logger=logging.getLogger('audio-decisions-'+self.session_id)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate=False
        self.handler=RotatingFileHandler(self.path,maxBytes=max_bytes,backupCount=backups,encoding='utf-8')
        self.handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(self.handler)

    def write(self,record):
        self.logger.info(json.dumps(dict(log_version=1,session_id=self.session_id,
            logged_at_ms=int(time.time()*1000),**record),allow_nan=False))

    def close(self):
        self.logger.removeHandler(self.handler)
        self.handler.close()
