import asyncio
import datetime
import logging
from typing import Any, Iterable, Optional

import icalendar
import pytz
from fastapi import HTTPException
from fastapi_cache import default_key_builder, FastAPICache
from fastapi_cache.decorator import cache
from starlette import status

from yet_another_calendar.settings import settings
from ..netology import views as netology_views
from ..modeus import views as modeus_views
from ..modeus import schema as modeus_schema
from ..netology import schema as netology_schema
from . import schema

logger = logging.getLogger(__name__)


def create_ics_event(title: str, starts_at: datetime.datetime, ends_at: datetime.datetime,
                     lesson_id: Any, timezone: datetime.tzinfo, description: Optional[str] = None,
                     webinar_url: Optional[str] = None) -> icalendar.Event:
    event = icalendar.Event()
    dt_now = datetime.datetime.now(tz=timezone)
    event.add('summary', title)
    event.add('location', webinar_url)
    event.add('dtstart', starts_at.astimezone(timezone))
    event.add('dtend', ends_at.astimezone(timezone))
    event.add('dtstamp', dt_now)
    event.add('uid', lesson_id)
    if description:
        event.add('description', description)
    return event


def export_to_ics(calendar: schema.CalendarResponse, timezone: str) -> Iterable[bytes]:
    try:
        tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        raise HTTPException(detail="Wrong timezone", status_code=status.HTTP_400_BAD_REQUEST) from None
    ics_calendar = icalendar.Calendar()
    ics_calendar.add('version', '2.0')
    ics_calendar.add('prodid', 'yet_another_calendar')

    for netology_lesson in calendar.netology.webinars:
        if not netology_lesson.starts_at or not netology_lesson.ends_at:
            continue
        event = create_ics_event(title=f"Netology: {netology_lesson.title}", starts_at=netology_lesson.starts_at,
                                 ends_at=netology_lesson.ends_at, lesson_id=netology_lesson.id,
                                 timezone=tz, webinar_url=netology_lesson.webinar_url)
        ics_calendar.add_component(event)
    for modeus_lesson in calendar.modeus:
        event = create_ics_event(title=f"Modeus: {modeus_lesson.name}",
                                 starts_at=modeus_lesson.start_time, ends_at=modeus_lesson.end_time,
                                 lesson_id=modeus_lesson.id, timezone=tz,
                                 description=modeus_lesson.description)
        ics_calendar.add_component(event)
    yield ics_calendar.to_ical()


async def refresh_events(
        body: modeus_schema.ModeusEventsBody,
        jwt_token: str,
        calendar_id: int,
        cookies: netology_schema.NetologyCookies,
) -> schema.RefreshedCalendarResponse:
    """Clear events cache."""
    cached_json = await get_cached_calendar(body, jwt_token, calendar_id, cookies)
    cached_calendar = schema.CalendarResponse.model_validate(cached_json)
    calendar = await get_calendar(body, jwt_token, calendar_id, cookies)
    changed = cached_calendar.get_hash() != calendar.get_hash()
    try:
        cache_key = default_key_builder(get_cached_calendar, args=(body, jwt_token, calendar_id, cookies), kwargs={})
        coder = FastAPICache.get_coder()
        backend = FastAPICache.get_backend()
        await backend.set(
            key=f"{settings.redis_prefix}:{cache_key}",
            value=coder.encode(calendar),
            expire=settings.redis_events_time_live)
    except Exception as exception:
        logger.error(f"Got redis {exception}")
        raise HTTPException(detail="Can't refresh redis", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from None
    return schema.RefreshedCalendarResponse(
        **{**calendar.model_dump(by_alias=True), "changed": changed},
    )


async def get_calendar(
        body: modeus_schema.ModeusEventsBody,
        jwt_token: str,
        calendar_id: int,
        cookies: netology_schema.NetologyCookies,
) -> schema.CalendarResponse:
    async with asyncio.TaskGroup() as tg:
        netology_response = tg.create_task(netology_views.get_calendar(body, calendar_id, cookies))
        modeus_response = tg.create_task(modeus_views.get_calendar(body, jwt_token))
    return schema.CalendarResponse.model_validate(
        {"netology": netology_response.result(), "modeus": modeus_response.result()},
    )


@cache(expire=settings.redis_events_time_live)
async def get_cached_calendar(
        body: modeus_schema.ModeusEventsBody,
        jwt_token: str,
        calendar_id: int,
        cookies: netology_schema.NetologyCookies,
) -> schema.CalendarResponse:
    return await get_calendar(body, jwt_token, calendar_id, cookies)
