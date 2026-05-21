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

TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRA")
CLE_GROQ = os.environ.get("CLE_GRO")
ADMIN_CODE = os.environ.get("JKBOT_ADMIN_CODE", "JK2027ADMIN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "kamdemjoseph06/JKBOT")
DB_FILE = "historiques.json"
CGI_UPDATES_FILE = "cgi_updates.json"
RAPPEL_FILE = "rappel_subscribers.json"

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

CALENDRIER_TEXT = """📅 *CALENDRIER FISCAL CAMEROUN 2026*

*JANVIER*
▸ 15/01 — TVA déclaration décembre N-1
▸ 15/01 — RS (retenues à la source) décembre
▸ 15/01 — Reversement IRPP salaires décembre

*FÉVRIER*
▸ 15/02 — TVA déclaration janvier
▸ 15/02 — RS et IRPP salaires janvier

*MARS* ⚠️ _Mois le plus chargé !_
▸ 15/03 — TVA déclaration février
▸ *15/03 — Déclaration DSF (IS/Résultat N-1)* 🔴
▸ *15/03 — 1er acompte IS* 🔴
▸ *15/03 — Déclaration annuelle IRPP*
▸ 31/03 — Paiement Patente & Licence
▸ 31/03 — Taxe foncière

*AVRIL*
▸ 15/04 — TVA déclaration mars

*MAI*
▸ 15/05 — TVA déclaration avril

*JUIN*
▸ 15/06 — TVA déclaration mai
▸ *15/06 — 2ème acompte IS* 🔴

*JUILLET*
▸ 15/07 — TVA déclaration juin

*AOÛT*
▸ 15/08 — TVA déclaration juillet

*SEPTEMBRE*
▸ 15/09 — TVA déclaration août
▸ *15/09 — 3ème acompte IS* 🔴

*OCTOBRE*
▸ 15/10 — TVA déclaration septembre

*NOVEMBRE*
▸ 15/11 — TVA déclaration octobre

*DÉCEMBRE*
▸ 15/12 — TVA déclaration novembre
▸ 31/12 — Clôture exercice fiscal

─────────────────────
🔴 = Échéance critique
⚠️ Pénalité de retard : 1,5%/mois (min 25 000 FCFA)
📞 DGI Cameroun : impots.cm
"""

LF2025_TEXT = """📜 *LOI DE FINANCES 2025 — POINTS CLÉS*

*🔵 IMPÔT SUR LES SOCIÉTÉS (IS)*
▸ Taux IS maintenu à 30% (+10% CAC = 33%)
▸ IMF : plafond relevé à 2 500 000 FCFA
▸ Renforcement des obligations de documentation de prix de transfert pour groupes
▸ Amortissements accélérés maintenus pour équipements industriels neufs

*🟢 TVA*
▸ Taux normal maintenu à 19,25%
▸ Nouvelles exonérations : matériaux de construction locaux (< seuil fixé)
▸ Facturation électronique obligatoire pour les grandes entreprises (CA > 3 Mds)
▸ Remboursement crédit TVA exportateurs : délai réduit à 30 jours

*🟡 IRPP & SALAIRES*
▸ Barème progressif inchangé (5 tranches)
▸ Abattement forfaitaire maintenu à 30%
▸ Nouvelle exonération : primes de scolarité versées par l'employeur (< 100 000/an/enfant)

*🟠 MESURES DOUANIÈRES*
▸ Réduction droits d'entrée sur équipements agricoles
▸ Taxe spéciale sur certains produits importés concurrençant la production locale

*🔴 NOUVELLES OBLIGATIONS*
▸ NIU obligatoire sur toutes les factures (déjà en vigueur, renforcé)
▸ Déclaration des comptes bancaires étrangers pour résidents fiscaux
▸ Obligation de télédéclaration pour entreprises du régime réel
▸ Extension du contrôle fiscal aux plateformes numériques étrangères

*🟣 CNPS*
▸ Taux cotisations inchangés (employeur ~13%, salarié 2,8%)
▸ Plafond mensuel AVID maintenu à 750 000 FCFA

─────────────────────
ℹ️ Consultez impots.cm pour le texte intégral
"""

CREATION_TEXT = """🏢 *GUIDE CRÉATION D'ENTREPRISE AU CAMEROUN*

*📋 ÉTAPE 1 — Choisir sa forme juridique*
┌─ *SA* (Société Anonyme) : capital min 10 000 000 FCFA, ≥ 3 actionnaires
├─ *SARL* (Société à Resp. Limitée) : capital min 1 000 000 FCFA, 1-50 associés ← recommandée
├─ *SAS* (Société par Actions Simplifiée) : flexible, capital libre, OHADA 2014
├─ *SNC* (Société en Nom Collectif) : pas de capital minimum, responsabilité illimitée
└─ *EI* (Entreprise Individuelle) : personne physique, simple, responsabilité illimitée

*📋 ÉTAPE 2 — Enregistrement au Greffe du Tribunal de Commerce*
▸ Dossier : statuts notariés, liste associés, acte de nomination gérant
▸ Délai : 3 à 7 jours ouvrables
▸ Coût : ~50 000 à 150 000 FCFA (droits d'enregistrement 1% capital)

*📋 ÉTAPE 3 — Obtenir le NIU (Numéro d'Identification Unique)*
▸ Auprès de la Direction des Impôts (DGI)
▸ Documents : acte de création, pièce identité dirigeant, bail locaux
▸ Délai : 24 à 72h
▸ GRATUIT

*📋 ÉTAPE 4 — Immatriculation RCCM (Registre Commerce)*
▸ Centre de Formalités de Création d'Entreprises (CFCE)
▸ Coût : ~30 000 FCFA
▸ Délai : 24h (guichet unique)

*📋 ÉTAPE 5 — Affiliation CNPS*
▸ Dès le premier salarié
▸ Documents : NIU, RCCM, contrats de travail
▸ Obtenir numéro employeur CNPS

*📋 ÉTAPE 6 — Ouverture compte bancaire professionnel*
▸ BICEC, Afriland, SCB, UBA, Ecobank...
▸ Présenter : statuts, RCCM, NIU, pièces dirigeants

*📋 ÉTAPE 7 — Obligations post-création*
▸ Tenir une comptabilité dès le 1er jour (SYSCOHADA)
▸ Émettre des factures normalisées avec NIU
▸ Déposer déclaration d'existence à la DGI (30 jours)
▸ Payer la patente avant le 31 mars de l'année suivante
▸ Première déclaration TVA le mois suivant si CA > 50M

*💰 Coût total estimé création SARL :*
▸ Notaire statuts : 150 000 – 300 000 FCFA
▸ Greffe + RCCM  : 50 000 – 100 000 FCFA
▸ Frais divers   : 30 000 – 50 000 FCFA
▸ *TOTAL : ~230 000 – 450 000 FCFA*

─────────────────────
🏢 CFCE Yaoundé : Avenue Monseigneur Vogt
🏢 CFCE Douala  : Bonanjo, face CCIMA
"""

PATENTE_GUIDE_TEXT = """📊 *GUIDE CALCUL DE LA PATENTE*

La patente est due par toute personne physique ou morale exerçant une activité commerciale, industrielle ou libérale (Art. 170 CGI).

*Formule :*
Patente = Droit fixe + Droit proportionnel

*Droit proportionnel :*
= 16,5% × Valeur locative des locaux professionnels

*Exemples de droits fixes par catégorie :*
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commerce général (gros)          : 120 000 FCFA
Commerce détail                  :  30 000 FCFA
Industrie manufacturière         : 150 000 FCFA
Prestataire de services          :  50 000 FCFA
Profession libérale (médecin...)  :  75 000 FCFA
Transporteur (par véhicule)      :  25 000 FCFA
Restaurant / Hôtel               :  60 000 FCFA
━━━━━━━━━━━━━━━━━━━━━━━━━━━

*Exemple complet :*
Commerce de gros, locaux de valeur locative annuelle 2 400 000 FCFA :
▸ Droit fixe         : 120 000 FCFA
▸ Droit proportionnel: 2 400 000 × 16,5% = 396 000 FCFA
▸ *Total patente     : 516 000 FCFA*

*Dates & pénalités :*
▸ Paiement : avant le 31 mars de chaque année
▸ Retard : pénalité 10% + intérêts 1,5%/mois

*Exonérations :*
▸ Agriculteurs exploitants
▸ Artisans (sous conditions de revenu)
▸ Nouvelle entreprise : exonérée la 1ère année d'activité

Posez vos questions pour un calcul personnalisé !
"""

DSF_PROMPT = """Tu es JKBOT en mode *Assistant DSF Intelligent* 🧮.
L'utilisateur va te décrire une opération comptable ou une situation d'entreprise en langage naturel.
Tu dois générer les *écritures comptables SYSCOHADA* correspondantes avec :
1. Le journal concerné (Achats, Ventes, Banque, OD...)
2. Le(s) compte(s) débité(s) avec libellé exact SYSCOHADA
3. Le(s) compte(s) crédité(s) avec libellé exact
4. Les montants calculés si fournis
5. Une explication pédagogique courte
6. Le traitement fiscal si applicable (TVA, RS, IS...)

Format de réponse OBLIGATOIRE :
───────────────────────────
Journal : [nom du journal]
Date    : [date de l'opération]

DÉBIT  | N° | Libellé SYSCOHADA         | Montant
CRÉDIT | N° | Libellé SYSCOHADA         | Montant
...
───────────────────────────
💡 Explication : [explication courte]
🧾 Fiscal : [impact fiscal si applicable]

Si une information manque pour compléter l'écriture, pose une question précise.
Réponds toujours en français avec émojis.
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

def calculer_cnps(salaire_brut: float) -> str:
    plafond_avid = 750_000
    assiette_avid = min(salaire_brut, plafond_avid)
    # Part salariale
    sal_avid = assiette_avid * 0.028
    total_sal = sal_avid
    # Part patronale
    pat_avid = assiette_avid * 0.042
    pat_famille = salaire_brut * 0.07
    pat_at = salaire_brut * 0.0175
    total_pat = pat_avid + pat_famille + pat_at
    net_a_payer = salaire_brut - total_sal
    cout_total = salaire_brut + total_pat
    return (
        f"📊 *Calcul CNPS — Salaire {salaire_brut:,.0f} FCFA*\n\n"
        f"*PART SALARIALE (déduite du salaire)*\n"
        f"AVID 2,8% × {assiette_avid:,.0f} FCFA : {sal_avid:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*Total retenu sur salarié : {total_sal:,.0f} FCFA*\n"
        f"*Net à payer au salarié   : {net_a_payer:,.0f} FCFA*\n\n"
        f"*PART PATRONALE (charge de l'employeur)*\n"
        f"AVID 4,2% × {assiette_avid:,.0f}  : {pat_avid:,.0f} FCFA\n"
        f"Alloc. fam. 7% × {salaire_brut:,.0f} : {pat_famille:,.0f} FCFA\n"
        f"AT/MP 1,75% × {salaire_brut:,.0f}   : {pat_at:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*Total charge patronale   : {total_pat:,.0f} FCFA*\n"
        f"*Coût total employeur     : {cout_total:,.0f} FCFA*\n\n"
        f"ℹ️ Plafond AVID : 750 000 FCFA/mois\n"
        f"📅 Reversement CNPS : avant le 15 du mois suivant"
    )

def calculer_tva_simple(montant_ht: float) -> str:
    tva = montant_ht * 0.1925
    ttc = montant_ht + tva
    return (
        f"📊 *Calcul TVA rapide*\n\n"
        f"Montant HT       : {montant_ht:,.0f} FCFA\n"
        f"TVA 19,25%       : {tva:,.0f} FCFA\n"
        f"─────────────────────\n"
        f"*Montant TTC     : {ttc:,.0f} FCFA*\n\n"
        f"ℹ️ Pour déduire la TVA d'un TTC :\n"
        f"TVA = TTC × 19,25/119,25 = {ttc * 0.1925 / 1.1925:,.0f} FCFA"
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
            return calculer_bfr(float(parts[1].replace(",", "")), float(parts[2].replace(",", "")),
                                float(parts[3].replace(",", "")), float(parts[4].replace(",", "")))
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
# ÉTAT GLOBAL PAR UTILISATEUR
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

# ─────────────────────────────────────────────
# BASE CGI AUTO-ÉVOLUTIVE
# ─────────────────────────────────────────────
def charger_cgi_updates() -> list:
    if os.path.exists(CGI_UPDATES_FILE):
        try:
            with open(CGI_UPDATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erreur chargement CGI updates: {e}")
    return []

def sauvegarder_cgi_updates(data: list):
    try:
        with open(CGI_UPDATES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde CGI updates: {e}")

async def push_fichier_github(chemin_local: str, chemin_repo: str, message_commit: str) -> dict:
    """Pousse un fichier local vers GitHub via l'API REST. Retourne {"ok": True} ou {"ok": False, "erreur": ...}"""
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

def get_system_prompt_dynamique(langue: str = "fr") -> str:
    updates = charger_cgi_updates()
    if not updates:
        base = SYSTEM_PROMPT
    else:
        annees = sorted(set(u["annee"] for u in updates), reverse=True)
        blocs = []
        for annee in annees:
            entrees = [u for u in updates if u["annee"] == annee]
            bloc = f"\n\n╔══════════════════════════════════════════╗\n║  MISES À JOUR CGI {annee}                 ║\n╚══════════════════════════════════════════╝\n"
            for e in entrees:
                bloc += f"\n▸ *{e['titre']}*\n{e['contenu']}\n"
            blocs.append(bloc)
        base = SYSTEM_PROMPT + "\n\n" + "\n".join(blocs)
    if langue == "en":
        base += "\nPlease respond in English."
    return base

# ─────────────────────────────────────────────
# SYSTÈME DE RAPPELS MENSUELS
# ─────────────────────────────────────────────
def charger_rappel_subscribers() -> set:
    if os.path.exists(RAPPEL_FILE):
        try:
            with open(RAPPEL_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"⚠️ Erreur chargement rappels: {e}")
    return set()

def sauvegarder_rappel_subscribers(data: set):
    try:
        with open(RAPPEL_FILE, "w", encoding="utf-8") as f:
            json.dump(list(data), f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde rappels: {e}")

rappel_subscribers: set = charger_rappel_subscribers()

ECHEANCES_PAR_MOIS = {
    1:  ["📌 15 jan — Déclaration et paiement TVA (décembre)",
         "📌 15 jan — Acompte IS (si applicable)",
         "📌 31 jan — Déclaration annuelle DSF (si clôture au 31/12)",
         "📌 31 jan — Déclaration IRPP salariés (année précédente)"],
    2:  ["📌 15 fév — TVA (janvier)",
         "📌 28 fév — Patente et droits de licence (si non payés en jan)"],
    3:  ["📌 15 mar — TVA (février)",
         "📌 31 mar — Liasse fiscale complète + DSF définitive",
         "📌 31 mar — Déclaration IS définitive (si clôture 31/12)"],
    4:  ["📌 15 avr — TVA (mars)",
         "📌 30 avr — Acompte IS 1er trimestre (25% de l'IS N-1)"],
    5:  ["📌 15 mai — TVA (avril)",
         "📌 31 mai — Déclaration CNPS 1er trimestre"],
    6:  ["📌 15 jun — TVA (mai)",
         "📌 30 jun — Acompte IS 2ème trimestre"],
    7:  ["📌 15 jul — TVA (juin)",
         "📌 31 jul — Déclaration CNPS 2ème trimestre"],
    8:  ["📌 15 aoû — TVA (juillet)"],
    9:  ["📌 15 sep — TVA (août)",
         "📌 30 sep — Acompte IS 3ème trimestre"],
    10: ["📌 15 oct — TVA (septembre)",
         "📌 31 oct — Déclaration CNPS 3ème trimestre"],
    11: ["📌 15 nov — TVA (octobre)"],
    12: ["📌 15 déc — TVA (novembre)",
         "📌 31 déc — Inventaire obligatoire (clôture exercice)",
         "📌 31 déc — Acompte IS 4ème trimestre"],
}

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

def get_rappel_mensuel(mois: int, annee: int) -> str:
    echeances = ECHEANCES_PAR_MOIS.get(mois, [])
    mois_nom = MOIS_FR[mois]
    texte = (
        f"📅 *RAPPEL FISCAL — {mois_nom} {annee}*\n"
        f"_Échéances à ne pas manquer :_\n\n"
    )
    if echeances:
        texte += "\n".join(echeances)
    else:
        texte += "Aucune échéance majeure ce mois-ci."
    texte += (
        "\n\n💡 Utilisez /calendrier pour le calendrier complet\n"
        "ou /tva, /is, /irpp pour calculer vos impôts."
    )
    return texte

async def job_rappel_mensuel(context) -> None:
    maintenant = datetime.now()
    if maintenant.day != 1:
        return
    mois = maintenant.month
    annee = maintenant.year
    message = get_rappel_mensuel(mois, annee)
    subs = charger_rappel_subscribers()
    envoyes = 0
    echecs = 0
    for chat_id in list(subs):
        try:
            await context.bot.send_message(chat_id=int(chat_id), text=message, parse_mode="Markdown")
            envoyes += 1
        except Exception as e:
            print(f"⚠️ Rappel non envoyé à {chat_id}: {e}")
            echecs += 1
    print(f"📅 Rappels envoyés: {envoyes} OK, {echecs} échecs")

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
        f"🧾 Fiscalité CGI 2026 • 📊 Comptabilité OHADA\n"
        f"🧮 Calculs automatiques • 📅 Calendrier fiscal\n"
        f"🏢 Création entreprise • 📄 Générateur de documents\n"
        f"🤖 Écritures SYSCOHADA intelligentes (DSF)\n\n"
        f"*Commandes rapides :*\n"
        f"• /tva 500000 • /is 2000000 • /irpp 350000 • /cnps 400000\n\n"
        f"*Navigation :*\n"
        f"• /aide — Menu complet\n"
        f"• /dsf — Assistant écritures SYSCOHADA\n"
        f"• /calendrier — Échéances fiscales\n"
        f"• /quiz — S'entraîner\n"
        f"• /lang — 🇫🇷/🇬🇧 Changer la langue",
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

# ── Commandes rapides avec argument inline ──
async def cmd_tva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            montant = float(context.args[0].replace(",", ""))
            await update.message.reply_text(calculer_tva_simple(montant), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/tva 500000`\nExemple : `/tva 1200000`", parse_mode="Markdown")

async def cmd_is(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            montant = float(context.args[0].replace(",", ""))
            await update.message.reply_text(calculer_is(montant), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/is 5000000`\nExemple : `/is 12000000`", parse_mode="Markdown")

async def cmd_irpp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            montant = float(context.args[0].replace(",", ""))
            await update.message.reply_text(calculer_irpp(montant), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/irpp 350000`\nExemple : `/irpp 600000`", parse_mode="Markdown")

async def cmd_cnps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            montant = float(context.args[0].replace(",", ""))
            await update.message.reply_text(calculer_cnps(montant), parse_mode="Markdown")
            return
        except ValueError:
            pass
    await update.message.reply_text("Usage : `/cnps 350000`\nExemple : `/cnps 500000`", parse_mode="Markdown")

async def cmd_patente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PATENTE_GUIDE_TEXT, parse_mode="Markdown")

async def cmd_calendrier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CALENDRIER_TEXT, parse_mode="Markdown")

async def cmd_lf2025(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(LF2025_TEXT, parse_mode="Markdown")

async def cmd_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CREATION_TEXT, parse_mode="Markdown")

# ── Générateur de documents (IA) ──
async def cmd_facture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_chat_action("typing")
    prompt = (
        "Génère un modèle de facture camerounaise complète et conforme (TVA 19,25%, NIU obligatoire). "
        "Inclus : numéro de facture, date, émetteur (nom, adresse, NIU, RCCM), client, désignation, "
        "quantité, prix unitaire HT, total HT, TVA 19,25%, total TTC. "
        "Formate-le clairement avec des séparateurs. Ajoute une mention légale en bas."
    )
    try:
        client = Groq(api_key=CLE_GROQ)
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": prompt}],
            max_tokens=1200, temperature=0.3
        )
        await update.message.reply_text(r.choices[0].message.content)
    except Exception as e:
        print(f"❌ Erreur facture: {e}")
        await update.message.reply_text("❌ Erreur technique. Réessayez.")

async def cmd_fiche_paie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_chat_action("typing")
    prompt = (
        "Génère un modèle de fiche de paie camerounaise simplifiée et conforme au droit social OHADA. "
        "Inclus : en-tête employeur (raison sociale, NIU, CNPS numéro), en-tête salarié (nom, poste, date d'embauche), "
        "éléments du salaire brut (salaire de base, primes, heures supplémentaires), "
        "déductions salariales (CNPS 2,8%, IRPP calculé sur barème progressif), "
        "charges patronales (CNPS patronal ~13%), net à payer, mention de bulletin. "
        "Utilise un exemple avec salaire de base de 400 000 FCFA. Formate proprement avec des colonnes."
    )
    try:
        client = Groq(api_key=CLE_GROQ)
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": prompt}],
            max_tokens=1200, temperature=0.3
        )
        await update.message.reply_text(r.choices[0].message.content)
    except Exception as e:
        print(f"❌ Erreur fiche_paie: {e}")
        await update.message.reply_text("❌ Erreur technique. Réessayez.")

# ── Assistant DSF Intelligent ──
async def cmd_dsf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    dsf_sessions.add(user_id)
    await update.message.reply_text(
        "🧮 *Mode DSF activé — Assistant Écritures SYSCOHADA*\n\n"
        "Décrivez votre opération en langage naturel, je génère les écritures comptables.\n\n"
        "*Exemples :*\n"
        "▸ \"Achat de marchandises 500 000 FCFA TTC à crédit\"\n"
        "▸ \"Vente de produits 1 200 000 FCFA TTC, payée par virement\"\n"
        "▸ \"Règlement d'un emprunt : échéance 150 000 dont 40 000 d'intérêts\"\n"
        "▸ \"Dotation amortissement matériel 8 000 000 FCFA sur 4 ans, 2ème année\"\n"
        "▸ \"Paiement salaires : brut 600 000, CNPS salarié, IRPP\"\n\n"
        "Tapez /stop pour quitter ce mode.",
        parse_mode="Markdown"
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    dsf_sessions.discard(user_id)
    await update.message.reply_text("✅ Mode DSF désactivé. Retour au mode normal.")

# ── Langue ──
async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    current = lang_prefs.get(user_id, "fr")
    if current == "fr":
        lang_prefs[user_id] = "en"
        await update.message.reply_text(
            "🇬🇧 *Language switched to English!*\n\n"
            "JKBOT will now respond in English.\n"
            "Type /lang again to switch back to French 🇫🇷",
            parse_mode="Markdown"
        )
    else:
        lang_prefs[user_id] = "fr"
        await update.message.reply_text(
            "🇫🇷 *Langue réglée sur le français !*\n\n"
            "JKBOT répondra maintenant en français.\n"
            "Tapez /lang pour repasser en anglais 🇬🇧",
            parse_mode="Markdown"
        )

# ── Quiz par catégorie ──
async def cmd_quiz_fiscal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    fiscales = [q for q in BANQUE_QUESTIONS if "Fiscalité" in q["categorie"]]
    score = get_score(user_id)
    q = random.choice(fiscales)
    quiz_sessions[user_id] = q
    await update.message.reply_text(formater_question(q, len(fiscales), score), parse_mode="Markdown")

async def cmd_quiz_compta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    compta = [q for q in BANQUE_QUESTIONS if "Comptabilité" in q["categorie"]]
    score = get_score(user_id)
    q = random.choice(compta)
    quiz_sessions[user_id] = q
    await update.message.reply_text(formater_question(q, len(compta), score), parse_mode="Markdown")

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

    # ── Mode DSF : écritures SYSCOHADA ──
    if user_id in dsf_sessions:
        await update.message.reply_chat_action("typing")
        try:
            client = Groq(api_key=CLE_GROQ)
            reponse = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
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

    # ── Réponse IA (normale) ──
    await update.message.reply_chat_action("typing")
    try:
        client = Groq(api_key=CLE_GROQ)
        historiques[user_id].append({"role": "user", "content": texte_recu})
        langue = lang_prefs.get(user_id, "fr")
        system = get_system_prompt_dynamique(langue)

        reponse = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system}] + historiques[user_id],
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
# NOUVEAUX HANDLERS : RAPPELS, CGI ÉVOLUTIF
# ─────────────────────────────────────────────
async def cmd_rappel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in rappel_subscribers:
        rappel_subscribers.discard(user_id)
        sauvegarder_rappel_subscribers(rappel_subscribers)
        await update.message.reply_text(
            "🔕 *Rappels désactivés.*\n\n"
            "Vous ne recevrez plus de notifications mensuelles.\n"
            "Tapez /rappel pour les réactiver.",
            parse_mode="Markdown"
        )
    else:
        rappel_subscribers.add(user_id)
        sauvegarder_rappel_subscribers(rappel_subscribers)
        maintenant = datetime.now()
        apercu = get_rappel_mensuel(maintenant.month, maintenant.year)
        await update.message.reply_text(
            "🔔 *Rappels mensuels activés !*\n\n"
            "Vous recevrez automatiquement le 1er de chaque mois "
            "les échéances fiscales du mois.\n\n"
            f"*Aperçu du mois en cours :*\n\n{apercu}\n\n"
            "_Tapez /rappel à nouveau pour désactiver._",
            parse_mode="Markdown"
        )

async def cmd_nouveautes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    updates = charger_cgi_updates()
    if not updates:
        await update.message.reply_text(
            "📋 Aucune mise à jour enregistrée pour l'instant.\n"
            "Les nouvelles dispositions du CGI seront ajoutées ici."
        )
        return
    tri = sorted(updates, key=lambda x: (x["annee"], x["id"]), reverse=True)
    annees_affichees = set()
    texte = "📢 *Nouveautés fiscales & comptables*\n\n"
    for u in tri:
        if u["annee"] not in annees_affichees:
            texte += f"━━━━ *{u['annee']}* ━━━━\n"
            annees_affichees.add(u["annee"])
        texte += f"▸ *{u['titre']}*\n_{u['contenu'][:200]}{'...' if len(u['contenu'])>200 else ''}_\n\n"
    texte += "💬 Posez vos questions sur ces nouveautés directement !"
    if len(texte) > 4096:
        for i in range(0, len(texte), 4096):
            await update.message.reply_text(texte[i:i+4096], parse_mode="Markdown")
    else:
        await update.message.reply_text(texte, parse_mode="Markdown")

async def cmd_lf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        annee_actuelle = datetime.now().year
        await update.message.reply_text(
            f"Usage : `/lf {annee_actuelle}` ou `/lf {annee_actuelle+1}`\n"
            "Affiche les dispositions de la Loi de Finances enregistrées pour une année.",
            parse_mode="Markdown"
        )
        return
    try:
        annee = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Année invalide. Ex : `/lf 2027`", parse_mode="Markdown")
        return
    if annee == 2025:
        await update.message.reply_text(LF2025_TEXT, parse_mode="Markdown")
        return
    updates = charger_cgi_updates()
    entrees = [u for u in updates if u["annee"] == annee]
    if not entrees:
        await update.message.reply_text(
            f"📋 Aucune disposition enregistrée pour {annee}.\n\n"
            f"Dès que la Loi de Finances {annee} sera publiée, "
            "l'administrateur pourra les ajouter avec `/maj_cgi`.",
            parse_mode="Markdown"
        )
        return
    texte = f"📜 *Loi de Finances {annee} — Dispositions enregistrées*\n\n"
    for e in entrees:
        texte += f"▸ *{e['titre']}*\n{e['contenu']}\n\n"
    if len(texte) > 4096:
        for i in range(0, len(texte), 4096):
            await update.message.reply_text(texte[i:i+4096], parse_mode="Markdown")
    else:
        await update.message.reply_text(texte, parse_mode="Markdown")

async def cmd_maj_cgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage : /maj_cgi CODE_ADMIN ANNEE TITRE | CONTENU
    Exemple : /maj_cgi JK2027ADMIN 2027 Nouveau taux IS | Le taux d'IS passe à 28% pour les grandes entreprises.
    """
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "⚙️ *Commande admin — Mise à jour CGI*\n\n"
            "Usage : `/maj_cgi CODE ANNEE TITRE | CONTENU`\n\n"
            "Exemple :\n"
            "`/maj_cgi JK2027ADMIN 2027 Nouveau taux IS | Le taux passe à 28%.`\n\n"
            "_Réservé à l'administrateur._",
            parse_mode="Markdown"
        )
        return
    code_saisi = context.args[0]
    if code_saisi != ADMIN_CODE:
        await update.message.reply_text("🔒 Code administrateur invalide.")
        return
    try:
        annee = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Année invalide.")
        return
    reste = " ".join(context.args[2:])
    if "|" not in reste:
        await update.message.reply_text("❌ Séparez le TITRE et le CONTENU avec `|`.", parse_mode="Markdown")
        return
    titre, contenu = reste.split("|", 1)
    titre = titre.strip()
    contenu = contenu.strip()
    if not titre or not contenu:
        await update.message.reply_text("❌ Titre ou contenu vide.")
        return
    updates = charger_cgi_updates()
    nouvel_id = max((u["id"] for u in updates), default=0) + 1
    auteur = update.effective_user.username or update.effective_user.first_name or "admin"
    nouvelle_entree = {
        "id": nouvel_id,
        "annee": annee,
        "titre": titre,
        "contenu": contenu,
        "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "auteur": auteur
    }
    updates.append(nouvelle_entree)
    sauvegarder_cgi_updates(updates)

    # Confirmation immédiate
    await update.message.reply_text(
        f"✅ *Mise à jour CGI {annee} enregistrée !*\n\n"
        f"📌 *Titre :* {titre}\n"
        f"📝 *Contenu :* {contenu[:300]}{'...' if len(contenu)>300 else ''}\n\n"
        f"Le bot intègre automatiquement cette disposition dans ses réponses.\n"
        f"🔄 Synchronisation GitHub en cours...",
        parse_mode="Markdown"
    )

    # Push automatique vers GitHub
    message_commit = f"CGI {annee} : {titre} [{datetime.now().strftime('%Y-%m-%d')}]"
    resultat = await push_fichier_github(
        chemin_local=CGI_UPDATES_FILE,
        chemin_repo="telegram-bot/cgi_updates.json",
        message_commit=message_commit
    )
    if resultat["ok"]:
        await update.message.reply_text(
            f"🐙 *GitHub synchronisé !*\n"
            f"[Voir cgi\\_updates.json sur GitHub]({resultat['url']})\n\n"
            f"Tapez /nouveautes pour voir toutes les mises à jour.",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            f"⚠️ Sauvegarde locale OK, mais GitHub non synchronisé : `{resultat['erreur']}`\n"
            f"Tapez /nouveautes pour voir les mises à jour.",
            parse_mode="Markdown"
        )

async def cmd_historique_cgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    updates = charger_cgi_updates()
    if not updates:
        await update.message.reply_text(
            "📋 Aucune mise à jour enregistrée.\n"
            "Utilisez `/maj_cgi` pour ajouter les nouvelles dispositions fiscales.",
            parse_mode="Markdown"
        )
        return

    tries = sorted(updates, key=lambda x: (x["annee"], x.get("date_ajout", "")), reverse=True)
    annees = sorted(set(u["annee"] for u in tries), reverse=True)

    texte = "📜 *Journal des mises à jour CGI — JKBOT*\n"
    texte += f"_Total : {len(updates)} disposition(s) enregistrée(s)_\n\n"

    for annee in annees:
        entrees = [u for u in tries if u["annee"] == annee]
        texte += f"┌─── *{annee}* ── {len(entrees)} disposition(s)\n"
        for i, e in enumerate(entrees):
            prefixe = "├" if i < len(entrees) - 1 else "└"
            date = e.get("date_ajout", "—")
            auteur = e.get("auteur", "admin")
            texte += (
                f"{prefixe}─ *#{e['id']}* {e['titre']}\n"
                f"   📅 {date}  •  ✍️ @{auteur}\n"
                f"   _{e['contenu'][:120]}{'…' if len(e['contenu']) > 120 else ''}_\n"
            )
        texte += "\n"

    texte += (
        "─────────────────────────\n"
        "➕ Ajouter : `/maj_cgi CODE ANNEE TITRE | CONTENU`\n"
        "🔎 Consulter : `/lf ANNEE`\n"
        "📢 Voir résumé : `/nouveautes`"
    )

    if len(texte) > 4096:
        for i in range(0, len(texte), 4096):
            await update.message.reply_text(texte[i:i+4096], parse_mode="Markdown")
    else:
        await update.message.reply_text(texte, parse_mode="Markdown")

async def cmd_supprimer_cgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage : /supprimer_cgi CODE_ADMIN ID
    Exemple : /supprimer_cgi JK2027ADMIN 3
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚙️ *Suppression d'une disposition CGI*\n\n"
            "Usage : `/supprimer_cgi CODE ID`\n\n"
            "Exemple : `/supprimer_cgi JK2027ADMIN 3`\n\n"
            "_Consultez `/historique_cgi` pour voir les IDs disponibles._",
            parse_mode="Markdown"
        )
        return

    code_saisi = context.args[0]
    if code_saisi != ADMIN_CODE:
        await update.message.reply_text("🔒 Code administrateur invalide.")
        return

    try:
        cible_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ ID invalide. Ex : `/supprimer_cgi JK2027ADMIN 3`", parse_mode="Markdown")
        return

    updates = charger_cgi_updates()
    entree = next((u for u in updates if u["id"] == cible_id), None)

    if not entree:
        ids_dispo = ", ".join(str(u["id"]) for u in updates) or "aucun"
        await update.message.reply_text(
            f"❌ Aucune disposition avec l'ID *#{cible_id}*.\n\n"
            f"IDs disponibles : `{ids_dispo}`\n"
            f"Tapez /historique\\_cgi pour consulter le journal.",
            parse_mode="Markdown"
        )
        return

    # Suppression
    updates_restants = [u for u in updates if u["id"] != cible_id]
    sauvegarder_cgi_updates(updates_restants)

    # Confirmation + push GitHub
    await update.message.reply_text(
        f"🗑️ *Disposition #{cible_id} supprimée*\n\n"
        f"📌 *Titre :* {entree['titre']}\n"
        f"📅 *Ajoutée le :* {entree.get('date_ajout', '—')}\n"
        f"✍️ *Par :* @{entree.get('auteur', 'admin')}\n\n"
        f"🔄 Synchronisation GitHub en cours...",
        parse_mode="Markdown"
    )

    message_commit = (
        f"CGI : suppression #{cible_id} '{entree['titre']}' "
        f"({entree['annee']}) [{datetime.now().strftime('%Y-%m-%d')}]"
    )
    resultat = await push_fichier_github(
        chemin_local=CGI_UPDATES_FILE,
        chemin_repo="telegram-bot/cgi_updates.json",
        message_commit=message_commit
    )

    if resultat["ok"]:
        restants = len(updates_restants)
        await update.message.reply_text(
            f"🐙 *GitHub synchronisé !*\n"
            f"[Voir le commit]({resultat['url']})\n\n"
            f"_Il reste {restants} disposition(s) dans la base._\n"
            f"Tapez /historique\\_cgi pour vérifier.",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            f"⚠️ Suppression locale OK, GitHub non synchronisé : `{resultat['erreur']}`",
            parse_mode="Markdown"
        )

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    historiques[user_id] = []
    dsf_sessions.discard(user_id)
    sauvegarder_historiques(historiques)
    await update.message.reply_text("🔄 Historique effacé et mode DSF réinitialisé !")

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
    # Calculs rapides
    app.add_handler(CommandHandler("tva", cmd_tva))
    app.add_handler(CommandHandler("is", cmd_is))
    app.add_handler(CommandHandler("irpp", cmd_irpp))
    app.add_handler(CommandHandler("cnps", cmd_cnps))
    app.add_handler(CommandHandler("patente", cmd_patente))
    # Référence fiscale
    app.add_handler(CommandHandler("calendrier", cmd_calendrier))
    app.add_handler(CommandHandler("lf2025", cmd_lf2025))
    app.add_handler(CommandHandler("creation", cmd_creation))
    # Générateur documents
    app.add_handler(CommandHandler("facture", cmd_facture))
    app.add_handler(CommandHandler("fiche_paie", cmd_fiche_paie))
    # DSF & langue
    app.add_handler(CommandHandler("dsf", cmd_dsf))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("lang", cmd_lang))
    # Quiz
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("quiz_fiscal", cmd_quiz_fiscal))
    app.add_handler(CommandHandler("quiz_compta", cmd_quiz_compta))
    app.add_handler(CommandHandler("score", cmd_score))
    # Rappels & CGI évolutif
    app.add_handler(CommandHandler("rappel", cmd_rappel))
    app.add_handler(CommandHandler("nouveautes", cmd_nouveautes))
    app.add_handler(CommandHandler("lf", cmd_lf))
    app.add_handler(CommandHandler("maj_cgi", cmd_maj_cgi))
    app.add_handler(CommandHandler("historique_cgi", cmd_historique_cgi))
    app.add_handler(CommandHandler("supprimer_cgi", cmd_supprimer_cgi))
    # Messages libres
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre))

    # ── Job queue : rappels mensuels (vérifie chaque jour à 7h00) ──
    job_queue = app.job_queue
    if job_queue:
        import pytz
        tz_cm = pytz.timezone("Africa/Douala")
        from datetime import time as dt_time
        job_queue.run_daily(
            job_rappel_mensuel,
            time=dt_time(hour=7, minute=0, tzinfo=tz_cm),
            name="rappel_mensuel"
        )
        print("📅 Job rappels mensuels programmé à 07h00 (heure Douala)")
    else:
        print("⚠️ JobQueue non disponible — rappels désactivés")

    print("✅ JKBOT prêt. Connexion à Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
