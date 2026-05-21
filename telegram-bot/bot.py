import logging
import json
import os
import sys
from telegram import Update
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, filters,
    ContextTypes
)
from groq import Groq

TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRA")
CLE_GROQ = os.environ.get("CLE_GRO")
DB_FILE = "historiques.json"

SYSTEM_PROMPT = """Tu es JKBOT 🇨🇲, expert en fiscalité camerounaise, spécialisé dans le Code Général des Impôts (CGI) 2026 et la Loi de Finances 2025/2026.
Réponds toujours en français, de façon claire, précise et pédagogique, avec des émojis pertinents.
Cite les articles du CGI quand c'est possible. Si une question est hors fiscalité camerounaise, redirige poliment.

==============================
CODE GÉNÉRAL DES IMPÔTS DU CAMEROUN — RÉFÉRENCE 2026
==============================

─── 1. IMPÔT SUR LES SOCIÉTÉS (IS) ───
• Taux IS : 30% sur le bénéfice imposable (Art. 27 CGI)
• Centimes Additionnels Communaux (CAC) : 10% de l'IS → Taux effectif global : 33%
• Impôt Minimum Forfaitaire (IMF) : 1% du CAHT, minimum 500 000 FCFA, maximum 2 500 000 FCFA (Art. 62 CGI)
• Exercice fiscal : 1er janvier – 31 décembre
• Dépôt déclaration IS : au plus tard le 15 mars de l'année suivante
• Acomptes IS : 3 versements (mars, juin, septembre) = 1% du CA mensuel
• Résultat fiscal = Résultat comptable + réintégrations – déductions
• Charges non déductibles : amendes et pénalités, dépenses somptuaires, provisions non réglementées
• Report déficitaire : 4 ans maximum (Art. 31 CGI)

─── 2. TAXE SUR LA VALEUR AJOUTÉE (TVA) ───
• Taux normal : 19,25% (17,5% + 10% CAC) (Art. 125 CGI)
• Taux zéro (0%) : exportations, produits pharmaceutiques agréés, intrants agricoles (Art. 128 CGI)
• Exonérations : produits alimentaires de base (maïs, manioc, plantain, riz local), eau potable, livres scolaires, soins médicaux (Art. 129 CGI)
• Seuil d'assujettissement : CAHT ≥ 50 000 000 FCFA (Art. 124 CGI)
• En dessous du seuil : régime de l'impôt libératoire
• Déclaration et paiement : mensuel (au plus tard le 15 du mois suivant)
• Base de calcul TVA : prix HT de la vente ou prestation
• TVA collectée – TVA déductible = TVA à payer
• Crédit TVA : remboursable sous conditions (exportateurs prioritaires)

─── 3. IRPP — IMPÔT SUR LE REVENU DES PERSONNES PHYSIQUES ───
• Barème progressif (Art. 69 CGI) :
   - De 0 à 2 000 000 FCFA/an         →  0%
   - De 2 000 001 à 3 000 000 FCFA    → 10%
   - De 3 000 001 à 5 000 000 FCFA    → 15%
   - De 5 000 001 à 10 000 000 FCFA   → 25%
   - Au-delà de 10 000 000 FCFA       → 35%
• + 10% CAC sur l'IRPP calculé → taux réels : 0/11/16,5/27,5/38,5%
• Abattement forfaitaire : 30% sur les revenus salariaux (minimum 500 000, maximum 3 000 000 FCFA)
• Revenus concernés : salaires, traitements, pensions, bénéfices professionnels, revenus fonciers, capitaux mobiliers
• Déclaration annuelle : avant le 15 mars
• Retenue à la source mensuelle sur salaires : obligatoire pour l'employeur

─── 4. RETENUES À LA SOURCE (RS) ───
• Honoraires, commissions, courtages versés à des résidents : 11% libératoire (Art. 92 CGI)
• Honoraires versés à des non-résidents : 15% libératoire
• Loyers versés à des personnes physiques résidentes : 15% libératoire (Art. 94 CGI)
• Dividendes distribués à des résidents : 16,5% (15% + 10% CAC) (Art. 37 CGI)
• Dividendes à des non-résidents : 16,5% sauf conventions fiscales
• Intérêts servis aux particuliers résidents : 16,5%
• Intérêts servis aux non-résidents : 16,5% sauf conventions
• Marchés publics (personnes non immatriculées) : 15% à la source
• RS sur achats de produits forestiers : 2,5%

─── 5. DROITS D'ACCISE ───
• Boissons alcoolisées locales : 25% (Art. 140 CGI)
• Boissons alcoolisées importées : 25% + droits de douane
• Tabacs et cigarettes : 25%
• Véhicules de tourisme (cylindrée > 2000 cm³) : 12,5%
• Produits de luxe (parfums, cosmétiques haut de gamme) : 25%
• Boissons sucrées/gazeuses : 3,5%
• Ces droits s'ajoutent à la TVA sur la base TTC accise

─── 6. PATENTE ET LICENCE ───
• Toute personne physique ou morale exerçant une activité commerciale, industrielle ou libérale est soumise à la patente (Art. 170 CGI)
• Calcul : droit fixe + droit proportionnel sur la valeur locative professionnelle
• Droit fixe selon la catégorie d'activité (tableau annexé CGI)
• Droit proportionnel : 16,5% de la valeur locative des locaux professionnels
• Paiement : annuel, avant le 31 mars
• Exemptions : agriculteurs, artisans, professions réglementées sous conditions

─── 7. TAXE FONCIÈRE ───
• Propriétés bâties : 0,1% de la valeur vénale du bien (Art. 577 CGI)
• Propriétés non bâties : 0,15% de la valeur vénale
• + 10% CAC
• Base : valeur vénale actualisée par l'administration
• Paiement : annuel avant le 31 mars
• Exonérations : propriétés de l'État, missions diplomatiques, premières années après construction neuve

─── 8. TAXE SPÉCIALE SUR LES REVENUS (TSR) ───
• S'applique aux sommes versées à des non-résidents en rémunération de prestations de services utilisées au Cameroun (Art. 99 CGI)
• Taux : 15% libératoire (avec 10% CAC → 16,5% effectif)
• Assiette : montant brut des sommes versées
• Retenue et reversement : à la charge du débiteur camerounais
• Exceptions : conventions fiscales bilatérales

─── 9. TAXE SUR LES ACTIVITÉS FINANCIÈRES (TAF) ───
• S'applique aux opérations bancaires et financières (Art. 145 CGI)
• Taux : 0,25% sur les crédits accordés
• Taux sur agios bancaires : 15%
• Exonérations : prêts au logement social, crédits à l'agriculture

─── 10. DROITS D'ENREGISTREMENT ───
• Ventes d'immeubles : 10% du prix de cession (Art. 468 CGI)
• Baux commerciaux : 10% du loyer annuel × durée plafonnée
• Actes de société (constitution, augmentation de capital) : 1% du capital
• Mutations à titre gratuit (donations, successions) : barème progressif de 1,5% à 20%
• Cessions de fonds de commerce : 5% du prix

─── 11. CENTIMES ADDITIONNELS COMMUNAUX (CAC) ───
• S'appliquent à : IS, IRPP, TVA (via les taux intégrés), patente, taxe foncière
• Taux unique : 10% de l'impôt principal
• Destinés aux collectivités territoriales décentralisées
• Attention : les taux affichés (IS 33%, TVA 19,25%, IRPP barème majoré) intègrent déjà les CAC

─── 12. IMPÔT LIBÉRATOIRE ───
• Pour contribuables dont le CAHT < 50 000 000 FCFA (Art. 103 CGI)
• Montant forfaitaire selon secteur d'activité et localisation :
   - Petits commerces zones rurales : 20 000 à 50 000 FCFA/trimestre
   - Petits commerces zones urbaines : 50 000 à 150 000 FCFA/trimestre
   - Artisans : 15 000 à 80 000 FCFA/trimestre
• Paiement : trimestriel

─── 13. REDEVANCE AUDIOVISUELLE ───
• Taux : 7 500 FCFA/an par poste de télévision détenu (Art. 223 CGI)
• Collectée conjointement avec la taxe foncière ou la patente

─── 14. OBLIGATIONS DÉCLARATIVES CLÉS ───
• Immatriculation obligatoire au fichier des contribuables (NIU)
• Déclaration existence : dans les 30 jours de démarrage d'activité
• Tenue de comptabilité obligatoire pour les entreprises du régime réel
• Factures normalisées obligatoires (mention du NIU, numéro de facture)
• Délais de prescription : 3 ans pour les impôts déclaratifs (Art. 43 LPF)
• Pénalités de retard : 1,5% par mois de retard, minimum 25 000 FCFA
• Majoration pour défaut de déclaration : 100% des droits dus

─── 15. CONVENTIONS FISCALES ───
• Convention CEMAC (Communauté Économique et Monétaire d'Afrique Centrale) : exonérations inter-États membres
• Conventions bilatérales : France, Canada, Maroc, Tunisie, Nigeria (réduction retenues à la source)
• Principe de résidence fiscale : > 183 jours/an au Cameroun → résident fiscal

==============================
FIN DU CODE GÉNÉRAL DES IMPÔTS 2026
==============================

En cas de doute sur un cas particulier complexe, recommande toujours de consulter un expert-comptable agréé ou la DGI (Direction Générale des Impôts) du Cameroun.
"""

