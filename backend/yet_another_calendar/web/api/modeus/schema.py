import datetime
import uuid
from typing import Optional, Self

from pydantic import BaseModel, Field, computed_field, model_validator, field_validator
from starlette.responses import Response

from . import integration
from yet_another_calendar.settings import settings


async def get_cookies_from_headers() -> str | Response:
    return await integration.login(settings.modeus_username, settings.modeus_password)


class ModeusCreds(BaseModel):
    """Modeus creds."""

    username: str
    password: str = Field(repr=False)

class ModeusTimeBody(BaseModel):
    time_min: datetime.datetime = Field(alias="timeMin", examples=["2024-09-23T00:00:00+03:00"])
    time_max: datetime.datetime = Field(alias="timeMax", examples=["2024-09-29T23:59:59+03:00"])

# noinspection PyNestedDecorators
class ModeusEventsBody(ModeusTimeBody):
    """Modeus search events body."""
    size: int = Field(default=50)
    attendee_person_id: list[uuid.UUID] = Field(alias="attendeePersonId",
                                                default=["d69c87c8-aece-4f39-b6a2-7b467b968211"])

    @field_validator("time_min")
    @classmethod
    def validate_time_min(cls, time_min: datetime.datetime) -> datetime.datetime:
        if time_min.weekday() != 0:
            raise ValueError("Weekday time_min must be Monday.")
        if time_min.second or time_min.hour or time_min.minute:
            raise ValueError("Time must me 00:00:00.")
        return time_min

    @field_validator("time_max")
    @classmethod
    def validate_time_max(cls, time_max: datetime.datetime) -> datetime.datetime:
        if time_max.weekday() != 6:
            raise ValueError("Weekday time_min must be Sunday.")
        if time_max.hour != 23 or time_max.second != 59 or time_max.minute != 59:
            raise ValueError("Time must me 23:59:59.")
        return time_max

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        delta = self.time_max - self.time_min
        if delta.days != 6:
            raise ValueError("Defence between dates must be 7 days.")
        return self


class FullModeusPersonSearch(BaseModel):
    """Modeus search events body."""
    full_name: str = Field(alias="fullName", examples=["Комаев Азамат Олегович"])
    sort: str = Field(default="+fullName")
    size: int = Field(default=10)
    page: int = Field(default=0)


class Location(BaseModel):
    id: uuid.UUID = Field(alias="eventId")
    custom_location: Optional[str] = Field(alias="customLocation", default=None)

    @computed_field  # type: ignore
    @property
    def is_lxp(self) -> float:
        if not self.custom_location:
            return True
        return self.custom_location == 'LXP'


class Event(BaseModel):
    name: str = Field(alias="name")
    name_short: Optional[str] = Field(alias="nameShort", default=None)
    description: Optional[str] = Field(alias="description")
    start_time: datetime.datetime = Field(alias="start")
    end_time: datetime.datetime = Field(alias="end")
    id: uuid.UUID


class Href(BaseModel):
    href: str

    @computed_field  # type: ignore
    @property
    def id(self) -> uuid.UUID:
        return uuid.UUID(self.href.replace('/', ''))


class Link(BaseModel):
    self: Href
    event: Href
    person: Href


class Attender(BaseModel):
    links: Link = Field(alias="_links")


class ShortPerson(BaseModel):
    id: uuid.UUID
    full_name: str = Field(alias="fullName")


class CalendarEmbedded(BaseModel):
    events: list[Event] = Field(alias="events")
    locations: list[Location] = Field(alias="event-locations")
    attendees: list[Attender] = Field(alias="event-attendees")
    people: list[ShortPerson] = Field(alias="persons")


class FullEvent(Event, Location):
    teacher_full_name: str


class ModeusCalendar(BaseModel):
    """Modeus calendar response."""

    embedded: CalendarEmbedded = Field(alias="_embedded")

    def serialize_modeus_response(self) -> list[FullEvent]:
        """Serialize calendar api response from modeus."""
        locations = {location.id: location for location in self.embedded.locations}
        teachers = {teacher.id: teacher for teacher in self.embedded.people}
        teachers_with_events = {teacher.links.event.id: teacher.links for teacher in self.embedded.attendees}
        full_events = []
        for event in self.embedded.events:
            try:
                teacher_event = teachers_with_events[event.id]
                teacher = teachers[teacher_event.person.id]
                teacher_full_name = teacher.full_name
            except KeyError:
                teacher_full_name = 'unknown'
            location = locations[event.id]
            if location.is_lxp:
                continue
            full_events.append(FullEvent(**{
                "teacher_full_name": teacher_full_name,
                **event.model_dump(by_alias=True), **location.model_dump(by_alias=True),
            }))
        return full_events


class StudentsSpeciality(BaseModel):
    id: uuid.UUID = Field(alias="personId")
    flow_code: Optional[str] = Field(alias="flowCode")
    learning_start_date: Optional[datetime.datetime] = Field(alias="learningStartDate")
    learning_end_date: Optional[datetime.datetime] = Field(alias="learningEndDate")
    specialty_code: Optional[str] = Field(alias="specialtyCode")
    specialty_name: Optional[str] = Field(alias="specialtyName")
    specialty_profile: Optional[str] = Field(alias="specialtyProfile")


class ExtendedPerson(StudentsSpeciality, ShortPerson):
    pass


class PeopleEmbedded(BaseModel):
    persons: list[ShortPerson] = Field(default=[])
    students: list[StudentsSpeciality] = Field(default=[])


class SearchPeople(BaseModel):
    embedded: PeopleEmbedded = Field(alias="_embedded")

    def serialize_modeus_response(self) -> list[ExtendedPerson]:
        """Serialize search people response."""
        speciality_ids = {student.id: student for student in self.embedded.students}
        extended_people = []
        for person in self.embedded.persons:
            try:
                teacher_event = speciality_ids[person.id]
            except KeyError:
                continue
            extended_people.append(ExtendedPerson(**{
                **teacher_event.model_dump(by_alias=True), **person.model_dump(by_alias=True),
            }))
        return extended_people
