import logging
import json
import os
import re
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, filters,
    ContextTypes
)
from groq import Groq
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
CLE_GROQ = os.environ.get("CLE_GROQ")
ADMIN_CODE = os.environ.get("JKBOT_ADMIN_CODE", "JK2027ADMIN")
DB_FILE = "historiques.json"

# ─────────────────────────────────────────────
# SCRAPING INTELLIGENT PAR SUJET
# ─────────────────────────────────────────────
def recherche_fiscal(question):
    try:
        question_lower = question.lower()

        if any(mot in question_lower for mot in ["créer", "création", "sarl", "entreprise", "immatriculer", "cfce", "rccm"]):
            url = "https://codegeneraldesimpots.com/cm/article/guide-complet-2026-creer-et-immatriculer-une-sarl-au-cameroun"
        elif any(mot in question_lower for mot in ["igs", "impôt synthétique", "libératoire"]):
            url = "https://codegeneraldesimpots.com/cm/article/igs-2026-ce-que-vous-devez-savoir"
        elif any(mot in question_lower for mot in ["tva", "taxe valeur ajoutée"]):
            url = "https://codegeneraldesimpots.com/cm/"
        elif any(mot in question_lower for mot in ["irpp", "salaire", "impôt revenu"]):
            url = "https://codegeneraldesimpots.com/cm/"
        elif any(mot in question_lower for mot in ["is ", "impôt société", "bénéfice", "imf"]):
            url = "https://codegeneraldesimpots.com/cm/"
        else:
            url = "https://codegeneraldesimpots.com/cm/"

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        texte = ""
        for p in soup.find_all(["p", "h2", "h3", "li"]):
            texte += p.get_text() + "\n"

        return texte[:4000]
    except Exception:
        return ""

# ─────────────────────────────────────────────
# HISTORIQUE
# ─────────────────────────────────────────────
def charger_historique():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def sauvegarder_historique(historique):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

def get_historique_user(user_id):
    historique = charger_historique()
    return historique.get(str(user_id), [])

def ajouter_message(user_id, role, content):
    historique = charger_historique()
    uid = str(user_id)
    if uid not in historique:
        historique[uid] = []
    historique[uid].append({"role": role, "content": content})
    # Garder seulement les 20 derniers messages
    historique[uid] = historique[uid][-20:]
    sauvegarder_historique(historique)

def reset_historique(user_id):
    historique = charger_historique()
    historique[str(user_id)] = []
    sauvegarder_historique(historique)

# ─────────────────────────────────────────────
# SYSTEM PROMPT COMPLET
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es JKBOT 🇨🇲, expert en fiscalité camerounaise ET en comptabilité OHADA/SYSCOHADA.
Réponds toujours en français, de façon claire, précise et pédagogique, avec des émojis pertinents.
Cite les articles du CGI ou du référentiel SYSCOHADA quand c'est possible.
Si une question est hors de tes domaines, redirige poliment.

╔══════════════════════════════════════════╗
║  CODE GÉNÉRAL DES IMPÔTS — CGI 2026      ║
╚══════════════════════════════════════════╝

─── 1. IMPÔT SUR LES SOCIÉTÉS (IS) ───
• Taux IS : 30% sur le bénéfice imposable (Art. 27 CGI)
• CAC 10% sur IS → taux effectif global : 33%
• IMF : 1% du CAHT, min 500 000 FCFA, max 2 500 000 FCFA (Art. 62 CGI)
• Exercice : 1er janv – 31 déc ; déclaration avant le 15 mars
• Acomptes : 3 versements (mars, juin, sept) = 1% CA mensuel
• Report déficitaire : 4 ans max (Art. 31 CGI)
• Charges non déductibles : amendes, dépenses somptuaires, provisions non réglementées

