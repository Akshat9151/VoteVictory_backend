from fastapi import APIRouter
from app.api.v1.endpoints import (
    analytics,
    audit_logs,
    auth,
    candidates,
    checkin,
    constituencies,
    dashboard,
    elections,
    health,
    imports,
    notifications,
    organizations,
    polling_stations,
    positions,
    results,
    users,
    volunteers,
    voters,
    voting,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(elections.router)
api_router.include_router(positions.router)
api_router.include_router(constituencies.router)
api_router.include_router(candidates.router)
api_router.include_router(voters.router)
api_router.include_router(imports.router)
api_router.include_router(polling_stations.router)
api_router.include_router(volunteers.router)
api_router.include_router(checkin.router)
api_router.include_router(voting.router)
api_router.include_router(results.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(analytics.router)
api_router.include_router(audit_logs.router)
api_router.include_router(webhooks.router)
