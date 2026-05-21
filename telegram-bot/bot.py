import logging
import json
import os
import sys
import random
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

╔══════════════════════════════════════════╗
║  ÉTATS FINANCIERS SYSCOHADA              ║
╚══════════════════════════════════════════╝

─── H. BILAN (structure SYSCOHADA) ───
ACTIF :
  Actif immobilisé :
    Immobilisations incorporelles (nettes)
    Immobilisations corporelles (nettes)
    Immobilisations financières
  Actif circulant :
    Stocks et encours
    Créances clients et comptes rattachés
    Autres créances
    Trésorerie actif
  Total Actif

PASSIF :
  Capitaux propres :
    Capital social
    Réserves (légale, statutaire, facultative)
    Report à nouveau
    Résultat net de l'exercice
  Dettes financières et ressources assimilées :
    Emprunts obligataires
    Emprunts bancaires
  Passif circulant :
    Dettes fournisseurs
    Dettes fiscales (TVA, IS, IRPP)
    Dettes sociales
    Autres dettes
  Total Passif
  (Total Actif = Total Passif)

─── I. COMPTE DE RÉSULTAT (SYSCOHADA) ───
(+) Ventes de marchandises
(-) Achats de marchandises + Δ stocks
= MARGE COMMERCIALE
(+) Production vendue (produits finis)
(+) Production stockée / déstockée
(+) Production immobilisée
= CHIFFRE D'AFFAIRES NET
(-) Consommations en provenance de tiers
= VALEUR AJOUTÉE (VA)
(+) Subventions d'exploitation
(-) Impôts, taxes et versements assimilés
(-) Charges de personnel (salaires + charges sociales)
= EXCÉDENT BRUT D'EXPLOITATION (EBE)
(+) Reprises de provisions d'exploitation
(-) Dotations aux amortissements et provisions
(+/-) Autres produits / charges d'exploitation
= RÉSULTAT D'EXPLOITATION
(+) Produits financiers (intérêts reçus, dividendes)
(-) Charges financières (intérêts payés)
= RÉSULTAT FINANCIER
= RÉSULTAT DES ACTIVITÉS ORDINAIRES (RAO)
(+) Produits HAO (cessions d'immobilisations)
(-) Charges HAO (VNC des immobilisations cédées)
= RÉSULTAT HAO
(-) Participation des travailleurs
(-) Impôt sur les sociétés (IS)
= RÉSULTAT NET DE L'EXERCICE

─── J. TABLEAU DES FLUX DE TRÉSORERIE (TFT) ───
A. FLUX D'EXPLOITATION :
  Résultat net
  (+) Dotations amortissements/provisions
  (-) Reprises provisions
  (+/-) Variation des stocks
  (+/-) Variation créances clients
  (+/-) Variation dettes fournisseurs
  (+/-) Variation autres éléments du BFR
  = FLUX NET D'EXPLOITATION (FNE)

B. FLUX D'INVESTISSEMENT :
  Acquisitions d'immobilisations
  Cessions d'immobilisations (produit de cession)
  Variation des immobilisations financières
  = FLUX NET D'INVESTISSEMENT (FNI)

C. FLUX DE FINANCEMENT :
  Augmentation de capital
  Emprunts nouveaux souscrits
  Remboursements d'emprunts
  Dividendes versés
  = FLUX NET DE FINANCEMENT (FNF)

VARIATION DE TRÉSORERIE = FNE + FNI + FNF
Trésorerie finale = Trésorerie initiale + Variation de trésorerie

─── K. RATIOS FINANCIERS CLÉS ───
• Ratio de liquidité générale = Actif circulant / Dettes CT  (norme > 1)
• Ratio de liquidité réduite = (Créances + Trésorerie) / Dettes CT  (norme > 0,8)
• Ratio d'endettement = Dettes totales / Capitaux propres  (norme < 1)
• Rentabilité économique = Résultat exploitation / Total actif
• Rentabilité financière = Résultat net / Capitaux propres
• BFR = Stocks + Créances clients – Dettes fournisseurs – Dettes fiscales-sociales
• Fonds de Roulement Net (FRN) = Capitaux permanents – Actif immobilisé net
• Trésorerie nette = FRN – BFR

─── L. LIEN FISCALITÉ / COMPTABILITÉ ───
• Le résultat fiscal = résultat comptable + réintégrations – déductions extracomptables
• Amortissements non déductibles (taux > normes fiscales) → réintégration
• Provisions non réglementées → réintégration
• Plus-values sur cessions d'immobilisations → imposables IS
• Comptabilité à partie double obligatoire dès le régime réel (CGI Art. 16)

Réponds toujours de manière pédagogique, avec des exemples chiffrés quand c'est utile.
"""

# ─────────────────────────────────────────────
# TEXTES DES COMMANDES
# ─────────────────────────────────────────────
AIDE_TEXT = """📚 *JKBOT — Domaines couverts*

*🧾 FISCALITÉ CAMEROUNAISE (CGI 2026)*
1️⃣ IS — Impôt sur les Sociétés
   ▸ "Calculer l'IS sur un bénéfice de 10M FCFA"
   ▸ "C'est quoi l'IMF ?"
2️⃣ TVA
   ▸ "Mon entreprise est-elle assujettie à la TVA ?"
   ▸ "Taux de TVA sur les produits alimentaires ?"
3️⃣ IRPP
   ▸ "IRPP sur un salaire de 500 000 FCFA/mois ?"
4️⃣ Retenues à la source
   ▸ "Taux RS sur honoraires versés à un consultant ?"
5️⃣ Droits d'accise, Patente, Taxe foncière
6️⃣ TSR, TAF, Droits d'enregistrement
7️⃣ Obligations déclaratives & Pénalités

*📊 COMPTABILITÉ OHADA / SYSCOHADA*
8️⃣ Plan comptable (classes 1 à 9)
   ▸ "À quelle classe appartient le compte Clients ?"
9️⃣ Cycle comptable & Partie double
   ▸ "Comment enregistrer une vente à crédit ?"
🔟 Amortissements & Provisions
   ▸ "Calculer l'amortissement linéaire d'un véhicule"
1️⃣1️⃣ Régularisations de fin d'exercice
   ▸ "C'est quoi une charge à payer ?"
1️⃣2️⃣ Soldes intermédiaires de gestion (SIG)
   ▸ "Comment calculer la Valeur Ajoutée ?"
1️⃣3️⃣ Ratios financiers
   ▸ "Calculer le BFR et le FRN ?"

─────────────────────
📑 /etats   — Structures des états financiers
📘 /cours   — Liste des cours disponibles
🧮 /calculer — Calculatrice fiscale guidée
🔄 /reset   — Effacer l'historique
❓ /aide    — Ce menu
"""

COURS_TEXT = """📘 *COURS DE COMPTABILITÉ DISPONIBLES*

Tapez la commande ou posez la question directement.

*📗 NIVEAU DÉBUTANT*
▸ "Explique-moi la partie double avec un exemple"
▸ "C'est quoi un débit et un crédit ?"
▸ "Comment lire un plan comptable OHADA ?"
▸ "Différence entre charge et immobilisation ?"
▸ "Qu'est-ce qu'un journal comptable ?"
▸ "Comment fonctionne un grand livre ?"
▸ "C'est quoi une balance de vérification ?"

*📙 NIVEAU INTERMÉDIAIRE*
▸ "Comment comptabiliser un achat de marchandises ?"
▸ "Comment enregistrer une vente avec TVA ?"
▸ "Écriture de paie : comment saisir les salaires ?"
▸ "Comment faire un amortissement linéaire ?"
▸ "Comment comptabiliser un emprunt bancaire ?"
▸ "Provision pour créances douteuses : comment faire ?"
▸ "Différence entre charge à payer et CCA ?"
▸ "Comment comptabiliser une cession d'immobilisation ?"

*📕 NIVEAU AVANCÉ*
▸ "Comment passer les écritures de fin d'exercice ?"
▸ "Comment calculer et interpréter le BFR ?"
▸ "Différence entre résultat comptable et fiscal ?"
▸ "Comment lire un tableau des flux de trésorerie ?"
▸ "Calculer et interpréter les SIG (EBE, VA, résultat)"
▸ "Comment faire une analyse financière d'un bilan ?"
▸ "Consolider les comptes d'un groupe ?"

*📊 ÉTATS FINANCIERS*
▸ /etats — Voir les structures complètes
▸ "Expliquer la structure du bilan SYSCOHADA"
▸ "Comment lire un compte de résultat ?"
▸ "Construire un TFT étape par étape"

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
│   • Immobilisations incorporelles (fonds commercial, brevets...)
│   • Immobilisations corporelles (terrains, bâtiments, matériel...)
│   • Immobilisations financières (participations, prêts > 1 an)
├─ Actif circulant HAO
├─ Actif circulant d'exploitation
│   • Stocks (marchandises, matières, produits finis)
│   • Créances clients et comptes rattachés
│   • Autres créances (État-TVA déductible, avances fournisseurs)
└─ Trésorerie actif (banque, caisse, CCP)

*PASSIF*
┌─ Capitaux propres et ressources assimilées
│   • Capital social
│   • Réserves (légale 5%, statutaires, facultatives)
│   • Report à nouveau (N-1)
│   • Résultat net de l'exercice
│   • Subventions d'investissement
├─ Dettes financières (emprunts > 1 an)
├─ Passif circulant HAO
├─ Passif circulant d'exploitation
│   • Dettes fournisseurs
│   • Dettes fiscales (TVA collectée, IS dû, IRPP)
│   • Dettes sociales (CNPS, salaires à payer)
│   • Autres dettes
└─ Trésorerie passif (découverts bancaires)
*TOTAL ACTIF = TOTAL PASSIF* ✅

━━━━━━━━━━━━━━━━━━━━━
📋 *2. COMPTE DE RÉSULTAT*
━━━━━━━━━━━━━━━━━━━━━
Ventes marchandises
— Coût d'achat marchandises vendues
= *Marge commerciale*
+ Production de l'exercice
— Consommations intermédiaires
= *Valeur Ajoutée (VA)*
— Charges personnel — Impôts & taxes
= *EBE (Excédent Brut d'Exploitation)*
— Dotations + Reprises ± Autres
= *Résultat d'exploitation*
± Résultat financier
= *RAO (Résultat Activités Ordinaires)*
± Résultat HAO
— IS
= *Résultat net de l'exercice* ✅

━━━━━━━━━━━━━━━━━━━━━
📋 *3. TABLEAU DES FLUX DE TRÉSORERIE (TFT)*
━━━━━━━━━━━━━━━━━━━━━
*A — Flux d'exploitation*
  Résultat net + Amortissements/provisions
  ± Variation BFR (stocks, créances, fournisseurs)
  = *Flux Net d'Exploitation (FNE)*

*B — Flux d'investissement*
  Acquisitions immobilisations (–)
  Cessions immobilisations (+)
  = *Flux Net d'Investissement (FNI)*

*C — Flux de financement*
  Augmentation capital / emprunts (+)
  Remboursements emprunts / dividendes (–)
  = *Flux Net de Financement (FNF)*

*Variation trésorerie = FNE + FNI + FNF*
*Trésorerie finale = Trésorerie initiale + Variation* ✅

━━━━━━━━━━━━━━━━━━━━━
📋 *4. TABLEAU DE VARIATION DES CP*
━━━━━━━━━━━━━━━━━━━━━
Capital N-1 + Augmentation capital
+ Résultat N-1 affecté en réserves
– Dividendes distribués
+ Résultat net N
= *Capitaux propres N* ✅

💬 Posez vos questions sur n'importe quel état !
"""

CALCULER_TEXT = """🧮 *CALCULATRICE FISCALE GUIDÉE*

Choisissez un calcul et envoyez le numéro + vos données :

*1️⃣ IS (Impôt sur les Sociétés)*
Format : `IS [bénéfice en FCFA]`
Exemple : `IS 15000000`

*2️⃣ IMF (Impôt Minimum Forfaitaire)*
Format : `IMF [chiffre d'affaires HT en FCFA]`
Exemple : `IMF 80000000`

*3️⃣ TVA à décaisser*
Format : `TVA [CA HT en FCFA] [TVA déductible en FCFA]`
Exemple : `TVA 5000000 200000`

*4️⃣ IRPP mensuel sur salaire*
Format : `IRPP [salaire brut mensuel en FCFA]`
Exemple : `IRPP 350000`

*5️⃣ Retenue à la source sur honoraires*
Format : `RS [montant honoraires en FCFA]`
Exemple : `RS 500000`

*6️⃣ Amortissement linéaire*
Format : `AMORT [valeur d'origine] [durée en années]`
Exemple : `AMORT 12000000 5`

*7️⃣ BFR (Besoin en Fonds de Roulement)*
Format : `BFR [stocks] [créances clients] [dettes fournisseurs] [dettes fiscales-sociales]`
Exemple : `BFR 3000000 2000000 1500000 500000`

─────────────────────
Ou posez directement votre question en langage naturel !
"""

# ─────────────────────────────────────────────
# CALCULS FISCAUX AUTOMATIQUES
# ─────────────────────────────────────────────
def calculer_is(benefice: float) -> str:
    is_brut = benefice * 0.30
    cac = is_brut * 0.10
    is_total = is_brut + cac
    imf_brut = 0
    return (
        f"📊 *Calcul IS sur {benefice:,.0f} FCFA*\n\n"
        f"Base imposable : {benefice:,.0f} FCFA\n"
        f"IS (30%)       : {is_brut:,.0f} FCFA\n"
        f"CAC (10% IS)   : {cac:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*IS total dû   : {is_total:,.0f} FCFA*\n\n"
        f"⚠️ Comparez avec l'IMF (1% du CAHT, min 500 000 FCFA).\n"
        f"Vous payez le montant le plus élevé entre IS et IMF."
    )

def calculer_imf(ca_ht: float) -> str:
    imf = ca_ht * 0.01
    imf = max(500_000, min(imf, 2_500_000))
    return (
        f"📊 *Calcul IMF sur CA HT {ca_ht:,.0f} FCFA*\n\n"
        f"1% du CAHT              : {ca_ht * 0.01:,.0f} FCFA\n"
        f"Plancher légal          : 500 000 FCFA\n"
        f"Plafond légal           : 2 500 000 FCFA\n"
        f"─────────────────────\n"
        f"*IMF à payer            : {imf:,.0f} FCFA*\n\n"
        f"ℹ️ L'IMF est dû même en cas de déficit (Art. 62 CGI)."
    )

def calculer_tva(ca_ht: float, tva_deductible: float) -> str:
    tva_collectee = ca_ht * 0.1925
    tva_nette = tva_collectee - tva_deductible
    statut = "à payer à la DGI" if tva_nette >= 0 else "crédit de TVA (report ou remboursement)"
    return (
        f"📊 *Calcul TVA*\n\n"
        f"CA HT                   : {ca_ht:,.0f} FCFA\n"
        f"TVA collectée (19,25%)  : {tva_collectee:,.0f} FCFA\n"
        f"TVA déductible          : {tva_deductible:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*TVA nette : {abs(tva_nette):,.0f} FCFA ({statut})*"
    )

def calculer_irpp(salaire_brut: float) -> str:
    abattement = min(max(salaire_brut * 0.30, 500_000 / 12), 3_000_000 / 12)
    revenu_net_mensuel = salaire_brut - abattement
    revenu_annuel = revenu_net_mensuel * 12
    tranches = [
        (2_000_000, 0.00),
        (1_000_000, 0.10),
        (2_000_000, 0.15),
        (5_000_000, 0.25),
        (float('inf'), 0.35),
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
        f"📊 *Calcul IRPP mensuel — Salaire {salaire_brut:,.0f} FCFA*\n\n"
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
        f"📊 *Retenue à la source — Honoraires {honoraires:,.0f} FCFA*\n\n"
        f"Montant brut            : {honoraires:,.0f} FCFA\n"
        f"RS (11%)                : {rs:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*Net perçu              : {net_percu:,.0f} FCFA*\n"
        f"*RS à reverser à la DGI : {rs:,.0f} FCFA*\n\n"
        f"ℹ️ Pour un prestataire non-résident : taux 15% (RS = {honoraires*0.15:,.0f} FCFA)"
    )

def calculer_amort(valeur: float, duree: int) -> str:
    taux = 1 / duree
    annuite = valeur * taux
    lignes = [
        f"📊 *Amortissement linéaire — {valeur:,.0f} FCFA sur {duree} ans*\n",
        f"Taux : {taux*100:.1f}% | Annuité : {annuite:,.0f} FCFA\n",
        f"{'Année':<8} {'Amort.':<16} {'Cumulé':<16} {'VNC':}",
        "─" * 50,
    ]
    cumul = 0
    for annee in range(1, duree + 1):
        cumul += annuite
        vnc = valeur - cumul
        lignes.append(f"  {annee:<7} {annuite:<16,.0f} {cumul:<16,.0f} {max(vnc,0):,.0f}")
    return "\n".join(lignes)

def calculer_bfr(stocks: float, creances: float, fournisseurs: float, fiscal_social: float) -> str:
    bfr = stocks + creances - fournisseurs - fiscal_social
    statut = "✅ BFR positif : besoin de financement" if bfr > 0 else "✅ BFR négatif : ressource de financement (favorable)"
    return (
        f"📊 *Calcul du BFR*\n\n"
        f"Stocks                  : +{stocks:,.0f} FCFA\n"
        f"Créances clients        : +{creances:,.0f} FCFA\n"
        f"Dettes fournisseurs     : -{fournisseurs:,.0f} FCFA\n"
        f"Dettes fiscales/sociales: -{fiscal_social:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*BFR = {bfr:,.0f} FCFA*\n"
        f"{statut}"
    )

def traiter_calcul(texte: str) -> str | None:
    t = texte.strip().upper()
    parts = texte.strip().split()
    try:
        cmd = parts[0].upper()
        if cmd == "IS" and len(parts) == 2:
            return calculer_is(float(parts[1].replace(" ", "").replace(",", "")))
        if cmd == "IMF" and len(parts) == 2:
            return calculer_imf(float(parts[1].replace(" ", "").replace(",", "")))
        if cmd == "TVA" and len(parts) == 3:
            return calculer_tva(float(parts[1].replace(",", "")), float(parts[2].replace(",", "")))
        if cmd == "IRPP" and len(parts) == 2:
            return calculer_irpp(float(parts[1].replace(",", "")))
        if cmd == "RS" and len(parts) == 2:
            return calculer_rs(float(parts[1].replace(",", "")))
        if cmd == "AMORT" and len(parts) == 3:
            return calculer_amort(float(parts[1].replace(",", "")), int(parts[2]))
        if cmd == "BFR" and len(parts) == 5:
            return calculer_bfr(float(parts[1].replace(",","")), float(parts[2].replace(",","")),
                                float(parts[3].replace(",","")), float(parts[4].replace(",","")))
    except (ValueError, IndexError):
        pass
    return None

# ─────────────────────────────────────────────
# BANQUE DE QUESTIONS QUIZ
# ─────────────────────────────────────────────
BANQUE_QUESTIONS = [
    # ── FISCALITÉ ──
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐ Débutant",
        "question": "Quel est le taux normal de TVA au Cameroun ?",
        "choix": ["A) 17,5%", "B) 19,25%", "C) 20%", "D) 15%"],
        "reponse": "B",
        "explication": "Le taux normal de TVA est 19,25% = 17,5% + 10% de Centimes Additionnels Communaux (CAC). (Art. 125 CGI)"
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐ Débutant",
        "question": "Quel est le taux de l'Impôt sur les Sociétés (IS) hors CAC au Cameroun ?",
        "choix": ["A) 25%", "B) 28%", "C) 30%", "D) 33%"],
        "reponse": "C",
        "explication": "Le taux IS est 30% (Art. 27 CGI). Avec les CAC de 10%, le taux effectif global est 33%. La réponse D (33%) représente le taux tout compris, mais le taux légal IS seul est 30%."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐ Débutant",
        "question": "À partir de quel chiffre d'affaires une entreprise est-elle assujettie à la TVA au Cameroun ?",
        "choix": ["A) 10 000 000 FCFA", "B) 30 000 000 FCFA", "C) 50 000 000 FCFA", "D) 100 000 000 FCFA"],
        "reponse": "C",
        "explication": "Le seuil d'assujettissement à la TVA est de 50 000 000 FCFA de CAHT (Art. 124 CGI). En dessous, l'entreprise relève du régime de l'impôt libératoire."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐ Débutant",
        "question": "Que signifie CAC en fiscalité camerounaise ?",
        "choix": ["A) Contribution aux Activités Communales", "B) Centimes Additionnels Communaux", "C) Charges Annuelles Comptables", "D) Crédit Annuel Compensatoire"],
        "reponse": "B",
        "explication": "CAC = Centimes Additionnels Communaux. Ce sont des majorations de 10% prélevées sur certains impôts (IS, IRPP, TVA) et reversées aux collectivités territoriales."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐ Débutant",
        "question": "Quel taux de retenue à la source s'applique aux honoraires versés à un consultant résident ?",
        "choix": ["A) 5%", "B) 11%", "C) 15%", "D) 20%"],
        "reponse": "B",
        "explication": "Les honoraires, commissions et courtages versés à des prestataires résidents font l'objet d'une retenue à la source libératoire de 11% (Art. 92 CGI)."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Qu'est-ce que l'IMF (Impôt Minimum Forfaitaire) ?",
        "choix": [
            "A) Un impôt remplaçant la TVA pour les petites entreprises",
            "B) Un impôt minimum de 1% du CAHT dû même en cas de déficit",
            "C) Une taxe sur les importations",
            "D) Un acompte sur l'IRPP"
        ],
        "reponse": "B",
        "explication": "L'IMF est égal à 1% du CAHT, avec un minimum de 500 000 FCFA et un maximum de 2 500 000 FCFA (Art. 62 CGI). Il est dû même lorsque l'entreprise est déficitaire, garantissant une contribution minimale."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Une société a un bénéfice imposable de 5 000 000 FCFA. Quel est son IS total (avec CAC) ?",
        "choix": ["A) 1 500 000 FCFA", "B) 1 650 000 FCFA", "C) 1 750 000 FCFA", "D) 2 000 000 FCFA"],
        "reponse": "B",
        "explication": "IS = 5 000 000 × 30% = 1 500 000 FCFA. CAC = 1 500 000 × 10% = 150 000 FCFA. Total = 1 650 000 FCFA. (Taux effectif global = 33%)"
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Sur quelle base calcule-t-on la TVA collectée ?",
        "choix": [
            "A) Prix TTC de la vente",
            "B) Prix HT de la vente × 19,25%",
            "C) Marge bénéficiaire × 19,25%",
            "D) Chiffre d'affaires annuel × 19,25%"
        ],
        "reponse": "B",
        "explication": "La TVA collectée = Prix HT × 19,25%. Le prix TTC = Prix HT × 1,1925. On applique toujours le taux sur la base hors taxes."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Quel est le taux IRPP effectif (avec CAC) sur la tranche de revenu annuel entre 3 000 001 et 5 000 000 FCFA ?",
        "choix": ["A) 15%", "B) 16,5%", "C) 17,5%", "D) 25%"],
        "reponse": "B",
        "explication": "Le taux IRPP légal sur cette tranche est 15%. Avec les CAC de 10% : 15% × 1,10 = 16,5%. C'est le taux effectif réellement supporté par le contribuable."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐⭐⭐ Avancé",
        "question": "Comment calcule-t-on le résultat fiscal à partir du résultat comptable ?",
        "choix": [
            "A) Résultat fiscal = Résultat comptable uniquement",
            "B) Résultat fiscal = Résultat comptable + Réintégrations – Déductions",
            "C) Résultat fiscal = Résultat comptable – Charges non déductibles",
            "D) Résultat fiscal = Résultat comptable × Taux IS"
        ],
        "reponse": "B",
        "explication": "Résultat fiscal = Résultat comptable + Réintégrations (charges non déductibles : amendes, dépenses somptuaires…) – Déductions (produits exonérés, amortissements différés…). Ce tableau de passage est obligatoire dans la liasse fiscale."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐⭐⭐ Avancé",
        "question": "Quelle est la durée maximale du report déficitaire en IS au Cameroun ?",
        "choix": ["A) 2 ans", "B) 3 ans", "C) 4 ans", "D) Illimité"],
        "reponse": "C",
        "explication": "Le déficit fiscal peut être reporté sur les 4 exercices suivants (Art. 31 CGI). Au-delà, le déficit non absorbé est définitivement perdu."
    },
    {
        "categorie": "🧾 Fiscalité",
        "niveau": "⭐⭐⭐ Avancé",
        "question": "Quel est le taux de la Taxe Spéciale sur les Revenus (TSR) versés à un prestataire étranger ?",
        "choix": ["A) 10%", "B) 11%", "C) 15%", "D) 16,5%"],
        "reponse": "D",
        "explication": "La TSR est de 15% + 10% CAC = 16,5% effectif (Art. 99 CGI). Elle est retenue et reversée par le débiteur camerounais qui paie le prestataire non-résident. Des conventions fiscales peuvent réduire ce taux."
    },
    # ── COMPTABILITÉ ──
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐ Débutant",
        "question": "Dans le plan comptable OHADA, à quelle classe appartient le compte 'Clients' ?",
        "choix": ["A) Classe 3", "B) Classe 4", "C) Classe 5", "D) Classe 6"],
        "reponse": "B",
        "explication": "Le compte Clients (411) appartient à la Classe 4 — Comptes de Tiers (créances et dettes à court terme). La classe 4 regroupe : fournisseurs (40), clients (41), personnel (42), État (44)."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐ Débutant",
        "question": "Quel est le principe fondamental de la comptabilité en partie double ?",
        "choix": [
            "A) Tout enregistrement au débit doit avoir une contrepartie égale au crédit",
            "B) Les charges doivent toujours être supérieures aux produits",
            "C) L'actif doit toujours être supérieur au passif",
            "D) Chaque opération est enregistrée deux fois dans le même compte"
        ],
        "reponse": "A",
        "explication": "La partie double signifie que pour chaque écriture, le total des débits = le total des crédits. Si vous débitez 'Banque' de 100 000 FCFA, vous devez créditer un autre compte de 100 000 FCFA."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐ Débutant",
        "question": "Quelle est la formule de base du bilan ?",
        "choix": [
            "A) Actif = Passif + Résultat",
            "B) Actif = Capitaux propres + Dettes",
            "C) Actif – Dettes = Capitaux propres",
            "D) B et C sont toutes les deux correctes"
        ],
        "reponse": "D",
        "explication": "Les deux formulations sont équivalentes : Actif = Capitaux propres + Dettes (équation du bilan), ce qui implique Actif – Dettes = Capitaux propres. L'actif est toujours égal au passif total."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐ Débutant",
        "question": "Une entreprise achète des marchandises pour 200 000 FCFA en espèces. Quelle est l'écriture correcte ?",
        "choix": [
            "A) Débit Caisse 200 000 / Crédit Marchandises 200 000",
            "B) Débit Marchandises 200 000 / Crédit Caisse 200 000",
            "C) Débit Fournisseurs 200 000 / Crédit Caisse 200 000",
            "D) Débit Caisse 200 000 / Crédit Fournisseurs 200 000"
        ],
        "reponse": "B",
        "explication": "On débite le compte Marchandises (31) car le stock augmente (actif en hausse = débit), et on crédite la Caisse (53) car elle diminue (actif en baisse = crédit)."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐ Débutant",
        "question": "Dans le plan comptable OHADA, quelle classe regroupe les charges ?",
        "choix": ["A) Classe 5", "B) Classe 6", "C) Classe 7", "D) Classe 8"],
        "reponse": "B",
        "explication": "La Classe 6 regroupe toutes les charges : achats (60), transports (61), services extérieurs (62-63), impôts (64), charges de personnel (66), charges financières (67), dotations (68)."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Une entreprise a acheté un véhicule à 8 000 000 FCFA. Durée de vie estimée : 4 ans. Quel est l'amortissement linéaire annuel ?",
        "choix": ["A) 1 600 000 FCFA", "B) 2 000 000 FCFA", "C) 2 400 000 FCFA", "D) 4 000 000 FCFA"],
        "reponse": "B",
        "explication": "Amortissement linéaire = Valeur d'origine / Durée = 8 000 000 / 4 = 2 000 000 FCFA/an. Le taux linéaire est de 25% (1/4). À la fin de l'année 4, la VNC sera zéro."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Quel est le solde intermédiaire de gestion calculé juste après la Valeur Ajoutée ?",
        "choix": [
            "A) Résultat d'exploitation",
            "B) Marge commerciale",
            "C) Excédent Brut d'Exploitation (EBE)",
            "D) Résultat net"
        ],
        "reponse": "C",
        "explication": "L'ordre des SIG est : Marge commerciale → VA → EBE → Résultat d'exploitation → RAO → Résultat HAO → Résultat net. L'EBE = VA + Subventions – Charges personnel – Impôts & taxes."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Une charge est engagée en décembre N mais la facture n'est pas encore reçue. Comment l'enregistre-t-on au 31/12/N ?",
        "choix": [
            "A) On ne l'enregistre pas, on attend la facture",
            "B) Débit Charge / Crédit 408 Fournisseurs-factures non parvenues (Charge à payer)",
            "C) Débit 476 Charges constatées d'avance / Crédit Charge",
            "D) Débit Trésorerie / Crédit Charge"
        ],
        "reponse": "B",
        "explication": "C'est une Charge À Payer (CAP) : la charge est rattachée à l'exercice N même si la facture n'est pas encore arrivée. On débite le compte de charge concerné et on crédite le compte 408 'Fournisseurs – factures non parvenues'."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐ Intermédiaire",
        "question": "Quelle est la formule du Besoin en Fonds de Roulement (BFR) ?",
        "choix": [
            "A) BFR = Capitaux propres – Actif immobilisé",
            "B) BFR = Stocks + Créances – Dettes CT d'exploitation",
            "C) BFR = Trésorerie actif – Trésorerie passif",
            "D) BFR = Actif circulant / Dettes CT"
        ],
        "reponse": "B",
        "explication": "BFR = Stocks + Créances clients – Dettes fournisseurs – Dettes fiscales & sociales. Un BFR positif signifie que l'entreprise doit financer un besoin. Un BFR négatif est une ressource (favorable pour la trésorerie)."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐⭐ Avancé",
        "question": "Une immobilisation est cédée à 3 000 000 FCFA. Sa valeur d'origine était 10 000 000 FCFA et les amortissements cumulés sont de 8 000 000 FCFA. Quel est le résultat de cession ?",
        "choix": [
            "A) Plus-value de 1 000 000 FCFA",
            "B) Moins-value de 7 000 000 FCFA",
            "C) Plus-value de 3 000 000 FCFA",
            "D) Moins-value de 1 000 000 FCFA"
        ],
        "reponse": "A",
        "explication": "VNC = 10 000 000 – 8 000 000 = 2 000 000 FCFA. Prix de cession = 3 000 000 FCFA. Résultat = 3 000 000 – 2 000 000 = +1 000 000 FCFA (plus-value). Cette plus-value est imposable à l'IS."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐⭐ Avancé",
        "question": "Comment interpréter un Fonds de Roulement Net (FRN) négatif ?",
        "choix": [
            "A) C'est toujours un signe positif, l'entreprise est performante",
            "B) Les ressources durables ne couvrent pas les actifs immobilisés : déséquilibre financier",
            "C) L'entreprise a trop de trésorerie",
            "D) Cela signifie que le BFR est nul"
        ],
        "reponse": "B",
        "explication": "FRN = Capitaux permanents (CP + dettes LT) – Actif immobilisé net. Un FRN négatif signifie que des dettes court terme financent des actifs immobilisés : situation précaire car les ressources ne sont pas adaptées aux emplois durables."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐⭐ Avancé",
        "question": "Dans le Tableau des Flux de Trésorerie, à quelle section appartient le remboursement d'un emprunt bancaire ?",
        "choix": [
            "A) Flux d'exploitation",
            "B) Flux d'investissement",
            "C) Flux de financement",
            "D) Variation du BFR"
        ],
        "reponse": "C",
        "explication": "Le remboursement d'un emprunt bancaire est un flux de financement négatif (sortie). La section C 'Flux de financement' comprend : emprunts souscrits (+), remboursements (–), augmentations de capital (+), dividendes versés (–)."
    },
    {
        "categorie": "📊 Comptabilité",
        "niveau": "⭐⭐⭐ Avancé",
        "question": "Quel est le lien entre résultat comptable et résultat fiscal ?",
        "choix": [
            "A) Ils sont toujours identiques",
            "B) Résultat fiscal = Résultat comptable + Réintégrations – Déductions extracomptables",
            "C) Le résultat fiscal est toujours inférieur au résultat comptable",
            "D) Le résultat fiscal s'obtient en soustrayant l'IS du résultat comptable"
        ],
        "reponse": "B",
        "explication": "Le résultat fiscal s'obtient par retraitement extracomptable : on réintègre les charges non déductibles (amendes, excès d'amortissements, provisions non réglementées) et on déduit les produits exonérés. L'IS est alors calculé sur ce résultat fiscal, pas sur le résultat comptable."
    },
]

# ─────────────────────────────────────────────
# ÉTAT DES QUIZ PAR UTILISATEUR
# ─────────────────────────────────────────────
quiz_sessions: dict = {}
scores: dict = {}

def get_score(user_id: str) -> dict:
    if user_id not in scores:
        scores[user_id] = {"correct": 0, "total": 0}
    return scores[user_id]

def nouvelle_question(user_id: str) -> dict:
    question = random.choice(BANQUE_QUESTIONS)
    quiz_sessions[user_id] = question
    return question

def formater_question(q: dict, num_total: int, score_actuel: dict) -> str:
    choix_text = "\n".join(q["choix"])
    return (
        f"{q['categorie']} | {q['niveau']}\n\n"
        f"❓ *{q['question']}*\n\n"
        f"{choix_text}\n\n"
        f"_Répondez par A, B, C ou D_\n"
        f"📊 Score actuel : {score_actuel['correct']}/{score_actuel['total']}"
    )

# ─────────────────────────────────────────────
# PERSISTANCE
# ─────────────────────────────────────────────
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# COMMANDES
# ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prenom = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Bonjour *{prenom}* !\n\n"
        f"Je suis *JKBOT* 🇨🇲 — votre assistant expert en :\n"
        f"🧾 Fiscalité camerounaise (CGI 2026)\n"
        f"📊 Comptabilité OHADA / SYSCOHADA\n"
        f"📑 États financiers (Bilan, CR, TFT)\n"
        f"🧮 Calculs fiscaux automatiques\n\n"
        f"Posez votre question ou utilisez :\n"
        f"• /aide — Menu complet\n"
        f"• /cours — Cours de comptabilité\n"
        f"• /etats — États financiers\n"
        f"• /calculer — Calculatrice fiscale",
        parse_mode="Markdown"
    )

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    historiques[user_id] = []
    sauvegarder_historiques(historiques)
    await update.message.reply_text("🔄 Historique effacé !")

async def cmd_aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(AIDE_TEXT, parse_mode="Markdown")

async def cmd_cours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(COURS_TEXT, parse_mode="Markdown")

async def cmd_etats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ETATS_TEXT, parse_mode="Markdown")

async def cmd_calculer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CALCULER_TEXT, parse_mode="Markdown")

async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    score = get_score(user_id)
    q = nouvelle_question(user_id)
    texte = formater_question(q, len(BANQUE_QUESTIONS), score)
    await update.message.reply_text(texte, parse_mode="Markdown")

async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    s = get_score(user_id)
    total = s["total"]
    correct = s["correct"]
    if total == 0:
        await update.message.reply_text(
            "📊 *Votre score*\n\nVous n'avez pas encore répondu à des questions.\nTapez /quiz pour commencer !",
            parse_mode="Markdown"
        )
        return
    pct = round(correct / total * 100)
    if pct >= 80:
        mention = "🏆 Excellent ! Vous maîtrisez le sujet."
    elif pct >= 60:
        mention = "👍 Bien ! Continuez à réviser."
    elif pct >= 40:
        mention = "📖 Passable. Relisez les cours (/cours)."
    else:
        mention = "💪 Courage ! Consultez /cours et /etats pour progresser."
    await update.message.reply_text(
        f"📊 *Votre score JKBOT*\n\n"
        f"✅ Bonnes réponses : {correct}\n"
        f"❌ Mauvaises réponses : {total - correct}\n"
        f"📝 Total questions : {total}\n"
        f"🎯 Taux de réussite : *{pct}%*\n\n"
        f"{mention}\n\n"
        f"Tapez /quiz pour continuer à vous entraîner !",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
# HANDLER MESSAGES
# ─────────────────────────────────────────────
async def repondre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texte_recu = update.message.text.strip()
    if user_id not in historiques:
        historiques[user_id] = []

    # ── Détection réponse au quiz ──
    if user_id in quiz_sessions and texte_recu.upper() in ("A", "B", "C", "D"):
        q = quiz_sessions[user_id]
        reponse_user = texte_recu.upper()
        bonne_reponse = q["reponse"]
        score = get_score(user_id)
        score["total"] += 1
        if reponse_user == bonne_reponse:
            score["correct"] += 1
            feedback = f"✅ *Bonne réponse !* La réponse était bien *{bonne_reponse}*.\n\n"
        else:
            feedback = f"❌ *Mauvaise réponse.* Vous avez répondu *{reponse_user}*, la bonne réponse était *{bonne_reponse}*.\n\n"
        explication = f"💡 *Explication :*\n{q['explication']}\n\n"
        score_line = f"📊 Score : {score['correct']}/{score['total']} ({round(score['correct']/score['total']*100)}%)\n\n"
        suite = "Tapez /quiz pour une nouvelle question ou /score pour voir votre bilan."
        del quiz_sessions[user_id]
        await update.message.reply_text(feedback + explication + score_line + suite, parse_mode="Markdown")
        return

    # ── Calculs automatiques ──
    resultat_calcul = traiter_calcul(texte_recu)
    if resultat_calcul:
        await update.message.reply_text(resultat_calcul, parse_mode="Markdown")
        return

    # ── Réponse IA ──
    await update.message.reply_chat_action("typing")
    try:
        client = Groq(api_key=CLE_GROQ)
        historiques[user_id].append({"role": "user", "content": texte_recu})

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

    print("🤖 Initialisation de JKBOT (CGI 2026 + SYSCOHADA)...")
    app = Application.builder().token(TOKEN_TELEGRAM).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("aide", cmd_aide))
    app.add_handler(CommandHandler("cours", cmd_cours))
    app.add_handler(CommandHandler("etats", cmd_etats))
    app.add_handler(CommandHandler("calculer", cmd_calculer))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("score", cmd_score))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre))

    print("✅ JKBOT prêt. Connexion à Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
