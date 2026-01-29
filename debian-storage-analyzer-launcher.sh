#!/bin/bash
# Lanceur local pour le développement
cd "$(dirname "$0")/debian-storage-analyzer"
exec python3 simple_launcher.py "$@"
