"""En el paquete del equipo, este MCP lo actualiza el paquete (scripts/al-empezar.sh): aquí no se toca git."""
from pathlib import Path

ORIGEN = Path(__file__).resolve().parents[1] / "ORIGEN"


def en_segundo_plano(repo=None):
    pass


def version(repo=None):
    return "paquete trago-marketing · " + (ORIGEN.read_text().strip()[:60] if ORIGEN.exists() else "?")


def pendiente(repo=None):
    return None


def instalar(repo=None, pruebas=None):
    return {"estado": "al_dia", "version": version(), "nota": "Este conector lo actualiza solo el paquete trago-marketing."}
