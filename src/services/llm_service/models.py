from pydantic import BaseModel
from typing import Optional


class ProcRequest(BaseModel):
    lat: float
    lon: float
    timestamp: int
    bus_num: str
    image: str
    cam_num: int
