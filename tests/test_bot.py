import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "telegram-bot"))

import bot


class CalculsTests(unittest.TestCase):
    def test_tva_accepte_les_espaces_dans_un_montant(self):
        resultat = bot.traiter_calcul("TVA 5 000 000")
        self.assertIsNotNone(resultat)
        self.assertIn("5,000,000", resultat)
        self.assertIn("962,500", resultat)

    def test_bfr_accepte_les_montants_groupes(self):
        resultat = bot.traiter_calcul("BFR 3 000 000 2 000 000 1 500 000 500 000")
        self.assertIsNotNone(resultat)
        self.assertIn("BFR = 3,000,000 FCFA", resultat)

    def test_valeurs_invalides_ne_crashent_pas_le_bot(self):
        self.assertIsNone(bot.traiter_calcul("AMORT 1000000 0"))
        self.assertIsNone(bot.traiter_calcul("IS -100"))
        self.assertIsNone(bot.traiter_calcul("TVA -100"))


class TelegramRobustnessTests(unittest.TestCase):
    def test_decoupage_respecte_la_limite_configuree(self):
        morceaux = bot.decouper_message("a" * 10000, taille=3900)
        self.assertEqual("".join(morceaux), "a" * 10000)
        self.assertTrue(all(len(morceau) <= 3900 for morceau in morceaux))

    def test_wada_est_expose(self):
        self.assertIn("Liste des substances", bot.WADA_TEXT)
        self.assertIn("wada-ama.org", bot.WADA_TEXT)


if __name__ == "__main__":
    unittest.main()
