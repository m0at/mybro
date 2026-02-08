"""System API — running servers, processes, droplets."""

from fastapi import APIRouter

from backend.services import process_scanner, digitalocean

router = APIRouter(tags=["system"])


@router.get("/system/servers")
async def get_servers():
    """Get all listening servers mapped to projects."""
    servers = await process_scanner.get_listening_servers()
    return {"servers": servers}


@router.get("/system/scripts")
async def get_scripts():
    """Get running scripts and background processes."""
    scripts = await process_scanner.get_running_scripts()
    return {"scripts": scripts}


@router.get("/system/claude")
async def get_claude():
    """Get running Claude Code instances."""
    procs = await process_scanner.get_claude_processes()
    return {"claude_processes": procs}


@router.get("/system/droplets")
async def get_droplets():
    """Get DigitalOcean droplets."""
    droplets = await digitalocean.get_droplets()
    return {"droplets": droplets}


@router.post("/system/droplets/sync")
async def sync_droplets():
    """Sync droplets from DO API to local database."""
    droplets = await digitalocean.sync_droplets()
    return {"synced": len(droplets)}


@router.get("/system/overview")
async def system_overview():
    """Full system overview — servers + scripts + claude + droplets."""
    servers = await process_scanner.get_listening_servers()
    scripts = await process_scanner.get_running_scripts()
    claude = await process_scanner.get_claude_processes()
    droplets = await digitalocean.get_droplets()

    return {
        "servers": servers,
        "scripts": scripts,
        "claude_processes": claude,
        "droplets": droplets,
    }