AIDE_TEXT = """📚 *JKBOT — Domaines fiscaux couverts*

Je suis votre expert en fiscalité camerounaise (CGI 2026). Voici ce que vous pouvez me demander :

*1️⃣ Impôt sur les Sociétés (IS)*
▸ "Comment calculer l'IS sur un bénéfice de 10M FCFA ?"
▸ "C'est quoi l'IMF et quand s'applique-t-il ?"

*2️⃣ TVA (Taxe sur la Valeur Ajoutée)*
▸ "Quel est le taux de TVA au Cameroun ?"
▸ "Mon entreprise est-elle assujettie à la TVA ?"

*3️⃣ IRPP (Impôt sur le Revenu)*
▸ "Calculer l'IRPP sur un salaire de 500 000 FCFA/mois"
▸ "Quelles sont les tranches du barème IRPP ?"

*4️⃣ Retenues à la source*
▸ "Quel taux de RS sur des honoraires versés à un consultant ?"
▸ "Comment retenir l'impôt sur les loyers ?"

*5️⃣ Droits d'accise*
▸ "Taux de droits d'accise sur les boissons alcoolisées ?"
▸ "Comment s'appliquent les accises sur le tabac ?"

*6️⃣ Patente & Taxe foncière*
▸ "Comment calculer ma patente ?"
▸ "Taux de la taxe foncière sur mon immeuble ?"

*7️⃣ TSR & TAF*
▸ "Je paie un prestataire étranger, quelle taxe appliquer ?"
▸ "La TAF s'applique-t-elle aux microcrédits ?"

*8️⃣ Droits d'enregistrement*
▸ "Frais d'enregistrement pour une vente immobilière ?"
▸ "Coût fiscal pour constituer une SARL ?"

*9️⃣ Obligations & Pénalités*
▸ "Quand déposer ma déclaration IS ?"
▸ "Pénalité pour retard de déclaration TVA ?"

─────────────────────
🔄 /reset — Effacer l'historique
❓ /aide — Afficher ce menu
"""

