"""Public marketing leads.

Anti-abuse lives here, not in the browser: the honeypot and submit timing are
re-checked server-side, and rate limits are keyed by the forwarded client IP.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rate_limit import client_ip, enforce
from app.config import get_settings
from app.db.session import public_session
from app.leads.schemas import LeadAccepted, LeadIn

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])

ACCEPTED = "Terima kasih, tim kami akan menghubungi Anda."
MIN_ELAPSED_MS = 3000


@router.post(
    "",
    response_model=LeadAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a demo request",
)
async def create_lead(body: LeadIn, request: Request) -> LeadAccepted:
    # Silently accept bots: no row, no hint that they were detected.
    if body.website.strip() or body.elapsed_ms < MIN_ELAPSED_MS:
        return LeadAccepted(message=ACCEPTED)

    settings = get_settings()
    ip = client_ip(request)
    await enforce(
        request.app.state.redis,
        key=f"sb:rl:leads:ip:{ip}",
        limit=settings.leads_ip_limit,
        window_seconds=3600,
    )
    await enforce(
        request.app.state.redis,
        key="sb:rl:leads:global",
        limit=settings.leads_global_limit,
        window_seconds=3600,
    )

    async with public_session(request.app.state.sessionmaker) as session:
        await _upsert_lead(session, body, request, ip)

    return LeadAccepted(message=ACCEPTED)


async def _upsert_lead(session: AsyncSession, body: LeadIn, request: Request, ip: str) -> None:
    existing = (
        await session.execute(
            text(
                """
                SELECT id FROM public.leads
                 WHERE email = :email
                   AND facility_name = :facility_name
                   AND created_at > now() - interval '24 hours'
                 ORDER BY created_at DESC
                 LIMIT 1
                """
            ),
            {"email": body.email, "facility_name": body.facility_name},
        )
    ).scalar_one_or_none()

    params = {
        "name": body.name.strip(),
        "email": body.email,
        "facility_name": body.facility_name.strip(),
        "facility_type": body.facility_type,
        "city": body.city,
        "phone": body.phone,
        "message": body.message,
        "ip": ip,
        "user_agent": request.headers.get("user-agent"),
    }

    if existing is not None:
        await session.execute(
            text(
                """
                UPDATE public.leads
                   SET name = :name,
                       facility_type = :facility_type,
                       city = :city,
                       phone = :phone,
                       message = :message,
                       ip = CAST(:ip AS inet),
                       user_agent = :user_agent,
                       created_at = now()
                 WHERE id = :id
                """
            ),
            {**params, "id": existing},
        )
        return

    await session.execute(
        text(
            """
            INSERT INTO public.leads
                (name, email, facility_name, facility_type, city, phone,
                 message, source, ip, user_agent)
            VALUES
                (:name, :email, :facility_name, :facility_type, :city, :phone,
                 :message, 'website', CAST(:ip AS inet), :user_agent)
            """
        ),
        params,
    )
