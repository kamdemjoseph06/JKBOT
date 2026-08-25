# JKBOT — Assistant Telegram WADA, finance et fiscalité

JKBOT est un assistant Telegram francophone conçu pour expliquer la **fiscalité camerounaise**, la **comptabilité OHADA/SYSCOHADA**, les calculs financiers courants et les sujets de **sport propre liés à la WADA**. Il peut répondre en langage naturel, conserver un historique court par utilisateur, analyser des documents, transcrire des messages vocaux et produire des modèles pédagogiques.

> **Important.** JKBOT fournit une information générale et des exemples. Il ne remplace ni un expert-comptable, ni un fiscaliste, ni un avocat, ni un médecin, ni une organisation antidopage. Les taux, échéances, règles fiscales et règles antidopage doivent être vérifiés dans les textes officiels applicables à la date de la décision.

## Fonctionnalités actuellement disponibles

| Domaine | Fonctionnalités |
| --- | --- |
| **Fiscalité camerounaise** | Explications sur l’IS, l’IMF, la TVA, l’IRPP, les retenues à la source, la patente, la taxe foncière, les droits d’enregistrement, les obligations déclaratives et les pénalités. |
| **Comptabilité OHADA/SYSCOHADA** | Partie double, plan comptable, écritures courantes, amortissements, provisions, régularisations, états financiers, SIG, BFR et ratios. |
| **Finance d’entreprise** | Analyse de liquidité, rentabilité, endettement, trésorerie, BFR, FRN, seuil de rentabilité et lecture pédagogique d’un bilan. |
| **WADA / sport propre** | Présentation du Code mondial antidopage, de la Liste des interdictions, des AUT/TUE, du contrôle antidopage, de l’éducation, de la protection des données et de la conformité. |
| **Documents et médias** | Analyse de PDF avec texte sélectionnable, lecture de factures ou reçus en image et transcription de vocaux Telegram en français. |
| **Formation** | Mode DSF, cours progressifs, quiz fiscalité/comptabilité et suivi du score. |
| **Veille** | Enrichissement contextuel à partir de `cgi_updates.json`, recherche ciblée sur les sites fiscaux configurés et recherche WADA lorsque la question le nécessite. |

## Commandes Telegram

### Navigation et assistance

| Commande | Fonction |
| --- | --- |
| `/start` | Présente JKBOT et ses domaines. |
| `/aide` | Affiche le menu complet. |
| `/wada` | Affiche les ressources et thèmes WADA couverts. |
| `/cours` | Liste les cours et exemples de questions. |
| `/etats` | Rappelle la structure du bilan, du compte de résultat et du TFT. |
| `/lang` | Bascule entre le français et l’anglais. |
| `/reset` | Efface l’historique de l’utilisateur et désactive le mode DSF. |

### Calculs et finance

| Commande | Exemple | Résultat |
| --- | --- | --- |
| `/tva` | `/tva 500000` | TVA et montant TTC à partir d’un montant HT. |
| `/is` | `/is 5000000` | IS, CAC et total indicatif. |
| `/irpp` | `/irpp 350000` | Estimation pédagogique de l’IRPP mensuel. |
| `/cnps` | `/cnps 400000` | Parts salariale et patronale CNPS selon les paramètres du bot. |
| `/calculer` | — | Guide des formats de calcul acceptés. |
| Message texte | `BFR 3000000 2000000 1500000 500000` | Calcul du besoin en fonds de roulement. |

Les formats directs supplémentaires sont `IS montant`, `IMF chiffre_affaires`, `TVA montant_ht`, `TVA montant_ht tva_deductible`, `IRPP salaire_brut`, `CNPS salaire_brut`, `RS honoraires`, `AMORT valeur durée` et `BFR stocks créances fournisseurs dettes_fiscales_sociales`.

### Comptabilité, documents et formation

| Commande ou action | Fonction |
| --- | --- |
| `/dsf` puis une opération | Génère une écriture SYSCOHADA avec journal, comptes débités/crédités, explication et impact fiscal. |
| `/stop` | Quitte le mode DSF. |
| `/facture` | Génère un modèle pédagogique de facture camerounaise. |
| `/fiche_paie` | Génère un modèle pédagogique de fiche de paie. |
| `/quiz`, `/quiz_fiscal`, `/quiz_compta` | Lance un quiz. |
| `/score` | Affiche le score de formation. |
| PDF envoyé au bot | Extrait le texte puis propose une analyse. |
| Image envoyée au bot | Analyse une facture, un reçu ou un document lisible. |
| Vocal envoyé au bot | Transcrit le vocal puis répond à la question. |

### Calendrier et mises à jour