─── 2. TVA ───
• Taux normal : 19,25% (17,5% + 10% CAC) (Art. 125 CGI)
• Taux zéro : exportations, produits pharma agréés, intrants agricoles (Art. 128)
• Exonérations : maïs, manioc, plantain, riz local, eau potable, livres scolaires, soins médicaux (Art. 129)
• Seuil assujettissement : CAHT ≥ 50 000 000 FCFA (Art. 124)
• Déclaration mensuelle (avant le 15 du mois suivant)
• TVA à payer = TVA collectée – TVA déductible

─── 3. IRPP ───
• Barème progressif (Art. 69 CGI) + 10% CAC :
  0 à 2 000 000 FCFA          →  0%  (effectif  0%)
  2 000 001 à 3 000 000        → 10%  (effectif 11%)
  3 000 001 à 5 000 000        → 15%  (effectif 16,5%)
  5 000 001 à 10 000 000       → 25%  (effectif 27,5%)
  Au-delà de 10 000 000        → 35%  (effectif 38,5%)
• Abattement forfaitaire salarial : 30% (min 500 000, max 3 000 000 FCFA)

─── 4. RETENUES À LA SOURCE ───
• Honoraires résidents : 11% libératoire
• Honoraires non-résidents : 15%
• Loyers (pers. physiques) : 15%
• Dividendes / Intérêts : 16,5%
• TSR (prestataires étrangers) : 16,5%
• Marchés publics (non immatriculés) : 15%

─── 5. AUTRES IMPÔTS ───
• Droits d'accise : boissons alcool 25%, tabacs 25%, boissons sucrées 3,5%, véhicules luxe 12,5%
• Patente : droit fixe + 16,5% valeur locative (avant 31 mars)
• Taxe foncière : 0,1% bâti / 0,15% non bâti (+ 10% CAC)
• Droits enregistrement : vente immeuble 10%, constitution société 1%, cession fonds commerce 5%
• Impôt libératoire : CAHT < 50M FCFA — forfait trimestriel 15 000 à 150 000 FCFA
• TAF : 0,15% sur crédits bancaires ; 15% sur agios
• Redevance audiovisuelle : 7 500 FCFA/an/poste TV

─── 6. OBLIGATIONS & PÉNALITÉS ───
• NIU obligatoire ; déclaration existence dans les 30 jours
• Pénalité retard : 1,5%/mois, min 25 000 FCFA
• Majoration défaut déclaration : 100% des droits dus
• Prescription : 3 ans (Art. 43 LPF)

─── 7. CONVENTIONS FISCALES ───
• CEMAC : exonérations inter-États membres
• Bilatérales : France, Canada, Maroc, Tunisie, Nigeria

─── 8. CRÉATION D'ENTREPRISE AU CAMEROUN ───
• SA  : capital min 10 000 000 FCFA, ≥ 3 actionnaires
• SARL: capital min 1 000 000 FCFA, 1 à 50 associés ← recommandée
• SAS : capital libre, flexible (OHADA 2014)
• SNC : pas de capital minimum, responsabilité illimitée
• EI  : personne physique, simple, responsabilité illimitée
• NIU : GRATUIT (auprès de la DGI, délai 24-72h)
• RCCM : ~30 000 FCFA (guichet unique CFCE, 24h)
• Notaire statuts : 150 000 – 300 000 FCFA
• Greffe + enregistrement : 50 000 – 100 000 FCFA
• Frais divers : 30 000 – 50 000 FCFA
• TOTAL création SARL : ~230 000 – 450 000 FCFA
• Délai total : 3 à 7 jours ouvrables
• CFCE Yaoundé : Avenue Monseigneur Vogt
• CFCE Douala : Bonanjo, face CCIMA

╔══════════════════════════════════════════╗
║  COMPTABILITÉ OHADA / SYSCOHADA          ║
╚══════════════════════════════════════════╝

─── A. PLAN COMPTABLE OHADA — CLASSES ───
• Classe 1 : Ressources durables (capitaux propres, dettes financières)
  10 Capital ; 11 Réserves ; 12 Report à nouveau ; 13 Résultat net ;
  14 Subventions d'investissement ; 16-19 Emprunts et dettes financières