def charger_historiques():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erreur chargement historiques: {e}")
    return {}

def sauvegarder_historiques(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde historiques: {e}")

historiques = charger_historiques()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prenom = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Bonjour {prenom} !\n\n"
        f"Je suis *JKBOT* 🇨🇲, votre expert en fiscalité camerounaise.\n\n"
        f"Je maîtrise le *Code Général des Impôts 2026* :\n"
        f"TVA • IS • IRPP • Patente • Retenues à la source • Droits d'accise • et bien plus.\n\n"
        f"Posez votre question librement, ou tapez /aide pour voir les domaines couverts. 💼",
        parse_mode="Markdown"
    )

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    historiques[user_id] = []
    sauvegarder_historiques(historiques)
    await update.message.reply_text("🔄 Historique effacé ! Posez votre prochaine question.")

async def cmd_aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(AIDE_TEXT, parse_mode="Markdown")

async def repondre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    question = update.message.text
    if user_id not in historiques:
        historiques[user_id] = []

    await update.message.reply_chat_action("typing")
    try:
        client = Groq(api_key=CLE_GROQ)
        historiques[user_id].append({"role": "user", "content": question})

        reponse = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + historiques[user_id],
            max_tokens=1500,
            temperature=0.5
        )

        texte = reponse.choices[0].message.content
        historiques[user_id].append({"role": "assistant", "content": texte})
        if len(historiques[user_id]) > 20:
            historiques[user_id] = historiques[user_id][-20:]

        sauvegarder_historiques(historiques)

        if len(texte) > 4096:
            for i in range(0, len(texte), 4096):
                await update.message.reply_text(texte[i:i+4096])
        else:
            await update.message.reply_text(texte)

    except Exception as e:
        print(f"❌ Erreur Groq: {e}")
        await update.message.reply_text("❌ Erreur technique. Réessayez dans quelques instants.")

def main():
    if not TOKEN_TELEGRAM:
        print("❌ TOKEN_TELEGRA manquant dans les variables d'environnement")
        sys.exit(1)
    if not CLE_GROQ:
        print("❌ CLE_GRO manquante dans les variables d'environnement")
        sys.exit(1)

    print("🤖 Initialisation de JKBOT CGI 2026...")
    app = Application.builder().token(TOKEN_TELEGRAM).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("aide", cmd_aide))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre))

    print("✅ JKBOT prêt. Connexion à Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
