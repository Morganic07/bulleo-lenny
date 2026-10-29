import sys
from pathlib import Path

# Les modules de l'appli (app.py, base.py, donnees.py) sont dans app/ : on rend ce dossier importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