• Classe 2 : Actif immobilisé
  20 Charges immobilisées ; 21 Immobilisations incorporelles ; 22 Terrains ;
  23 Bâtiments ; 24 Matériel ; 25 Avances/acomptes sur immobilisations ;
  28 Amortissements (comptes soustractifs) ; 29 Provisions pour dépréciation
• Classe 3 : Stocks
  31 Marchandises ; 32 Matières premières ; 35 Produits finis ;
  36 Produits intermédiaires ; 39 Provisions pour dépréciation stocks
• Classe 4 : Tiers (créances et dettes à court terme)
  40 Fournisseurs ; 41 Clients ; 42 Personnel ; 43 Organismes sociaux ;
  44 État et collectivités (TVA, IS, IRPP) ; 45 Associés ; 47 Débiteurs/créditeurs divers
• Classe 5 : Trésorerie
  51 Banque ; 52 Chèques postaux ; 53 Caisses ; 57 Régies
• Classe 6 : Charges (comptes de gestion)
  60 Achats ; 61 Transport ; 62 Services extérieurs A ; 63 Services extérieurs B ;
  64 Impôts et taxes ; 65 Autres charges ; 66 Charges personnel ;
  67 Charges financières ; 68 Dotations amortissements/provisions ; 69 IS
• Classe 7 : Produits
  70 Ventes ; 71 Subventions d'exploitation ; 72 Production immobilisée ;
  75 Autres produits ; 77 Produits financiers ; 78 Reprises provisions
• Classe 8 : Autres charges et produits (hors activités ordinaires — HAO)
  81 Valeurs comptables des cessions ; 82 Produits de cessions
• Classe 9 : Comptabilité analytique (usage interne)

─── B. CYCLE COMPTABLE ───
1. Collecte des pièces justificatives
2. Enregistrement dans le journal (livre journal)
3. Report au Grand Livre (par compte)
4. Établissement de la Balance (vérification équilibre débit/crédit)
5. Travaux d'inventaire (amortissements, provisions, régularisations)
6. Établissement des états financiers
7. Approbation et dépôt légal

─── C. MÉCANISME DE LA PARTIE DOUBLE ───
• Tout débit a un crédit correspondant de même montant
• Actif augmente au débit, diminue au crédit
• Passif augmente au crédit, diminue au débit
• Charges augmentent au débit ; Produits augmentent au crédit
• Exemple : Achat marchandises 100 000 FCFA au comptant :
  Débit 31 Marchandises 100 000 / Crédit 53 Caisse 100 000

─── D. AMORTISSEMENTS ───
• Amortissement linéaire = Valeur d'origine / Durée d'utilité
• Taux linéaires usuels : bâtiments 5%, matériel 20-25%, mobilier 10-20%, véhicules 25%
• Amortissement dégressif = (V.O. – Σ amort.) × taux dégressif
• Taux dégressif = taux linéaire × coefficient (1,5 à 2,5 selon durée)
• Écriture annuelle : Débit 681 Dotations / Crédit 28x Amortissements
• Valeur nette comptable (VNC) = Valeur d'origine – Amortissements cumulés

─── E. PROVISIONS ───
• Pour dépréciation clients douteux (Débit 697 / Crédit 491)
• Pour dépréciation stocks (Débit 659 / Crédit 39x)
• Pour risques et charges (Débit 691 / Crédit 19x)
• Reprise de provision si le risque disparaît (Débit 19x/39x/49x / Crédit 798/759)

─── F. RÉGULARISATIONS DE FIN D'EXERCICE ───
• Charges à payer (CAP) : charge engagée non encore facturée
  Débit 6xx / Crédit 408 Fournisseurs-factures non parvenues
• Charges constatées d'avance (CCA) : charge payée d'avance
  Débit 476 CCA / Crédit 6xx
• Produits à recevoir (PAR) : produit acquis non encore encaissé
  Débit 418 Clients-produits à recevoir / Crédit 7xx
• Produits constatés d'avance (PCA) : produit encaissé non encore acquis
  Débit 7xx / Crédit 477 PCA

