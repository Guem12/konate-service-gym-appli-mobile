#!/usr/bin/env python
"""Utilitaire en ligne de commande de Django."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Django est introuvable. Activez l'environnement virtuel "
            "(.venv) avant d'exécuter cette commande."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
