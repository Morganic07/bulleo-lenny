#!/usr/bin/env bash
# Démarre l'appli Bulléo Export Hub sur http://127.0.0.1:5000
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Création de l'environnement virtuel (.venv)…"
  python3 -m venv .venv
fi

# Réinstalle les dépendances seulement si requirements.txt a changé depuis la dernière installation.
if [ ! -f .venv/.installe ] || [ requirements.txt -nt .venv/.installe ]; then
  echo "Installation des dépendances…"
  .venv/bin/pip install --quiet -r requirements.txt
  touch .venv/.installe
fi

echo "Bulléo Export Hub : ouvre http://127.0.0.1:5000 dans le navigateur (Ctrl+C pour arrêter)."
exec .venv/bin/python app/app.py