─── G. CALCULS CLÉS ───
• Marge commerciale = Ventes marchandises – Coût d'achat des marchandises vendues
• Production de l'exercice = Ventes de produits + Production stockée + Production immobilisée
• Valeur Ajoutée (VA) = Marge commerciale + Production – Consommations intermédiaires
• Excédent Brut d'Exploitation (EBE) = VA + Subventions d'exploitation – Charges de personnel – Impôts et taxes
• Résultat d'exploitation = EBE + Reprises – Dotations
• Résultat financier = Produits financiers – Charges financières
• Résultat HAO = Produits HAO – Charges HAO
• Résultat avant IS = Résultat exploit. + Résultat financier + Résultat HAO
• Résultat net = Résultat avant IS – IS

─── H. RATIOS FINANCIERS CLÉS ───
• Ratio de liquidité générale = Actif circulant / Dettes CT  (norme > 1)
• Ratio de liquidité réduite = (Créances + Trésorerie) / Dettes CT  (norme > 0,8)
• Ratio d'endettement = Dettes totales / Capitaux propres  (norme < 1)
• Rentabilité économique = Résultat exploitation / Total actif
• Rentabilité financière = Résultat net / Capitaux propres
• BFR = Stocks + Créances clients – Dettes fournisseurs – Dettes fiscales-sociales
• Fonds de Roulement Net (FRN) = Capitaux permanents – Actif immobilisé net
• Trésorerie nette = FRN – BFR

─── I. LIEN FISCALITÉ / COMPTABILITÉ ───
• Le résultat fiscal = résultat comptable + réintégrations – déductions extracomptables
• Amortissements non déductibles (taux > normes fiscales) → réintégration
• Provisions non réglementées → réintégration
• Plus-values sur cessions d'immobilisations → imposables IS
• Comptabilité à partie double obligatoire dès le régime réel (CGI Art. 16)

Réponds toujours de manière pédagogique, avec des exemples chiffrés quand c'est utile.
Si des données en ligne sont fournies, utilise-les en priorité sur tes données internes.
"""

# ─────────────────────────────────────────────
# TEXTES DES COMMANDES
# ─────────────────────────────────────────────
AIDE_TEXT = """📚 *JKBOT — Domaines couverts*

*🧾 FISCALITÉ CAMEROUNAISE (CGI 2026)*
1️⃣ IS — Impôt sur les Sociétés
2️⃣ TVA
3️⃣ IRPP
4️⃣ Retenues à la source
5️⃣ Droits d'accise, Patente, Taxe foncière
6️⃣ TSR, TAF, Droits d'enregistrement
7️⃣ Obligations déclaratives & Pénalités
8️⃣ Création d'entreprise au Cameroun

*📊 COMPTABILITÉ OHADA / SYSCOHADA*
9️⃣ Plan comptable (classes 1 à 9)
🔟 Cycle comptable & Partie double
1️⃣1️⃣ Amortissements & Provisions
1️⃣2️⃣ Régularisations de fin d'exercice
1️⃣3️⃣ Soldes intermédiaires de gestion (SIG)
1️⃣4️⃣ Ratios financiers

─────────────────────
📑 /etats     — Structures des états financiers
📘 /cours     — Liste des cours disponibles
🧮 /calculer  — Calculatrice fiscale guidée
📅 /calendrier — Calendrier fiscal 2026
🔄 /reset     — Effacer l'historique
❓ /aide      — Ce menu
"""

COURS_TEXT = """📘 *COURS DE COMPTABILITÉ DISPONIBLES*

*📗 NIVEAU DÉBUTANT*
▸ "Explique-moi la partie double avec un exemple"
▸ "C'est quoi un débit et un crédit ?"
▸ "Comment lire un plan comptable OHADA ?"
▸ "Différence entre charge et immobilisation ?"
▸ "Qu'est-ce qu'un journal comptable ?"

*📙 NIVEAU INTERMÉDIAIRE*
▸ "Comment comptabiliser un achat de marchandises ?"
▸ "Comment enregistrer une vente avec TVA ?"
▸ "Écriture de paie : comment saisir les salaires ?"
▸ "Comment faire un amortissement linéaire ?"
▸ "Provision pour créances douteuses : comment faire ?"