| Commande | Fonction |
| --- | --- |
| `/calendrier` | Affiche le calendrier fiscal configuré. |
| `/rappel` | Active ou désactive le rappel mensuel à 07:00, heure de Douala. |
| `/nouveautes` | Liste les mises à jour locales enregistrées. |
| `/lf ANNEE` | Recherche les dispositions enregistrées pour une année. |
| `/maj_cgi CODE ANNEE TITRE \| CONTENU` | Ajoute une disposition, uniquement si `JKBOT_ADMIN_CODE` est configuré. |
| `/historique_cgi` | Affiche le journal des mises à jour. |
| `/supprimer_cgi CODE ID` | Supprime une disposition protégée par le code d’administration. |

## Installation locale

### Prérequis

Il faut Python **3.11 ou supérieur**, un bot Telegram créé via [BotFather](https://t.me/BotFather), ainsi qu’une clé API [Groq](https://console.groq.com/). Aucun binaire `ffmpeg` n’est nécessaire pour les vocaux : JKBOT transmet directement le format OGG accepté par l’API de transcription.

### Installation

```bash
git clone https://github.com/kamdemjoseph06/JKBOT.git
cd JKBOT
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r telegram-bot/requirements.txt
```

Le fichier `pyproject.toml` contient également les dépendances nécessaires aux environnements qui installent le projet avec `uv` ou un gestionnaire PEP 621.

### Variables d’environnement

Les noms recommandés sont `TELEGRAM_BOT_TOKEN` et `GROQ_API_KEY`. Les anciens noms `TOKEN_TELEGRAM`, `TOKEN_TELEGRA`, `CLE_GROQ` et `CLE_GRO` restent acceptés pour ne pas casser les déploiements existants.

```bash
export TELEGRAM_BOT_TOKEN="votre_token_telegram"
export GROQ_API_KEY="votre_cle_groq"

# Recommandé en production pour activer les mises à jour CGI protégées
export JKBOT_ADMIN_CODE="un_code_long_et_aleatoire"

# Facultatif : synchronisation GitHub après /maj_cgi
export GITHUB_TOKEN="votre_token_avec_le_droit_necessaire"
export GITHUB_REPO="kamdemjoseph06/JKBOT"

# Facultatif : remplacement des modèles sans modifier le code
export JKBOT_MODEL="openai/gpt-oss-120b"
export JKBOT_VISION_MODEL="qwen/qwen3.6-27b"
export JKBOT_TRANSCRIPTION_MODEL="whisper-large-v3-turbo"
```

### Démarrage

Le point d’entrée de production est `telegram-bot/bot.py` :

```bash
cd telegram-bot
python bot.py
```

`telegram-bot/chatbot.py` est conservé comme **wrapper de compatibilité** et redirige vers la même implémentation. Cela évite que deux versions concurrentes du bot utilisent des clés, des modèles ou des comportements différents.

Sur Replit, le workflow `JKBOT Telegram` exécute déjà `cd telegram-bot && python bot.py`. Vérifiez seulement que les secrets sont configurés dans l’environnement du projet.

## Architecture technique

| Composant | Choix |
| --- | --- |
| Framework Telegram | `python-telegram-bot` 22.x, API asynchrone |
| Modèle texte par défaut | `openai/gpt-oss-120b` via Groq |
| Modèle vision par défaut | `qwen/qwen3.6-27b` via Groq |
| Transcription | `whisper-large-v3-turbo` via Groq |
| Persistance | Fichiers JSON locaux dans `telegram-bot/` |
| Planification | JobQueue/APScheduler intégré à python-telegram-bot |
| Documents | PyMuPDF pour l’extraction PDF |
| Veille | `requests` et BeautifulSoup avec délais d’expiration |

Le flux d’un message est le suivant :

```text
Message Telegram
      │
      ├── Commande ──→ handler spécialisé
      │
      ├── Quiz ──────→ correction et score
      │
      ├── Calcul ────→ résultat déterministe
      │
      ├── Mode DSF ──→ écriture comptable guidée
      │
      ├── PDF/image/vocal ──→ extraction ou transcription puis IA
      │
      └── Question libre ──→ contexte CGI/WADA + historique + réponse IA
```

Les appels synchrones au SDK Groq et les recherches Web sont exécutés dans des threads dédiés afin de ne pas bloquer la boucle événementielle Telegram. Les réponses sont découpées automatiquement sous la limite Telegram et retombent en texte brut lorsqu’un format Markdown est invalide.

## Conformité WADA et extensions prévues

JKBOT peut constituer une interface pédagogique pour les athlètes, encadrants, fédérations, clubs et organisations sportives. Les extensions prévues sont les suivantes :

| Extension | Description |
| --- | --- |
| **Vérificateur de substances** | Recherche guidée dans la Liste des interdictions, avec distinction entre substances toujours interdites, interdites en compétition et interdites dans certains sports. La réponse devra toujours renvoyer vers la version officielle. |
| **Assistant AUT/TUE** | Checklist des informations à préparer pour une autorisation d’usage à des fins thérapeutiques, sans poser de diagnostic ni décider de l’éligibilité médicale. |
| **Calendrier de conformité sportive** | Rappels pour formations, contrôles, renouvellements documentaires, rapports et échéances internes. |
| **Registre d’incidents** | Journal chiffré des signalements, avec contrôle d’accès, minimisation des données et politique de conservation. |
| **Formation ADEL** | Parcours de quiz sur les droits et responsabilités, le contrôle, les conséquences du dopage et le sport propre. |
| **Tableau de bord des signataires** | Suivi de questionnaires, demandes d’information, audits et actions correctives. |
| **Budget et finance sportive** | Budget d’une fédération ou d’un club, suivi des subventions, coûts de contrôle, analyse des écarts et reporting financeur. |

Le Code mondial antidopage harmonise les politiques et règles antidopage avec huit standards internationaux [1]. La Liste des interdictions 2026 est entrée en vigueur le 1er janvier 2026 [2]. WADA présente l’éducation, les droits et responsabilités, les AUT/TUE et le processus de contrôle comme des thèmes fondamentaux [3]. La conformité inclut notamment l’éducation, les tests, la gestion des résultats, la protection des données, les audits et les actions correctives [4].

## Extensions finance et fiscalité proposées

La feuille de route peut être enrichie sans casser le fonctionnement actuel :

| Fonctionnalité | Valeur pour l’utilisateur |
| --- | --- |
| **Analyse de ratios multi-exercices** | Compare liquidité, marge, rentabilité, endettement, autonomie financière et trésorerie sur plusieurs périodes. |
| **Budget prévisionnel** | Produit un budget mensuel avec hypothèses, scénarios prudent/central/optimiste et analyse des écarts. |
| **Seuil de rentabilité** | Calcule le point mort à partir des charges fixes, du prix de vente et du coût variable. |
| **Plan de trésorerie** | Suit encaissements, décaissements, solde prévisionnel et besoins de financement. |
| **Assistant DSF renforcé** | Contrôle l’équilibre débit/crédit, signale les informations manquantes et exporte une proposition structurée. |
| **Contrôle de facture** | Vérifie présence du NIU, dates, totaux HT/TVA/TTC, doublons et incohérences apparentes. |
| **Assistant clôture** | Checklist des travaux d’inventaire, amortissements, provisions, régularisations et rapprochements. |
| **Veille fiscale versionnée** | Conserve source, date, juridiction, auteur, ancien texte et nouveau texte pour chaque mise à jour. |
| **Multi-pays CEMAC** | Sépare les règles par pays au lieu de mélanger les règles camerounaises avec celles d’autres juridictions. |
| **Exports professionnels** | Génère ultérieurement CSV, XLSX ou PDF à partir d’un résultat validé par l’utilisateur. |

## Sécurité et exploitation

Les clés ne doivent jamais être écrites dans le code, dans `README.md`, dans un commit ou dans un fichier partagé. Un ancien artefact du dépôt contenait des identifiants en clair : il a été retiré du contenu courant, mais toute clé qui aurait pu y figurer doit être révoquée et régénérée dans le fournisseur concerné. Le code d’administration est désormais désactivé par défaut tant que `JKBOT_ADMIN_CODE` n’est pas défini. Le token GitHub est facultatif et ne doit être accordé qu’avec le minimum de droits nécessaires.

Les fichiers JSON locaux sont adaptés à un prototype ou à un déploiement unique. Pour plusieurs instances, une haute disponibilité ou des données sensibles, il faudra migrer l’historique, les abonnements et les mises à jour vers une base de données avec contrôle d’accès, sauvegardes et journalisation.

Avant toute mise en production, testez au minimum `/start`, `/aide`, `/wada`, `/tva 500000`, `/is 5000000`, `/dsf`, un PDF, une image, un vocal et une question libre. Vérifiez également que les secrets sont présents et que le modèle choisi existe encore dans le catalogue Groq.

## Références officielles

[1]: https://www.wada-ama.org/en/what-we-do/world-anti-doping-code "WADA — The World Anti-Doping Code"

[2]: https://www.wada-ama.org/en/resources/world-anti-doping-code-and-international-standards/prohibited-list "WADA — Prohibited List"

[3]: https://www.wada-ama.org/en/athletes-support-personnel/anti-doping-education "WADA — Anti-Doping Education"

[4]: https://www.wada-ama.org/en/what-we-do/compliance-monitoring/code-compliance-implementation-and-maintenance "WADA — Code Compliance Implementation and Maintenance"

[5]: https://console.groq.com/docs/models "Groq — Supported Models"

[6]: https://console.groq.com/docs/deprecations "Groq — Model Deprecation"

[7]: https://console.groq.com/docs/vision "Groq — Images and Vision"

[8]: https://console.groq.com/docs/speech-to-text "Groq — Speech to Text"

## Contribution

Pour contribuer, créez une branche descriptive, ajoutez ou mettez à jour les tests, vérifiez `python3 -m py_compile telegram-bot/bot.py telegram-bot/chatbot.py`, puis ouvrez une Pull Request. Toute nouvelle règle fiscale ou antidopage doit être accompagnée de sa juridiction, de sa date d’effet et d’une source officielle.
