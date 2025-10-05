from pydantic import BaseModel
from typing import Optional, Any


class Image(BaseModel):
    cam_num: int
    cam_info: str # frontal, gate
    gate_pos: list[int] | int # list if frontal
    image_bytes: str

class ProcRequest(BaseModel):
    images: list[dict[str, Any]]