*📕 NIVEAU AVANCÉ*
▸ "Comment passer les écritures de fin d'exercice ?"
▸ "Différence entre résultat comptable et fiscal ?"
▸ "Comment lire un tableau des flux de trésorerie ?"
▸ "Calculer et interpréter les SIG (EBE, VA, résultat)"
▸ "Comment faire une analyse financière d'un bilan ?"

─────────────────────
🧮 /calculer — Calculatrice fiscale guidée
❓ /aide     — Menu principal
"""

ETATS_TEXT = """📑 *ÉTATS FINANCIERS SYSCOHADA — STRUCTURES*

━━━━━━━━━━━━━━━━━━━━━
📋 *1. BILAN*
━━━━━━━━━━━━━━━━━━━━━
*ACTIF*
┌─ Actif immobilisé (brut – amort = net)
│   • Immobilisations incorporelles
│   • Immobilisations corporelles
│   • Immobilisations financières
├─ Actif circulant d'exploitation
│   • Stocks
│   • Créances clients
│   • Autres créances
└─ Trésorerie actif (banque, caisse)

*PASSIF*
┌─ Capitaux propres
│   • Capital social
│   • Réserves
│   • Report à nouveau
│   • Résultat net de l'exercice
├─ Dettes financières (emprunts > 1 an)
├─ Passif circulant
│   • Dettes fournisseurs
│   • Dettes fiscales (TVA, IS, IRPP)
│   • Dettes sociales (CNPS)
└─ Trésorerie passif
*TOTAL ACTIF = TOTAL PASSIF* ✅

━━━━━━━━━━━━━━━━━━━━━
📋 *2. COMPTE DE RÉSULTAT*
━━━━━━━━━━━━━━━━━━━━━
Ventes – Coût d'achat = *Marge commerciale*
+ Production – Consommations = *Valeur Ajoutée*
– Charges personnel – Impôts = *EBE*
– Dotations + Reprises = *Résultat exploitation*
± Résultat financier = *RAO*
± Résultat HAO – IS = *Résultat net* ✅

💬 Posez vos questions sur n'importe quel état !
"""

CALCULER_TEXT = """🧮 *CALCULATRICE FISCALE GUIDÉE*

*1️⃣ IS* → `IS 15000000`
*2️⃣ IMF* → `IMF 80000000`
*3️⃣ TVA* → `TVA 5000000 200000`
*4️⃣ IRPP* → `IRPP 350000`
*5️⃣ Retenue source* → `RS 500000`
*6️⃣ Amortissement* → `AMORT 12000000 5`
*7️⃣ BFR* → `BFR 3000000 2000000 1500000 500000`

Ou posez directement votre question en langage naturel !
"""

CALENDRIER_TEXT = """📅 *CALENDRIER FISCAL CAMEROUN 2026*

*JANVIER*
▸ 15/01 — TVA, RS, IRPP salaires décembre

*FÉVRIER*
▸ 15/02 — TVA, RS, IRPP salaires janvier

*MARS* ⚠️ _Mois le plus chargé !_
▸ 15/03 — TVA février
▸ *15/03 — Déclaration DSF (IS/Résultat N-1)* 🔴
▸ *15/03 — 1er acompte IS* 🔴
▸ *15/03 — Déclaration annuelle IRPP* 🔴
▸ 31/03 — Patente & Licence + Taxe foncière

*AVRIL → MAI*
▸ 15 de chaque mois — TVA du mois précédent

*JUIN*
▸ 15/06 — TVA mai
▸ *15/06 — 2ème acompte IS* 🔴

*JUILLET → AOÛT*
▸ 15 de chaque mois — TVA du mois précédent

*SEPTEMBRE*
▸ 15/09 — TVA août
▸ *15/09 — 3ème acompte IS* 🔴

*OCTOBRE → DÉCEMBRE*
▸ 15 de chaque mois — TVA du mois précédent
▸ 31/12 — Clôture exercice fiscal

