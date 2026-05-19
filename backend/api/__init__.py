from __future__ import annotations

"""
Prepara el paquete API y hace visible `backend/scripts` para los modulos legacy
que todavia importan `utils` o `enrichment` como paquetes de nivel superior.

Esto evita que la API dependa del directorio exacto desde el que se arranca el
servidor y centraliza el ajuste de `sys.path` en un unico punto.
"""

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BACKEND_DIR / "scripts"

for path in (BACKEND_DIR, SCRIPTS_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
