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

# ─────────────────────────────────────────────
# HANDLER MESSAGES
# ─────────────────────────────────────────────
async def repondre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    question = update.message.text
    if user_id not in historiques:
        historiques[user_id] = []

    resultat_calcul = traiter_calcul(question)
    if resultat_calcul:
        await update.message.reply_text(resultat_calcul, parse_mode="Markdown")
        return

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre))

    print("✅ JKBOT prêt. Connexion à Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