─────────────────────
🔴 = Échéance critique
"""

# ─────────────────────────────────────────────
# CALCULATRICE FISCALE
# ─────────────────────────────────────────────
def calculer_fiscal(texte):
    texte = texte.upper().strip()

    try:
        # IS
        if texte.startswith("IS "):
            benefice = float(texte.split()[1])
            is_base = benefice * 0.30
            cac = is_base * 0.10
            total = is_base + cac
            return (f"💰 *Calcul IS*\n"
                    f"Bénéfice imposable : {benefice:,.0f} FCFA\n"
                    f"IS (30%) : {is_base:,.0f} FCFA\n"
                    f"CAC (10%) : {cac:,.0f} FCFA\n"
                    f"*Total IS dû : {total:,.0f} FCFA*")

        # IMF
        elif texte.startswith("IMF "):
            ca = float(texte.split()[1])
            imf = max(500000, min(ca * 0.01, 2500000))
            return (f"💰 *Calcul IMF*\n"
                    f"CA HT : {ca:,.0f} FCFA\n"
                    f"IMF (1%) : {ca * 0.01:,.0f} FCFA\n"
                    f"*IMF dû (min 500K, max 2,5M) : {imf:,.0f} FCFA*")

        # TVA
        elif texte.startswith("TVA "):
            parts = texte.split()
            ca = float(parts[1])
            tva_deductible = float(parts[2]) if len(parts) > 2 else 0
            tva_collectee = ca * 0.1925
            tva_payer = max(0, tva_collectee - tva_deductible)
            return (f"💰 *Calcul TVA*\n"
                    f"CA HT : {ca:,.0f} FCFA\n"
                    f"TVA collectée (19,25%) : {tva_collectee:,.0f} FCFA\n"
                    f"TVA déductible : {tva_deductible:,.0f} FCFA\n"
                    f"*TVA à décaisser : {tva_payer:,.0f} FCFA*")

        # IRPP
        elif texte.startswith("IRPP "):
            salaire = float(texte.split()[1])
            abattement = max(500000, min(salaire * 0.30, 3000000)) / 12
            revenu_net = salaire - abattement
            revenu_annuel = revenu_net * 12

            if revenu_annuel <= 2000000:
                irpp_annuel = 0
            elif revenu_annuel <= 3000000:
                irpp_annuel = (revenu_annuel - 2000000) * 0.10
            elif revenu_annuel <= 5000000:
                irpp_annuel = 100000 + (revenu_annuel - 3000000) * 0.15
            elif revenu_annuel <= 10000000:
                irpp_annuel = 400000 + (revenu_annuel - 5000000) * 0.25
            else:
                irpp_annuel = 1650000 + (revenu_annuel - 10000000) * 0.35

            irpp_mensuel = irpp_annuel / 12
            cac = irpp_mensuel * 0.10
            total = irpp_mensuel + cac
            return (f"💰 *Calcul IRPP mensuel*\n"
                    f"Salaire brut : {salaire:,.0f} FCFA\n"
                    f"Abattement (30%) : {abattement:,.0f} FCFA\n"
                    f"IRPP mensuel : {irpp_mensuel:,.0f} FCFA\n"
                    f"CAC (10%) : {cac:,.0f} FCFA\n"
                    f"*Total retenu : {total:,.0f} FCFA*")

        # RS
        elif texte.startswith("RS "):
            montant = float(texte.split()[1])
            rs = montant * 0.11
            return (f"💰 *Retenue à la source*\n"
                    f"Honoraires : {montant:,.0f} FCFA\n"
                    f"*RS (11%) : {rs:,.0f} FCFA*\n"
                    f"Net à payer : {montant - rs:,.0f} FCFA")

        # AMORT
        elif texte.startswith("AMORT "):
            parts = texte.split()
            vo = float(parts[1])
            duree = int(parts[2])
            annuite = vo / duree
            taux = (1 / duree) * 100
            return (f"💰 *Amortissement linéaire*\n"
                    f"Valeur d'origine : {vo:,.0f} FCFA\n"
                    f"Durée : {duree} ans\n"
                    f"Taux : {taux:.1f}%\n"
                    f"*Annuité : {annuite:,.0f} FCFA/an*")

        # BFR
        elif texte.startswith("BFR "):
            parts = texte.split()
            stocks = float(parts[1])
            creances = float(parts[2])
            fournisseurs = float(parts[3])
            fiscal_social = float(parts[4]) if len(parts) > 4 else 0
            bfr = stocks + creances - fournisseurs - fiscal_social
            return (f"💰 *Calcul BFR*\n"
                    f"Stocks : {stocks:,.0f} FCFA\n"
                    f"Créances clients : {creances:,.0f} FCFA\n"
                    f"Dettes fournisseurs : {fournisseurs:,.0f} FCFA\n"
                    f"Dettes fiscales/sociales : {fiscal_social:,.0f} FCFA\n"
                    f"*BFR : {bfr:,.0f} FCFA*")

    except Exception:
        pass
    return None

# ─────────────────────────────────────────────
# APPEL GROQ AVEC SCRAPING
# ─────────────────────────────────────────────
def appeler_groq(user_id, question):
    # Récupérer données en ligne
    contexte_web = recherche_fiscal(question)

    # Construire le system prompt enrichi
    system_enrichi = SYSTEM_PROMPT
    if contexte_web:
        system_enrichi += f"\n\n─── DONNÉES EN LIGNE (priorité) ───\n{contexte_web}"

    # Historique de conversation
    messages_historique = get_historique_user(user_id)

    messages = [{"role": "system", "content": system_enrichi}] + \
               messages_historique + \
               [{"role": "user", "content": question}]

    client = Groq(api_key=CLE_GROQ)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        max_tokens=1500,
        temperature=0.3
    )
    return response.choices[0].message.content

# ─────────────────────────────────────────────
# HANDLERS TELEGRAM
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bonjour ! Je suis *JKBOT* 🇨🇲\n"
        "Votre expert en fiscalité camerounaise et comptabilité OHADA.\n\n"
        "Tapez /aide pour voir tout ce que je peux faire !",
        parse_mode="Markdown"
    )

async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(AIDE_TEXT, parse_mode="Markdown")

async def cours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(COURS_TEXT, parse_mode="Markdown")

async def etats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ETATS_TEXT, parse_mode="Markdown")

async def calculer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CALCULER_TEXT, parse_mode="Markdown")

async def calendrier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CALENDRIER_TEXT, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_historique(update.effective_user.id)
    await update.message.reply_text("🔄 Historique effacé ! Nouvelle conversation.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    user_id = update.effective_user.id

    # Vérifier si c'est un calcul direct
    calcul = calculer_fiscal(question)
    if calcul:
        await update.message.reply_text(calcul, parse_mode="Markdown")
        return

    # Indicateur de frappe
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        # Sauvegarder la question
        ajouter_message(user_id, "user", question)

        # Appeler Groq avec scraping
        reponse = appeler_groq(user_id, question)

        # Sauvegarder la réponse
        ajouter_message(user_id, "assistant", reponse)

        await update.message.reply_text(reponse, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Erreur Groq : {e}")
        await update.message.reply_text(
            "⚠️ Une erreur s'est produite. Réessayez dans quelques instants."
        )

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    if not TOKEN_TELEGRAM:
        logger.error("TOKEN_TELEGRAM manquant !")
        return
    if not CLE_GROQ:
        logger.error("CLE_GROQ manquante !")
        return

    app = Application.builder().token(TOKEN_TELEGRAM).build()

    # Commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("aide", aide))
    app.add_handler(CommandHandler("cours", cours))
    app.add_handler(CommandHandler("etats", etats))
    app.add_handler(CommandHandler("calculer", calculer))
    app.add_handler(CommandHandler("calendrier", calendrier))
    app.add_handler(CommandHandler("reset", reset))

    # Messages texte
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ JKBOT démarré !")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()