"""
Modeus API implemented using a controller.
"""
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from starlette.responses import StreamingResponse

from yet_another_calendar.settings import settings
from ..modeus import schema as modeus_schema
from ..netology import schema as netology_schema
from . import integration, schema

router = APIRouter()


@router.post("/events/")
async def get_calendar(
        body: modeus_schema.ModeusEventsBody,
        cookies: Annotated[netology_schema.NetologyCookies, Depends(netology_schema.get_cookies_from_headers)],
        jwt_token: Annotated[str, Depends(modeus_schema.get_cookies_from_headers)],
        calendar_id: int = settings.netology_default_course_id,
) -> schema.CalendarResponse:
    """
    Get events from Netology and Modeus, cached.
    """

    cached_calendar = await integration.get_cached_calendar(body, jwt_token, calendar_id, cookies)
    return schema.CalendarResponse.model_validate(cached_calendar)


@router.post("/refresh_events/")
async def refresh_calendar(
        body: modeus_schema.ModeusEventsBody,
        cookies: Annotated[netology_schema.NetologyCookies, Depends(netology_schema.get_cookies_from_headers)],
        jwt_token: Annotated[str, Depends(modeus_schema.get_cookies_from_headers)],
        calendar_id: int = settings.netology_default_course_id,
) -> schema.RefreshedCalendarResponse:
    """
    Refresh events in redis.
    """

    return await integration.refresh_events(body, jwt_token, calendar_id, cookies)


@router.post("/export_ics/")
async def export_ics(
        body: modeus_schema.ModeusEventsBody,
        cookies: Annotated[netology_schema.NetologyCookies, Depends(netology_schema.get_cookies_from_headers)],
        jwt_token: Annotated[str, Depends(modeus_schema.get_cookies_from_headers)],
        calendar_id: int = settings.netology_default_course_id,
        time_zone: str = "Europe/Moscow",
) -> StreamingResponse:
    """
    Export into .ics format
    """
    calendar = await integration.get_calendar(body, jwt_token, calendar_id, cookies)
    return StreamingResponse(integration.export_to_ics(calendar, time_zone))
