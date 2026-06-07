import logging
import json
import os
import sys
import random
import base64
import httpx
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, filters,
    ContextTypes, JobQueue
)
from groq import Groq
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF


# ─────────────────────────────────────────────
# RECHERCHE FISCALE WEB (injectée dans les réponses)
# ─────────────────────────────────────────────
def recherche_fiscal(question: str) -> str:
    """Scrape codegeneraldesimpots.com et retourne un extrait pertinent."""
    try:
        url = "https://codegeneraldesimpots.com/cm/"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        texte = ""
        for p in soup.find_all(["p", "h2", "h3", "li"]):
            texte += p.get_text() + "\n"
        texte = texte[:3000]
        return texte
    except Exception as e:
        return ""

def recherche_dgi(question: str) -> str:
    """Recherche sur le site DGI Cameroun."""
    try:
        url = "https://www.impots.cm/"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        texte = ""
        for p in soup.find_all(["p", "h2", "h3", "li", "article"]):
            texte += p.get_text() + "\n"
        return texte[:2000]
    except Exception as e:
        return ""

def rechercher_dans_cgi_local(question: str) -> str:
    """Recherche dans la base CGI locale (cgi_updates.json)."""
    updates = charger_cgi_updates()
    if not updates:
        return ""
    mots_cles = question.lower().split()
    resultats = []
    for u in updates:
        score = sum(1 for mot in mots_cles if mot in u["titre"].lower() or mot in u["contenu"].lower())
        if score > 0:
            resultats.append((score, u))
    resultats.sort(key=lambda x: x[0], reverse=True)
    if not resultats:
        return ""
    texte = "\n\n📋 MISES À JOUR CGI PERTINENTES :\n"
    for _, u in resultats[:3]:
        texte += f"▸ {u['titre']} ({u['annee']}) : {u['contenu']}\n"
    return texte

def enrichir_contexte(question: str) -> str:
    """Construit un contexte enrichi pour la réponse IA."""
    contexte = ""
    # 1. Base CGI locale (toujours)
    cgi_local = rechercher_dans_cgi_local(question)
    if cgi_local:
        contexte += cgi_local

    # 2. Mots-clés déclenchant la recherche web
    mots_web = ["dernier", "récent", "nouveau", "2026", "2027", "circulaire",
                "décret", "loi", "actualité", "modification", "mise à jour", "dgi"]
    if any(mot in question.lower() for mot in mots_web):
        web = recherche_fiscal(question)
        if web:
            contexte += f"\n\n🌐 SOURCE WEB CGI :\n{web}"
        dgi = recherche_dgi(question)
        if dgi:
            contexte += f"\n\n🏛️ SOURCE DGI :\n{dgi}"

    return contexte

def extraire_texte_pdf(chemin: str) -> str:
    """Extrait le texte d'un PDF avec PyMuPDF."""
    try:
        doc = fitz.open(chemin)
        texte = ""
        for page in doc:
            texte += page.get_text()
        doc.close()
        return texte[:6000]
    except Exception as e:
        return f"Impossible de lire le PDF : {e}"

TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRA")
CLE_GROQ = os.environ.get("CLE_GRO")
ADMIN_CODE = os.environ.get("JKBOT_ADMIN_CODE", "JK2027ADMIN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "kamdemjoseph06/JKBOT")
DB_FILE = "historiques.json"
CGI_UPDATES_FILE = "cgi_updates.json"
RAPPEL_FILE = "rappel_subscribers.json"

MODELE_GROQ = "llama-3.3-70b-versatile"

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

╔══════════════════════════════════════════╗
║  COMPTABILITÉ OHADA / SYSCOHADA          ║
╚══════════════════════════════════════════╝

─── A. PLAN COMPTABLE OHADA — CLASSES ───
• Classe 1 : Ressources durables (capitaux propres, dettes financières)
• Classe 2 : Actif immobilisé
• Classe 3 : Stocks
• Classe 4 : Tiers (créances et dettes à court terme)
• Classe 5 : Trésorerie
• Classe 6 : Charges (comptes de gestion)
• Classe 7 : Produits
• Classe 8 : Autres charges et produits (HAO)
• Classe 9 : Comptabilité analytique

─── B. CYCLE COMPTABLE ───
1. Collecte pièces justificatives → 2. Journal → 3. Grand Livre
4. Balance → 5. Inventaire → 6. États financiers → 7. Dépôt légal

─── C. MÉCANISME DE LA PARTIE DOUBLE ───
• Actif augmente au débit ; Passif augmente au crédit
• Charges augmentent au débit ; Produits augmentent au crédit

─── D. AMORTISSEMENTS ───
• Linéaire = Valeur d'origine / Durée
• Taux usuels : bâtiments 5%, matériel 20-25%, mobilier 10-20%, véhicules 25%

─── G. CALCULS CLÉS (SIG) ───
• Marge commerciale = Ventes – Coût d'achat marchandises vendues
• VA = Marge + Production – Consommations intermédiaires
• EBE = VA + Subventions – Charges personnel – Impôts & taxes
• Résultat net = Résultat avant IS – IS

Réponds toujours de manière pédagogique, avec des exemples chiffrés quand c'est utile.
"""

# ─────────────────────────────────────────────
# TEXTES DES COMMANDES
# ─────────────────────────────────────────────
AIDE_TEXT = """📚 *JKBOT — Domaines couverts*

*🧾 FISCALITÉ CAMEROUNAISE (CGI 2026)*
1️⃣ IS — 2️⃣ TVA — 3️⃣ IRPP — 4️⃣ Retenues à la source
5️⃣ Patente, Taxe foncière — 6️⃣ TSR, TAF — 7️⃣ Pénalités

*📊 COMPTABILITÉ OHADA / SYSCOHADA*
8️⃣ Plan comptable — 9️⃣ Cycle comptable
🔟 Amortissements — 1️⃣1️⃣ Régularisations
1️⃣2️⃣ SIG (EBE, VA...) — 1️⃣3️⃣ Ratios financiers

*🧮 CALCULS RAPIDES*
/tva /is /irpp /cnps /patente

*📎 FICHIERS ACCEPTÉS*
PDF (bilan, relevé, contrat...) → analyse automatique
Images (facture, reçu...) → lecture et commentaire

*📑 NAVIGATION*
/etats /cours /calculer /dsf /quiz /calendrier /rappel
/nouveautes /lf /creation /facture /fiche_paie
"""

COURS_TEXT = """📘 *COURS DE COMPTABILITÉ DISPONIBLES*

*📗 DÉBUTANT*
▸ "Explique-moi la partie double"
▸ "C'est quoi un débit et un crédit ?"
▸ "Comment lire un plan comptable OHADA ?"

*📙 INTERMÉDIAIRE*
▸ "Comment comptabiliser un achat de marchandises ?"
▸ "Comment enregistrer une vente avec TVA ?"
▸ "Comment faire un amortissement linéaire ?"

*📕 AVANCÉ*
▸ "Comment passer les écritures de fin d'exercice ?"
▸ "Différence entre résultat comptable et fiscal ?"
▸ "Comment construire un TFT étape par étape ?"

/etats — Structures états financiers
/calculer — Calculatrice fiscale guidée
"""

ETATS_TEXT = """📑 *ÉTATS FINANCIERS SYSCOHADA — STRUCTURES*

━━━━━━━━━━━━━━━━━━━━━
📋 *1. BILAN*
━━━━━━━━━━━━━━━━━━━━━
*ACTIF*
┌─ Actif immobilisé (brut – amort = net)
├─ Actif circulant (stocks, créances, trésorerie)
└─ Total Actif

*PASSIF*
┌─ Capitaux propres (capital, réserves, résultat)
├─ Dettes financières LT
├─ Passif circulant (fournisseurs, fiscal, social)
└─ Total Passif = Total Actif ✅

━━━━━━━━━━━━━━━━━━━━━
📋 *2. COMPTE DE RÉSULTAT*
━━━━━━━━━━━━━━━━━━━━━
Ventes – Coût d'achat = *Marge commerciale*
+ Production – Consommations = *VA*
– Charges personnel – Impôts = *EBE*
± Dotations/Reprises = *Résultat exploitation*
± Financier → *RAO* ± HAO – IS = *Résultat net* ✅

━━━━━━━━━━━━━━━━━━━━━
📋 *3. TABLEAU DES FLUX (TFT)*
━━━━━━━━━━━━━━━━━━━━━
A — Flux exploitation (FNE)
B — Flux investissement (FNI)
C — Flux financement (FNF)
Variation = FNE + FNI + FNF ✅
"""

CALCULER_TEXT = """🧮 *CALCULATRICE FISCALE GUIDÉE*

*1️⃣ IS* : `IS 15000000`
*2️⃣ IMF* : `IMF 80000000`
*3️⃣ TVA* : `TVA 5000000 200000`
*4️⃣ IRPP* : `IRPP 350000`
*5️⃣ CNPS* : `CNPS 400000`
*6️⃣ RS* : `RS 500000`
*7️⃣ AMORT* : `AMORT 12000000 5`
*8️⃣ BFR* : `BFR 3000000 2000000 1500000 500000`

Ou posez directement votre question en langage naturel !
"""

CALENDRIER_TEXT = """📅 *CALENDRIER FISCAL CAMEROUN 2026*

*JANVIER* ▸ 15/01 TVA déc • RS • IRPP salaires déc
*FÉVRIER* ▸ 15/02 TVA jan • RS • IRPP jan
*MARS* ⚠️ _Mois le plus chargé !_
  ▸ 15/03 TVA fév
  ▸ *15/03 DSF (IS/Résultat N-1)* 🔴
  ▸ *15/03 1er acompte IS* 🔴
  ▸ *15/03 Déclaration annuelle IRPP* 🔴
  ▸ 31/03 Patente & Licence • Taxe foncière
*AVRIL* ▸ 15/04 TVA mars
*MAI* ▸ 15/05 TVA avr
*JUIN* ▸ 15/06 TVA mai • *2ème acompte IS* 🔴
*JUILLET* ▸ 15/07 TVA jun
*AOÛT* ▸ 15/08 TVA jul
*SEPTEMBRE* ▸ 15/09 TVA aoû • *3ème acompte IS* 🔴
*OCTOBRE* ▸ 15/10 TVA sep
*NOVEMBRE* ▸ 15/11 TVA oct
*DÉCEMBRE* ▸ 15/12 TVA nov • 31/12 Clôture exercice

🔴 Échéance critique | Pénalité : 1,5%/mois
📞 impots.cm
"""

LF2025_TEXT = """📜 *LOI DE FINANCES 2025 — POINTS CLÉS*

*IS* : Taux 30% maintenu (+CAC = 33%) • IMF plafonné à 2 500 000 FCFA
*TVA* : 19,25% maintenu • Facturation électronique obligatoire (CA > 3 Mds)
*IRPP* : Barème inchangé • Exonération primes scolarité < 100 000/enfant/an
*CNPS* : Taux inchangés • Plafond AVID 750 000 FCFA/mois
*Obligations* : NIU sur toutes factures • Télédéclaration régime réel

ℹ️ impots.cm pour le texte intégral
"""

CREATION_TEXT = """🏢 *GUIDE CRÉATION D'ENTREPRISE AU CAMEROUN*

*Étape 1* — Choisir la forme : SARL (capital min 1M FCFA) recommandée
*Étape 2* — Greffe du Tribunal de Commerce (3-7 jours, ~100 000 FCFA)
*Étape 3* — NIU à la DGI (gratuit, 24-72h)
*Étape 4* — Immatriculation RCCM au CFCE (24h, ~30 000 FCFA)
*Étape 5* — Affiliation CNPS (dès le 1er salarié)
*Étape 6* — Compte bancaire professionnel
*Étape 7* — Obligations post-création (comptabilité, TVA, patente)

💰 *Coût total SARL* : ~230 000 – 450 000 FCFA

🏢 CFCE Yaoundé : Avenue Monseigneur Vogt
🏢 CFCE Douala : Bonanjo, face CCIMA
"""

PATENTE_GUIDE_TEXT = """📊 *GUIDE CALCUL DE LA PATENTE*

*Formule* : Patente = Droit fixe + (16,5% × Valeur locative)

*Exemples droits fixes* :
• Commerce gros : 120 000 FCFA
• Commerce détail : 30 000 FCFA
• Prestataire services : 50 000 FCFA
• Profession libérale : 75 000 FCFA

*Exemple* : Commerce gros, loyer annuel 2 400 000 FCFA
▸ Droit fixe : 120 000
▸ Proportionnel : 2 400 000 × 16,5% = 396 000
▸ *Total : 516 000 FCFA*

📅 Paiement avant le 31 mars | Pénalité retard : 10% + 1,5%/mois
"""

DSF_PROMPT = """Tu es JKBOT en mode *Assistant DSF Intelligent* 🧮.
L'utilisateur décrit une opération comptable en langage naturel.
Génère les écritures comptables SYSCOHADA avec :
1. Journal concerné
2. Comptes débités (N° + libellé SYSCOHADA + montant)
3. Comptes crédités (N° + libellé SYSCOHADA + montant)
4. Explication pédagogique courte
5. Impact fiscal si applicable

Format OBLIGATOIRE :
───────────────────────────
Journal : [nom]
Date    : [date]

DÉBIT  | N° | Libellé SYSCOHADA | Montant
CRÉDIT | N° | Libellé SYSCOHADA | Montant
───────────────────────────
💡 Explication : [courte]
🧾 Fiscal : [impact fiscal]

Si info manquante, pose une question précise.
"""

# ─────────────────────────────────────────────
# CALCULS FISCAUX AUTOMATIQUES
# ─────────────────────────────────────────────
def calculer_is(benefice: float) -> str:
    is_brut = benefice * 0.30
    cac = is_brut * 0.10
    is_total = is_brut + cac
    return (
        f"📊 *Calcul IS sur {benefice:,.0f} FCFA*\n\n"
        f"Base imposable : {benefice:,.0f} FCFA\n"
        f"IS (30%)       : {is_brut:,.0f} FCFA\n"
        f"CAC (10% IS)   : {cac:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*IS total dû   : {is_total:,.0f} FCFA*\n\n"
        f"⚠️ Comparez avec l'IMF (1% CAHT, min 500 000 FCFA)."
    )

def calculer_imf(ca_ht: float) -> str:
    imf = max(500_000, min(ca_ht * 0.01, 2_500_000))
    return (
        f"📊 *Calcul IMF sur CA HT {ca_ht:,.0f} FCFA*\n\n"
        f"1% du CAHT     : {ca_ht * 0.01:,.0f} FCFA\n"
        f"Plancher légal : 500 000 FCFA\n"
        f"Plafond légal  : 2 500 000 FCFA\n"
        f"─────────────────────\n"
        f"*IMF à payer   : {imf:,.0f} FCFA*\n\n"
        f"ℹ️ Dû même en cas de déficit (Art. 62 CGI)."
    )

def calculer_tva(ca_ht: float, tva_deductible: float) -> str:
    tva_collectee = ca_ht * 0.1925
    tva_nette = tva_collectee - tva_deductible
    statut = "à payer à la DGI" if tva_nette >= 0 else "crédit de TVA (report ou remboursement)"
    return (
        f"📊 *Calcul TVA*\n\n"
        f"CA HT                  : {ca_ht:,.0f} FCFA\n"
        f"TVA collectée (19,25%) : {tva_collectee:,.0f} FCFA\n"
        f"TVA déductible         : {tva_deductible:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*TVA nette : {abs(tva_nette):,.0f} FCFA ({statut})*"
    )

def calculer_irpp(salaire_brut: float) -> str:
    abattement = min(max(salaire_brut * 0.30, 500_000 / 12), 3_000_000 / 12)
    revenu_net_mensuel = salaire_brut - abattement
    revenu_annuel = revenu_net_mensuel * 12
    tranches = [
        (2_000_000, 0.00), (1_000_000, 0.10), (2_000_000, 0.15),
        (5_000_000, 0.25), (float('inf'), 0.35),
    ]
    irpp_annuel = 0
    reste = revenu_annuel
    for plafond, taux in tranches:
        if reste <= 0:
            break
        tranche = min(reste, plafond)
        irpp_annuel += tranche * taux
        reste -= tranche
    irpp_cac = irpp_annuel * 1.10
    irpp_mensuel = irpp_cac / 12
    return (
        f"📊 *Calcul IRPP — Salaire {salaire_brut:,.0f} FCFA*\n\n"
        f"Salaire brut mensuel    : {salaire_brut:,.0f} FCFA\n"
        f"Abattement 30%          : {abattement:,.0f} FCFA\n"
        f"Revenu net mensuel      : {revenu_net_mensuel:,.0f} FCFA\n"
        f"Revenu net annualisé    : {revenu_annuel:,.0f} FCFA\n"
        f"IRPP annuel (barème)    : {irpp_annuel:,.0f} FCFA\n"
        f"+ CAC 10%               : {irpp_annuel * 0.10:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*IRPP annuel total      : {irpp_cac:,.0f} FCFA*\n"
        f"*IRPP mensuel à retenir : {irpp_mensuel:,.0f} FCFA*"
    )

def calculer_rs(honoraires: float) -> str:
    rs = honoraires * 0.11
    net_percu = honoraires - rs
    return (
        f"📊 *Retenue à la source — {honoraires:,.0f} FCFA*\n\n"
        f"Montant brut            : {honoraires:,.0f} FCFA\n"
        f"RS (11%)                : {rs:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*Net perçu              : {net_percu:,.0f} FCFA*\n"
        f"*RS à reverser DGI      : {rs:,.0f} FCFA*\n\n"
        f"ℹ️ Non-résident : 15% → RS = {honoraires*0.15:,.0f} FCFA"
    )

def calculer_amort(valeur: float, duree: int) -> str:
    taux = 1 / duree
    annuite = valeur * taux
    lignes = [
        f"📊 *Amortissement linéaire — {valeur:,.0f} FCFA sur {duree} ans*\n",
        f"Taux : {taux*100:.1f}% | Annuité : {annuite:,.0f} FCFA\n",
        f"{'Année':<8} {'Amort.':<16} {'Cumulé':<16} {'VNC'}",
        "─" * 50,
    ]
    cumul = 0
    for annee in range(1, duree + 1):
        cumul += annuite
        vnc = max(valeur - cumul, 0)
        lignes.append(f"  {annee:<7} {annuite:<16,.0f} {cumul:<16,.0f} {vnc:,.0f}")
    return "\n".join(lignes)

def calculer_bfr(stocks: float, creances: float, fournisseurs: float, fiscal_social: float) -> str:
    bfr = stocks + creances - fournisseurs - fiscal_social
    statut = "✅ Besoin de financement" if bfr > 0 else "✅ Ressource de financement (favorable)"
    return (
        f"📊 *Calcul du BFR*\n\n"
        f"Stocks                  : +{stocks:,.0f} FCFA\n"
        f"Créances clients        : +{creances:,.0f} FCFA\n"
        f"Dettes fournisseurs     : -{fournisseurs:,.0f} FCFA\n"
        f"Dettes fiscales/sociales: -{fiscal_social:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*BFR = {bfr:,.0f} FCFA*\n{statut}"
    )

def calculer_cnps(salaire_brut: float) -> str:
    plafond_avid = 750_000
    assiette_avid = min(salaire_brut, plafond_avid)
    sal_avid = assiette_avid * 0.028
    pat_avid = assiette_avid * 0.042
    pat_famille = salaire_brut * 0.07
    pat_at = salaire_brut * 0.0175
    total_sal = sal_avid
    total_pat = pat_avid + pat_famille + pat_at
    net_a_payer = salaire_brut - total_sal
    cout_total = salaire_brut + total_pat
    return (
        f"📊 *Calcul CNPS — Salaire {salaire_brut:,.0f} FCFA*\n\n"
        f"*PART SALARIALE*\n"
        f"AVID 2,8% × {assiette_avid:,.0f} : {sal_avid:,.0f} FCFA\n"
        f"*Net salarié : {net_a_payer:,.0f} FCFA*\n\n"
        f"*PART PATRONALE*\n"
        f"AVID 4,2%      : {pat_avid:,.0f} FCFA\n"
        f"Alloc. fam. 7% : {pat_famille:,.0f} FCFA\n"
        f"AT/MP 1,75%    : {pat_at:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*Charge patronale : {total_pat:,.0f} FCFA*\n"
        f"*Coût employeur   : {cout_total:,.0f} FCFA*\n\n"
        f"ℹ️ Plafond AVID : 750 000 FCFA/mois"
    )

def calculer_tva_simple(montant_ht: float) -> str:
    tva = montant_ht * 0.1925
    ttc = montant_ht + tva
    return (
        f"📊 *Calcul TVA rapide*\n\n"
        f"Montant HT   : {montant_ht:,.0f} FCFA\n"
        f"TVA 19,25%   : {tva:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*Montant TTC : {ttc:,.0f} FCFA*"
    )

def traiter_calcul(texte: str) -> str | None:
    parts = texte.strip().split()
    try:
        cmd = parts[0].upper()
        if cmd == "IS" and len(parts) == 2:
            return calculer_is(float(parts[1].replace(",", "")))
        if cmd == "IMF" and len(parts) == 2:
            return calculer_imf(float(parts[1].replace(",", "")))
        if cmd == "TVA" and len(parts) == 2:
            return calculer_tva_simple(float(parts[1].replace(",", "")))
        if cmd == "TVA" and len(parts) == 3:
            return calculer_tva(float(parts[1].replace(",", "")), float(parts[2].replace(",", "")))
        if cmd == "IRPP" and len(parts) == 2:
            return calculer_irpp(float(parts[1].replace(",", "")))
        if cmd == "CNPS" and len(parts) == 2:
            return calculer_cnps(float(parts[1].replace(",", "")))
        if cmd == "RS" and len(parts) == 2:
            return calculer_rs(float(parts[1].replace(",", "")))
        if cmd == "AMORT" and len(parts) == 3:
            return calculer_amort(float(parts[1].replace(",", "")), int(parts[2]))
        if cmd == "BFR" and len(parts) == 5:
            return calculer_bfr(
                float(parts[1].replace(",", "")), float(parts[2].replace(",", "")),
                float(parts[3].replace(",", "")), float(parts[4].replace(",", ""))
            )
    except (ValueError, IndexError):
        pass
    return None

# ─────────────────────────────────────────────
# BANQUE DE QUESTIONS QUIZ (conservée intacte)
# ─────────────────────────────────────────────
BANQUE_QUESTIONS = [
    {"categorie": "🧾 Fiscalité", "niveau": "⭐ Débutant",
     "question": "Quel est le taux normal de TVA au Cameroun ?",
     "choix": ["A) 17,5%", "B) 19,25%", "C) 20%", "D) 15%"], "reponse": "B",
     "explication": "TVA = 17,5% + 10% CAC = 19,25% (Art. 125 CGI)"},
    {"categorie": "🧾 Fiscalité", "niveau": "⭐ Débutant",
     "question": "Quel est le taux de l'IS hors CAC au Cameroun ?",
     "choix": ["A) 25%", "B) 28%", "C) 30%", "D) 33%"], "reponse": "C",
     "explication": "IS = 30% (Art. 27 CGI). Avec CAC 10% → taux effectif 33%."},
    {"categorie": "🧾 Fiscalité", "niveau": "⭐ Débutant",
     "question": "Seuil TVA au Cameroun ?",
     "choix": ["A) 10M", "B) 30M", "C) 50M FCFA", "D) 100M"], "reponse": "C",
     "explication": "Seuil : CAHT ≥ 50 000 000 FCFA (Art. 124 CGI)."},
    {"categorie": "🧾 Fiscalité", "niveau": "⭐⭐ Intermédiaire",
     "question": "IS + CAC sur bénéfice de 5 000 000 FCFA ?",
     "choix": ["A) 1 500 000", "B) 1 650 000", "C) 1 750 000", "D) 2 000 000"], "reponse": "B",
     "explication": "IS = 5M × 30% = 1 500 000. CAC = 150 000. Total = 1 650 000 FCFA."},
    {"categorie": "📊 Comptabilité", "niveau": "⭐ Débutant",
     "question": "Classe du compte 'Clients' en OHADA ?",
     "choix": ["A) Classe 3", "B) Classe 4", "C) Classe 5", "D) Classe 6"], "reponse": "B",
     "explication": "Clients = compte 411, Classe 4 — Comptes de Tiers."},
    {"categorie": "📊 Comptabilité", "niveau": "⭐⭐ Intermédiaire",
     "question": "Amortissement linéaire d'un véhicule 8 000 000 FCFA sur 4 ans ?",
     "choix": ["A) 1 600 000", "B) 2 000 000", "C) 2 400 000", "D) 4 000 000"], "reponse": "B",
     "explication": "8 000 000 / 4 = 2 000 000 FCFA/an (taux 25%)."},
    {"categorie": "📊 Comptabilité", "niveau": "⭐⭐⭐ Avancé",
     "question": "Cession immobilisation : VO 10M, amort cumulés 8M, prix cession 3M. Résultat ?",
     "choix": ["A) +1M", "B) -7M", "C) +3M", "D) -1M"], "reponse": "A",
     "explication": "VNC = 10M - 8M = 2M. Résultat = 3M - 2M = +1M (plus-value imposable IS)."},
]

# ─────────────────────────────────────────────
# ÉTAT GLOBAL
# ─────────────────────────────────────────────
quiz_sessions: dict = {}
scores: dict = {}
dsf_sessions: set = set()
lang_prefs: dict = {}

def get_score(user_id: str) -> dict:
    if user_id not in scores:
        scores[user_id] = {"correct": 0, "total": 0}
    return scores[user_id]

def nouvelle_question(user_id: str) -> dict:
    q = random.choice(BANQUE_QUESTIONS)
    quiz_sessions[user_id] = q
    return q

def formater_question(q: dict, score_actuel: dict) -> str:
    choix_text = "\n".join(q["choix"])
    return (
        f"{q['categorie']} | {q['niveau']}\n\n"
        f"❓ *{q['question']}*\n\n"
        f"{choix_text}\n\n"
        f"_Répondez par A, B, C ou D_\n"
        f"📊 Score : {score_actuel['correct']}/{score_actuel['total']}"
    )

# ─────────────────────────────────────────────
# PERSISTANCE
# ─────────────────────────────────────────────
def charger_historiques():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def sauvegarder_historiques(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde: {e}")

historiques = charger_historiques()

# ─────────────────────────────────────────────
# BASE CGI AUTO-ÉVOLUTIVE
# ─────────────────────────────────────────────
def charger_cgi_updates() -> list:
    if os.path.exists(CGI_UPDATES_FILE):
        try:
            with open(CGI_UPDATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def sauvegarder_cgi_updates(data: list):
    try:
        with open(CGI_UPDATES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde CGI: {e}")

async def push_fichier_github(chemin_local: str, chemin_repo: str, message_commit: str) -> dict:
    if not GITHUB_TOKEN:
        return {"ok": False, "erreur": "GITHUB_TOKEN non configuré"}
    try:
        with open(chemin_local, "r", encoding="utf-8") as f:
            contenu_brut = f.read()
        contenu_b64 = base64.b64encode(contenu_brut.encode("utf-8")).decode("ascii")
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{chemin_repo}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r_get = await client.get(url, headers=headers)
            sha = r_get.json().get("sha") if r_get.status_code == 200 else None
            payload = {"message": message_commit, "content": contenu_b64}
            if sha:
                payload["sha"] = sha
            r_put = await client.put(url, headers=headers, json=payload)
            if r_put.status_code in (200, 201):
                html_url = r_put.json().get("content", {}).get("html_url", "")
                return {"ok": True, "url": html_url}
            else:
                return {"ok": False, "erreur": r_put.json().get("message", str(r_put.status_code))}
    except Exception as e:
        return {"ok": False, "erreur": str(e)}

def get_system_prompt_dynamique(langue: str = "fr", contexte_enrichi: str = "") -> str:
    updates = charger_cgi_updates()
    base = SYSTEM_PROMPT
    if updates:
        annees = sorted(set(u["annee"] for u in updates), reverse=True)
        for annee in annees:
            entrees = [u for u in updates if u["annee"] == annee]
            base += f"\n\n╔══ MISES À JOUR CGI {annee} ══╗\n"
            for e in entrees:
                base += f"▸ {e['titre']} : {e['contenu']}\n"
    if contexte_enrichi:
        base += f"\n\n{contexte_enrichi}"
    if langue == "en":
        base += "\nPlease respond in English."
    return base

# ─────────────────────────────────────────────
# RAPPELS MENSUELS
# ─────────────────────────────────────────────
def charger_rappel_subscribers() -> set:
    if os.path.exists(RAPPEL_FILE):
        try:
            with open(RAPPEL_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def sauvegarder_rappel_subscribers(data: set):
    try:
        with open(RAPPEL_FILE, "w", encoding="utf-8") as f:
            json.dump(list(data), f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde rappels: {e}")

rappel_subscribers: set = charger_rappel_subscribers()

ECHEANCES_PAR_MOIS = {
    1:  ["📌 15 jan — TVA (décembre)", "📌 15 jan — RS et IRPP salaires décembre"],
    2:  ["📌 15 fév — TVA (janvier)", "📌 28 fév — Patente (si non payée)"],
    3:  ["📌 15 mar — TVA (février)", "📌 15 mar — DSF + IS N-1 🔴", "📌 15 mar — 1er acompte IS 🔴", "📌 31 mar — Patente & Taxe foncière"],
    4:  ["📌 15 avr — TVA (mars)", "📌 30 avr — Acompte IS 1er trim."],
    5:  ["📌 15 mai — TVA (avril)", "📌 31 mai — Déclaration CNPS 1er trim."],
    6:  ["📌 15 jun — TVA (mai)", "📌 15 jun — 2ème acompte IS 🔴"],
    7:  ["📌 15 jul — TVA (juin)", "📌 31 jul — CNPS 2ème trim."],
    8:  ["📌 15 aoû — TVA (juillet)"],
    9:  ["📌 15 sep — TVA (août)", "📌 15 sep — 3ème acompte IS 🔴"],
    10: ["📌 15 oct — TVA (septembre)", "📌 31 oct — CNPS 3ème trim."],
    11: ["📌 15 nov — TVA (octobre)"],
    12: ["📌 15 déc — TVA (novembre)", "📌 31 déc — Inventaire & Clôture exercice"],
}

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

def get_rappel_mensuel(mois: int, annee: int) -> str:
    echeances = ECHEANCES_PAR_MOIS.get(mois, [])
    mois_nom = MOIS_FR[mois]
    texte = f"📅 *RAPPEL FISCAL — {mois_nom} {annee}*\n\n"
    if echeances:
        texte += "\n".join(echeances)
    else:
        texte += "Aucune échéance majeure ce mois-ci."
    texte += "\n\n💡 /calendrier pour le calendrier complet"
    return texte

async def job_rappel_mensuel(context) -> None:
    if datetime.now().day != 1:
        return
    mois = datetime.now().month
    annee = datetime.now().year
    message = get_rappel_mensuel(mois, annee)
    subs = charger_rappel_subscribers()
    for chat_id in list(subs):
        try:
            await context.bot.send_message(chat_id=int(chat_id), text=message, parse_mode="Markdown")
        except Exception as e:
            print(f"⚠️ Rappel non envoyé à {chat_id}: {e}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# COMMANDES
# ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prenom = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Bonjour *{prenom}* !\n\n"
        f"Je suis *JKBOT* 🇨🇲 — Expert en :\n"
        f"🧾 Fiscalité CGI 2026 • 📊 Comptabilité OHADA\n"
        f"🧮 Calculs automatiques • 📅 Calendrier fiscal\n"
        f"📎 *Analyse de fichiers PDF et images*\n\n"
        f"*Calculs rapides :* /tva /is /irpp /cnps\n"
        f"*Navigation :* /aide /dsf /quiz /calendrier\n"
        f"*Nouveauté :* Envoyez un PDF ou une image, je l'analyse !",
        parse_mode="Markdown"
    )

async def cmd_aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(AIDE_TEXT, parse_mode="Markdown")

async def cmd_cours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(COURS_TEXT, parse_mode="Markdown")

async def cmd_etats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ETATS_TEXT, parse_mode="Markdown")

async def cmd_calculer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CALCULER_TEXT, parse_mode="Markdown")

async def cmd_tva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            await update.message.reply_text(calculer_tva_simple(float(context.args[0].replace(",", ""))), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/tva 500000`", parse_mode="Markdown")

async def cmd_is(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            await update.message.reply_text(calculer_is(float(context.args[0].replace(",", ""))), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/is 5000000`", parse_mode="Markdown")

async def cmd_irpp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            await update.message.reply_text(calculer_irpp(float(context.args[0].replace(",", ""))), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/irpp 350000`", parse_mode="Markdown")

async def cmd_cnps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            await update.message.reply_text(calculer_cnps(float(context.args[0].replace(",", ""))), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/cnps 350000`", parse_mode="Markdown")

async def cmd_patente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PATENTE_GUIDE_TEXT, parse_mode="Markdown")

async def cmd_calendrier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CALENDRIER_TEXT, parse_mode="Markdown")

async def cmd_lf2025(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(LF2025_TEXT, parse_mode="Markdown")

async def cmd_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CREATION_TEXT, parse_mode="Markdown")

async def cmd_facture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_chat_action("typing")
    prompt = (
        "Génère un modèle de facture camerounaise complète et conforme (TVA 19,25%, NIU obligatoire). "
        "Inclus : numéro, date, émetteur (nom, adresse, NIU, RCCM), client, désignation, "
        "quantité, prix unitaire HT, total HT, TVA 19,25%, total TTC. "
        "Formate clairement avec séparateurs et mention légale."
    )
    try:
        client = Groq(api_key=CLE_GROQ)
        r = client.chat.completions.create(
            model=MODELE_GROQ,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            max_tokens=1200, temperature=0.3
        )
        await update.message.reply_text(r.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text("❌ Erreur technique. Réessayez.")

async def cmd_fiche_paie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_chat_action("typing")
    prompt = (
        "Génère un modèle de fiche de paie camerounaise (salaire de base 400 000 FCFA). "
        "Inclus : en-tête employeur/salarié, salaire brut, CNPS salarié (2,8%), IRPP, net à payer, "
        "charges patronales CNPS (~13%), coût total employeur. Formate en colonnes."
    )
    try:
        client = Groq(api_key=CLE_GROQ)
        r = client.chat.completions.create(
            model=MODELE_GROQ,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            max_tokens=1200, temperature=0.3
        )
        await update.message.reply_text(r.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text("❌ Erreur technique. Réessayez.")

async def cmd_dsf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    dsf_sessions.add(user_id)
    await update.message.reply_text(
        "🧮 *Mode DSF activé — Écritures SYSCOHADA*\n\n"
        "Décrivez votre opération en langage naturel.\n\n"
        "*Exemples :*\n"
        "▸ \"Achat marchandises 500 000 FCFA TTC à crédit\"\n"
        "▸ \"Vente 1 200 000 FCFA TTC par virement\"\n"
        "▸ \"Paiement salaires : brut 600 000, CNPS, IRPP\"\n"
        "▸ \"Dotation amortissement matériel 8M sur 4 ans, 2ème année\"\n\n"
        "Tapez /stop pour quitter.",
        parse_mode="Markdown"
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    dsf_sessions.discard(user_id)
    await update.message.reply_text("✅ Mode DSF désactivé.")

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    current = lang_prefs.get(user_id, "fr")
    if current == "fr":
        lang_prefs[user_id] = "en"
        await update.message.reply_text("🇬🇧 *Language switched to English!*\nType /lang to switch back.", parse_mode="Markdown")
    else:
        lang_prefs[user_id] = "fr"
        await update.message.reply_text("🇫🇷 *Langue réglée sur le français !*\nTapez /lang pour repasser en anglais.", parse_mode="Markdown")

async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    q = nouvelle_question(user_id)
    await update.message.reply_text(formater_question(q, get_score(user_id)), parse_mode="Markdown")

async def cmd_quiz_fiscal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    fiscales = [q for q in BANQUE_QUESTIONS if "Fiscalité" in q["categorie"]]
    q = random.choice(fiscales)
    quiz_sessions[user_id] = q
    await update.message.reply_text(formater_question(q, get_score(user_id)), parse_mode="Markdown")

async def cmd_quiz_compta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    compta = [q for q in BANQUE_QUESTIONS if "Comptabilité" in q["categorie"]]
    q = random.choice(compta)
    quiz_sessions[user_id] = q
    await update.message.reply_text(formater_question(q, get_score(user_id)), parse_mode="Markdown")

async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    s = get_score(user_id)
    total = s["total"]
    correct = s["correct"]
    if total == 0:
        await update.message.reply_text("📊 Pas encore de questions répondues. Tapez /quiz !")
        return
    pct = round(correct / total * 100)
    mention = "🏆 Excellent !" if pct >= 80 else ("👍 Bien !" if pct >= 60 else ("📖 Passable." if pct >= 40 else "💪 Courage !"))
    await update.message.reply_text(
        f"📊 *Votre score JKBOT*\n\n"
        f"✅ Bonnes : {correct} | ❌ Mauvaises : {total - correct}\n"
        f"🎯 Taux : *{pct}%* — {mention}",
        parse_mode="Markdown"
    )

async def cmd_rappel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in rappel_subscribers:
        rappel_subscribers.discard(user_id)
        sauvegarder_rappel_subscribers(rappel_subscribers)
        await update.message.reply_text("🔕 Rappels désactivés. Tapez /rappel pour réactiver.")
    else:
        rappel_subscribers.add(user_id)
        sauvegarder_rappel_subscribers(rappel_subscribers)
        maintenant = datetime.now()
        apercu = get_rappel_mensuel(maintenant.month, maintenant.year)
        await update.message.reply_text(
            f"🔔 *Rappels mensuels activés !*\n\n{apercu}",
            parse_mode="Markdown"
        )

async def cmd_nouveautes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    updates = charger_cgi_updates()
    if not updates:
        await update.message.reply_text("📋 Aucune mise à jour enregistrée.")
        return
    tri = sorted(updates, key=lambda x: (x["annee"], x.get("date_ajout", "")), reverse=True)
    texte = "📢 *Nouveautés fiscales & comptables*\n\n"
    for u in tri[:10]:
        texte += f"▸ *{u['titre']}* ({u['annee']})\n_{u['contenu'][:200]}{'...' if len(u['contenu'])>200 else ''}_\n\n"
    if len(texte) > 4096:
        for i in range(0, len(texte), 4096):
            await update.message.reply_text(texte[i:i+4096], parse_mode="Markdown")
    else:
        await update.message.reply_text(texte, parse_mode="Markdown")

async def cmd_lf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage : `/lf 2026`", parse_mode="Markdown")
        return
    try:
        annee = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Année invalide.")
        return
    if annee == 2025:
        await update.message.reply_text(LF2025_TEXT, parse_mode="Markdown")
        return
    updates = [u for u in charger_cgi_updates() if u["annee"] == annee]
    if not updates:
        await update.message.reply_text(f"📋 Aucune disposition enregistrée pour {annee}.")
        return
    texte = f"📜 *Loi de Finances {annee}*\n\n"
    for e in updates:
        texte += f"▸ *{e['titre']}*\n{e['contenu']}\n\n"
    await update.message.reply_text(texte[:4096], parse_mode="Markdown")

async def cmd_maj_cgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Usage : `/maj_cgi CODE ANNEE TITRE | CONTENU`\n"
            "Exemple : `/maj_cgi JK2027ADMIN 2027 Nouveau taux IS | Le taux passe à 28%.`",
            parse_mode="Markdown"
        )
        return
    if context.args[0] != ADMIN_CODE:
        await update.message.reply_text("🔒 Code administrateur invalide.")
        return
    try:
        annee = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Année invalide.")
        return
    reste = " ".join(context.args[2:])
    if "|" not in reste:
        await update.message.reply_text("❌ Séparez TITRE et CONTENU avec `|`.", parse_mode="Markdown")
        return
    titre, contenu = reste.split("|", 1)
    titre, contenu = titre.strip(), contenu.strip()
    updates = charger_cgi_updates()
    nouvel_id = max((u["id"] for u in updates), default=0) + 1
    auteur = update.effective_user.username or update.effective_user.first_name or "admin"
    updates.append({
        "id": nouvel_id, "annee": annee, "titre": titre, "contenu": contenu,
        "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M"), "auteur": auteur
    })
    sauvegarder_cgi_updates(updates)
    await update.message.reply_text(
        f"✅ *Mise à jour CGI {annee} enregistrée !*\n📌 {titre}\n🔄 Sync GitHub...",
        parse_mode="Markdown"
    )
    resultat = await push_fichier_github(CGI_UPDATES_FILE, "telegram-bot/cgi_updates.json",
                                         f"CGI {annee}: {titre}")
    if resultat["ok"]:
        await update.message.reply_text(f"🐙 GitHub synchronisé !", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ Local OK, GitHub : `{resultat['erreur']}`", parse_mode="Markdown")

async def cmd_historique_cgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    updates = charger_cgi_updates()
    if not updates:
        await update.message.reply_text("📋 Aucune mise à jour. Utilisez `/maj_cgi`.", parse_mode="Markdown")
        return
    tri = sorted(updates, key=lambda x: (x["annee"], x.get("date_ajout", "")), reverse=True)
    texte = f"📜 *Journal CGI — {len(updates)} disposition(s)*\n\n"
    for u in tri:
        texte += f"▸ *#{u['id']}* {u['titre']} ({u['annee']})\n_{u['contenu'][:100]}…_\n\n"
    await update.message.reply_text(texte[:4096], parse_mode="Markdown")

async def cmd_supprimer_cgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage : `/supprimer_cgi CODE ID`", parse_mode="Markdown")
        return
    if context.args[0] != ADMIN_CODE:
        await update.message.reply_text("🔒 Code invalide.")
        return
    try:
        cible_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ ID invalide.")
        return
    updates = charger_cgi_updates()
    entree = next((u for u in updates if u["id"] == cible_id), None)
    if not entree:
        await update.message.reply_text(f"❌ ID #{cible_id} introuvable.")
        return
    sauvegarder_cgi_updates([u for u in updates if u["id"] != cible_id])
    await update.message.reply_text(f"🗑️ Disposition #{cible_id} supprimée : {entree['titre']}")
    await push_fichier_github(CGI_UPDATES_FILE, "telegram-bot/cgi_updates.json",
                              f"CGI: suppression #{cible_id}")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    historiques[user_id] = []
    dsf_sessions.discard(user_id)
    sauvegarder_historiques(historiques)
    await update.message.reply_text("🔄 Historique effacé et mode DSF réinitialisé !")

# ─────────────────────────────────────────────
# HANDLER FICHIERS PDF
# ─────────────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit un PDF, extrait le texte, et demande à l'IA de l'analyser."""
    doc = update.message.document
    if not doc.mime_type or doc.mime_type != "application/pdf":
        await update.message.reply_text("📎 Je peux analyser les fichiers *PDF* uniquement.\nEnvoyez un PDF (bilan, relevé, contrat, déclaration...).", parse_mode="Markdown")
        return
    await update.message.reply_chat_action("typing")
    await update.message.reply_text("📥 PDF reçu, extraction en cours...")
    try:
        fichier = await context.bot.get_file(doc.file_id)
        chemin_local = f"/tmp/jkbot_{doc.file_id}.pdf"
        await fichier.download_to_drive(chemin_local)
        texte_pdf = extraire_texte_pdf(chemin_local)
        os.remove(chemin_local)
        if not texte_pdf or texte_pdf.startswith("Impossible"):
            await update.message.reply_text("❌ Impossible d'extraire le texte de ce PDF. Vérifiez qu'il n'est pas scanné (image).")
            return
        user_id = str(update.effective_user.id)
        langue = lang_prefs.get(user_id, "fr")
        caption = update.message.caption or "Analyse ce document. S'il s'agit d'un document comptable ou fiscal, identifie les éléments clés, les montants, les obligations et donne des conseils."
        prompt_analyse = f"Voici le contenu extrait d'un document PDF :\n\n{texte_pdf}\n\nInstruction : {caption}"
        client = Groq(api_key=CLE_GROQ)
        reponse = client.chat.completions.create(
            model=MODELE_GROQ,
            messages=[
                {"role": "system", "content": get_system_prompt_dynamique(langue)},
                {"role": "user", "content": prompt_analyse}
            ],
            max_tokens=2000, temperature=0.4
        )
        texte = reponse.choices[0].message.content
        if len(texte) > 4096:
            for i in range(0, len(texte), 4096):
                await update.message.reply_text(texte[i:i+4096])
        else:
            await update.message.reply_text(texte)
    except Exception as e:
        print(f"❌ Erreur PDF: {e}")
        await update.message.reply_text("❌ Erreur lors de l'analyse du PDF. Réessayez.")

# ─────────────────────────────────────────────
# HANDLER IMAGES (factures, reçus)
# ─────────────────────────────────────────────
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit une image et demande à l'IA de la décrire/analyser."""
    await update.message.reply_chat_action("typing")
    try:
        photo = update.message.photo[-1]  # Meilleure résolution
        fichier = await context.bot.get_file(photo.file_id)
        chemin_local = f"/tmp/jkbot_{photo.file_id}.jpg"
        await fichier.download_to_drive(chemin_local)
        with open(chemin_local, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("ascii")
        os.remove(chemin_local)
        caption = update.message.caption or "Analyse cette image. S'il s'agit d'une facture, d'un reçu ou d'un document comptable, identifie tous les éléments importants."
        user_id = str(update.effective_user.id)
        langue = lang_prefs.get(user_id, "fr")
        # Groq supporte les images via llama-3.2-11b-vision-preview
        client = Groq(api_key=CLE_GROQ)
        reponse = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": get_system_prompt_dynamique(langue)},
                {"role": "user", "content": [
                    {"type": "text", "text": caption},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]}
            ],
            max_tokens=1500, temperature=0.4
        )
        texte = reponse.choices[0].message.content
        if len(texte) > 4096:
            for i in range(0, len(texte), 4096):
                await update.message.reply_text(texte[i:i+4096])
        else:
            await update.message.reply_text(texte)
    except Exception as e:
        print(f"❌ Erreur image: {e}")
        await update.message.reply_text(
            "❌ Impossible d'analyser cette image.\n"
            "💡 Astuce : Envoyez un PDF pour une meilleure analyse."
        )

