"""Point d'entrée de compatibilité pour les anciens déploiements JKBOT.

L'implémentation principale se trouve dans bot.py afin d'éviter deux versions
concurrentes avec des variables d'environnement et des modèles différents.
"""

from bot import main


if __name__ == "__main__":
    main()
