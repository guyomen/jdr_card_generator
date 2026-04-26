#!/usr/bin/env python3
"""
Script de lancement rapide - Utilise la nouvelle structure
À exécuter depuis la racine du projet
"""

import sys
import os

# Ajoute le répertoire courant au path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_generator.cli import main

if __name__ == "__main__":
    main()