# ─────────────────────────────────────────────
# HANDLER MESSAGES TEXTE
# ─────────────────────────────────────────────
async def repondre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texte_recu = update.message.text.strip()
    if user_id not in historiques:
        historiques[user_id] = []

    # ── Quiz ──
    if user_id in quiz_sessions and texte_recu.upper() in ("A", "B", "C", "D"):
        q = quiz_sessions[user_id]
        reponse_user = texte_recu.upper()
        bonne_reponse = q["reponse"]
        score = get_score(user_id)
        score["total"] += 1
        if reponse_user == bonne_reponse:
            score["correct"] += 1
            feedback = f"✅ *Bonne réponse !* ({bonne_reponse})\n\n"
        else:
            feedback = f"❌ *Mauvaise.* Vous : *{reponse_user}* | Bonne : *{bonne_reponse}*\n\n"
        del quiz_sessions[user_id]
        pct = round(score["correct"] / score["total"] * 100)
        await update.message.reply_text(
            f"{feedback}💡 {q['explication']}\n\n"
            f"📊 Score : {score['correct']}/{score['total']} ({pct}%)\n"
            f"➡️ /quiz pour continuer",
            parse_mode="Markdown"
        )
        return

    # ── Calculs automatiques ──
    resultat_calcul = traiter_calcul(texte_recu)
    if resultat_calcul:
        await update.message.reply_text(resultat_calcul, parse_mode="Markdown")
        return

    # ── Mode DSF ──
    if user_id in dsf_sessions:
        await update.message.reply_chat_action("typing")
        try:
            client = Groq(api_key=CLE_GROQ)
            reponse = client.chat.completions.create(
                model=MODELE_GROQ,
                messages=[{"role": "system", "content": DSF_PROMPT},
                          {"role": "user", "content": texte_recu}],
                max_tokens=1500, temperature=0.3
            )
            texte = reponse.choices[0].message.content
            if len(texte) > 4096:
                for i in range(0, len(texte), 4096):
                    await update.message.reply_text(texte[i:i+4096])
            else:
                await update.message.reply_text(texte)
        except Exception as e:
            print(f"❌ Erreur DSF: {e}")
            await update.message.reply_text("❌ Erreur technique. Réessayez.")
        return

    # ── Réponse IA normale avec contexte enrichi ──
    await update.message.reply_chat_action("typing")
    try:
        client = Groq(api_key=CLE_GROQ)
        historiques[user_id].append({"role": "user", "content": texte_recu})
        langue = lang_prefs.get(user_id, "fr")

        # Enrichissement du contexte (CGI local + web si pertinent)
        contexte_enrichi = enrichir_contexte(texte_recu)
        system = get_system_prompt_dynamique(langue, contexte_enrichi)

        reponse = client.chat.completions.create(
            model=MODELE_GROQ,
            messages=[{"role": "system", "content": system}] + historiques[user_id],
            max_tokens=1500, temperature=0.5
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

# ─────────────────────────────────────────────
# LANCEMENT
# ─────────────────────────────────────────────
def main():
    if not TOKEN_TELEGRAM:
        print("❌ TOKEN_TELEGRA manquant")
        sys.exit(1)
    if not CLE_GROQ:
        print("❌ CLE_GRO manquante")
        sys.exit(1)

    print("🤖 Initialisation JKBOT v2.0 (CGI 2026 + SYSCOHADA + PDF + Images)...")
    app = Application.builder().token(TOKEN_TELEGRAM).build()

    # Commandes
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("aide", cmd_aide))
    app.add_handler(CommandHandler("cours", cmd_cours))
    app.add_handler(CommandHandler("etats", cmd_etats))
    app.add_handler(CommandHandler("calculer", cmd_calculer))
    app.add_handler(CommandHandler("tva", cmd_tva))
    app.add_handler(CommandHandler("is", cmd_is))
    app.add_handler(CommandHandler("irpp", cmd_irpp))
    app.add_handler(CommandHandler("cnps", cmd_cnps))
    app.add_handler(CommandHandler("patente", cmd_patente))
    app.add_handler(CommandHandler("calendrier", cmd_calendrier))
    app.add_handler(CommandHandler("lf2025", cmd_lf2025))
    app.add_handler(CommandHandler("creation", cmd_creation))
    app.add_handler(CommandHandler("facture", cmd_facture))
    app.add_handler(CommandHandler("fiche_paie", cmd_fiche_paie))
    app.add_handler(CommandHandler("dsf", cmd_dsf))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("quiz_fiscal", cmd_quiz_fiscal))
    app.add_handler(CommandHandler("quiz_compta", cmd_quiz_compta))
    app.add_handler(CommandHandler("score", cmd_score))
    app.add_handler(CommandHandler("rappel", cmd_rappel))
    app.add_handler(CommandHandler("nouveautes", cmd_nouveautes))
    app.add_handler(CommandHandler("lf", cmd_lf))
    app.add_handler(CommandHandler("maj_cgi", cmd_maj_cgi))
    app.add_handler(CommandHandler("historique_cgi", cmd_historique_cgi))
    app.add_handler(CommandHandler("supprimer_cgi", cmd_supprimer_cgi))

    # Fichiers
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Messages texte
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre))

    # Job rappels mensuels
    job_queue = app.job_queue
    if job_queue:
        import pytz
        from datetime import time as dt_time
        tz_cm = pytz.timezone("Africa/Douala")
        job_queue.run_daily(
            job_rappel_mensuel,
            time=dt_time(hour=7, minute=0, tzinfo=tz_cm),
            name="rappel_mensuel"
        )
        print("📅 Rappels mensuels programmés à 07h00 (Douala)")
    else:
        print("⚠️ JobQueue non disponible")

    print("✅ JKBOT v2.0 prêt. Connexion Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
