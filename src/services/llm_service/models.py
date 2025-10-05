from pydantic import BaseModel, Field
from typing import Optional, Union, List

class ProcRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    timestamp: Optional[int] = None
    bus_num: Optional[str] = None
    image_bytes: str
    cam_num: Optional[int] = None
    cam_info: Optional[str] = None
    gate_pos: Optional[list[int] | int] = None # list if frontal

class BusAnalysisResponse(BaseModel):
    load: str = Field(description="Estimated bus occupancy. One of three possible states: free, average, or full")
    people_num: int = Field(description="Actual number of people")
    free_entrance: Union[int, List[int]] = Field(description="Freest entrance(s). If gate_num is a single number, return that number or 0 if all exits are full. If gate_num is an array, return an array of freest entrances in order of preference or [0] if all exits are full.")
    free_seats: int = Field(description="Actual number of free seats in bus")