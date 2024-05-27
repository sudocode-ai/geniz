import uuid
from datetime import datetime, timedelta

from pydantic import BaseModel

from .util import PersistStateToFile


class RoundInfo(BaseModel, PersistStateToFile):
    created: datetime = datetime.now()
    round: int = 1
    session_id: str = str(uuid.uuid4())

    def dead(self):
        if datetime.now() - self.created > timedelta(minutes=25):
            return True
        return False


def get_round_info():
    round_info = RoundInfo().load()
    return round_info

def get_round_filename_prefix():
    round_info = RoundInfo().load()
    return f'round_{round_info.round}'