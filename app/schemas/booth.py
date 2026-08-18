from pydantic import BaseModel, ConfigDict


class BoothBase(BaseModel):
    boothNo: str
    location: str
    incharge: str
    voters: int = 0
    slips: int = 0
    coverage: str = "0%"


class BoothCreate(BoothBase):
    pass


class BoothResponse(BoothBase):
    model_config = ConfigDict(from_attributes=True)
