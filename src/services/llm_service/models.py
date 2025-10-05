from pydantic import BaseModel
from typing import Optional


class ProcRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    timestamp: Optional[int] = None
    bus_num: Optional[str] = None
    image_bytes: str
    cam_num: Optional[int] = None
    cam_info: Optional[str] = None
    gate_pos: Optional[list[int] | int] = None # list if frontal