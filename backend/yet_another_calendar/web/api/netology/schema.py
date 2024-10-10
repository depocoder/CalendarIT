import datetime
import re
from typing import Optional, Annotated, Any
from urllib.parse import urljoin

from fastapi import Header
from pydantic import BaseModel, Field, computed_field

from yet_another_calendar.settings import settings
from yet_another_calendar.web.api.modeus.schema import ModeusTimeBody

_DATE_PATTERN = r"\d{2}.\d{2}.\d{2}"


class NetologyCreds(BaseModel):
    """Netology creds."""

    username: str
    password: str = Field(repr=False)


class NetologyCookies(BaseModel):
    rails_session: str = Field(alias="_netology-on-rails_session")


async def get_cookies_from_headers(
        rails_session: Annotated[str, Header(alias="_netology-on-rails_session")],
) -> NetologyCookies:
    return NetologyCookies.model_validate({
        "_netology-on-rails_session": rails_session,
    })


class NetologyProgramId(BaseModel):
    """Netology program id."""
    id: int
    title: str
    url_code: str = Field(alias="urlcode")
    type: str


class CoursesResponse(BaseModel):
    """Program id."""
    programs: list[NetologyProgramId]

    def get_utmn_program(self) -> Optional[NetologyProgramId]:
        for program in self.programs:
            if settings.netology_course_name in program.title:
                return program


class BaseLesson(BaseModel):
    id: int
    lesson_id: int
    type: str
    title: str


class LessonWebinar(BaseLesson):
    starts_at: Optional[datetime.datetime] = Field(default=None)
    ends_at: Optional[datetime.datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    experts: Optional[list[dict[str, Any]]] = Field(default=None)
    video_url: Optional[str] = None
    webinar_url: Optional[str] = None

    def is_suitable_time(self, time_min: datetime.datetime, time_max: datetime.datetime) -> bool:
        """Check if lesson have suitable time"""
        if not self.starts_at or time_min > self.starts_at:
            return False
        if not self.ends_at or self.ends_at > time_max:
            return False
        return True


# noinspection PyNestedDecorators
class LessonTask(BaseLesson):
    path: str

    @computed_field  # type: ignore
    @property
    def url(self) -> str:
        return urljoin(settings.netology_url, self.path)

    @computed_field  # type: ignore
    @property
    def deadline(self) -> Optional[datetime.datetime]:
        match = re.search(_DATE_PATTERN, self.title)
        if not match:
            return None
        date = match.group(0)
        return datetime.datetime.strptime(date, "%d.%m.%y").replace(tzinfo=datetime.timezone.utc)

    def is_suitable_time(self, time_min: datetime.datetime, time_max: datetime.datetime) -> bool:
        """Check if lesson have suitable time"""
        if self.deadline and time_max > self.deadline > time_min:
            return True
        return False


class NetologyProgram(BaseModel):
    lesson_items: list[dict[str, Any]]


class CalendarResponse(BaseModel):
    lessons: list[NetologyProgram]

    @staticmethod
    def filter_lessons(
            program: NetologyProgram, time_min: datetime.datetime, time_max: datetime.datetime,
    ) -> tuple[list[LessonTask], list[LessonWebinar]]:
        """Filter lessons by time and status."""
        homework_events, webinars = [], []
        for lesson in program.lesson_items:
            if lesson['type'] in ["task", "test"]:
                homework = LessonTask(**lesson)
                if homework.is_suitable_time(time_min, time_max):
                    homework_events.append(homework)
                    continue
            if lesson['type'] == "webinar":
                webinar = LessonWebinar(**lesson)
                if webinar.is_suitable_time(time_min, time_max):
                    webinars.append(webinar)
                    continue
        return homework_events, webinars

    def get_serialized_lessons(self, body: ModeusTimeBody) -> tuple[list[Any], list[Any]]:
        filtered_webinars = []
        filtered_homework = []
        time_min = body.time_min
        time_max = body.time_max
        for lesson in self.lessons:
            homework_events, webinars_events = self.filter_lessons(lesson, time_min, time_max)
            filtered_homework.extend(homework_events)
            filtered_webinars.extend(webinars_events)
        return filtered_homework, filtered_webinars


class ExtendedLesson(LessonWebinar):
    passed: bool
    experts: Optional[list[dict[str, Any]]] = Field(default=None)


class ExtendedLessonResponse(BaseModel):
    lesson_items: list[ExtendedLesson]

    def exclude_attachment(self) -> list[ExtendedLesson]:
        excluded_lessons = []
        for lesson in self.lesson_items:
            if lesson.type != 'attachment':
                excluded_lessons.append(lesson)
        return excluded_lessons


class DetailedProgram(BaseModel):
    id: int
    name: str
    start_date: datetime.datetime
    finish_date: datetime.datetime


class Program(BaseModel):
    detailed_program: DetailedProgram = Field(alias='program')


class ProfessionResponse(BaseModel):
    """Professions modules info from Netology."""
    profession_modules: list[Program]

    def get_lesson_ids(self) -> set[int]:
        program_ids = set()
        for program in self.profession_modules:
            program_ids.add(program.detailed_program.id)
        return program_ids

class SerializedEvents(BaseModel):
    """Structure for displaying frontend."""
    homework: list[LessonTask]
    webinars: list[LessonWebinar]
