import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

import config_store
from models import ConfigUpdate, RoutingConfig
from seed import seed

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="config-gateway")


@app.on_event("startup")
async def startup() -> None:
    await seed()


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz() -> str:
    return "ok"


@app.get("/v1/tenants/{tenant_id}/route", response_model=RoutingConfig)
async def get_route(tenant_id: str) -> RoutingConfig:
    try:
        cfg = await config_store.get_routing_config(tenant_id)
    except config_store.TenantNotFoundError:
        raise HTTPException(status_code=404, detail="unknown tenant")
    return RoutingConfig(tenant_id=tenant_id, **cfg)


@app.post("/admin/tenants/{tenant_id}/config", response_model=RoutingConfig)
async def post_config(tenant_id: str, body: ConfigUpdate) -> RoutingConfig:
    fields = body.model_dump(exclude={"expected_generation"})
    try:
        cfg = await config_store.update_routing_config(
            tenant_id, body.expected_generation, fields
        )
    except config_store.ConflictError:
        raise HTTPException(status_code=409, detail="generation conflict")
    return RoutingConfig(tenant_id=tenant_id, **cfg)
