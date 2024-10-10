import datetime
import hashlib

from pydantic import BaseModel, Field

from ..modeus import schema as modeus_schema
from ..netology import schema as netology_schema


class BulkResponse(BaseModel):
    netology: netology_schema.SerializedEvents
    modeus: list[modeus_schema.FullEvent]


class CalendarResponse(BulkResponse):
    cached_at: datetime.datetime = Field(default_factory=datetime.datetime.now, alias="cached_at")

    def get_hash(self) -> str:
        dump = BulkResponse(**self.model_dump(by_alias=True)).model_dump_json(by_alias=True)
        return hashlib.md5(dump.encode()).hexdigest()


class RefreshedCalendarResponse(CalendarResponse):
    changed: bool
