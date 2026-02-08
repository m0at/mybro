"""DigitalOcean API integration for droplet monitoring."""

import httpx
from backend.config import config
from backend.db import postgres

DO_API = "https://api.digitalocean.com/v2"


async def get_droplets() -> list[dict]:
    """Fetch all droplets from DigitalOcean API."""
    token = config.digitalocean_token
    if not token:
        return []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{DO_API}/droplets",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    droplets = []
    for d in data.get("droplets", []):
        networks = d.get("networks", {}).get("v4", [])
        public_ip = next((n["ip_address"] for n in networks if n["type"] == "public"), None)

        droplets.append({
            "droplet_id": d["id"],
            "name": d["name"],
            "status": d["status"],
            "ip_address": public_ip,
            "size_slug": d["size_slug"],
            "region": d["region"]["slug"],
            "monthly_cost": d["size"]["price_monthly"],
        })

    return droplets


async def sync_droplets():
    """Sync droplets from DO API to local database."""
    droplets = await get_droplets()
    for d in droplets:
        await postgres.execute(
            """INSERT INTO droplets (droplet_id, name, status, ip_address, size_slug, region, monthly_cost, last_checked_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
               ON CONFLICT (droplet_id)
               DO UPDATE SET status = $3, ip_address = $4, last_checked_at = NOW()""",
            d["droplet_id"], d["name"], d["status"], d["ip_address"],
            d["size_slug"], d["region"], d["monthly_cost"],
        )
    return droplets
