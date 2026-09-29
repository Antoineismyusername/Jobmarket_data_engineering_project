#!/bin/sh
set -e

# Se placer à la racine du projet et créer le dossier des logs
cd "$(dirname "$0")/.."
mkdir -p logs/api

# Construire l'image et démarrer l'API.
docker build -f docker/Dockerfile.api -t api:local .
docker compose up -d api