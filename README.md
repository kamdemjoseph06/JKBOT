# 🤖 JKBOT — Assistant Fiscal & Comptable Camerounais

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?logo=telegram)](https://t.me/)
[![Groq](https://img.shields.io/badge/LLM-Groq_LLaMA_3.3-orange)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**JKBOT** est un bot Telegram expert en fiscalité camerounaise (CGI 2026) et en comptabilité OHADA/SYSCOHADA, propulsé par le modèle LLaMA 3.3-70B via l'API Groq. Il couvre les calculs fiscaux automatiques, les écritures comptables SYSCOHADA, les quiz de formation, les rappels mensuels et bien plus.

---

## ✨ Fonctionnalités

### 🧮 Calculatrices fiscales instantanées
| Commande | Description |
|----------|-------------|
| `/tva 500000` | Calcul TVA 19,25% (HT → TTC) |
| `/is 5000000` | Impôt sur les Sociétés + CAC |
| `/irpp 350000` | IRPP mensuel sur barème progressif |
| `/cnps 400000` | Cotisations CNPS salarié + patronal |
| `/calculer` | Guide complet calculatrice multi-impôts |

### 📚 Cours & Référence
| Commande | Description |
|----------|-------------|
| `/cours` | Cours complet comptabilité SYSCOHADA |
| `/etats` | Structure des états financiers (Bilan, CR, TFT) |
| `/patente` | Guide calcul de la patente |
| `/lf2025` | Mesures clés Loi de Finances 2025 |
| `/lf 2027` | Dispositions LF d'une année donnée |
| `/calendrier` | Calendrier fiscal annuel complet |
| `/creation` | Guide création d'entreprise (SARL, SA…) |

### 🤖 Assistant DSF — Écritures SYSCOHADA Intelligentes
| Commande | Description |
|----------|-------------|
| `/dsf` | Active le mode écritures SYSCOHADA |
| `/stop` | Quitte le mode DSF |

En mode DSF, décrivez une opération en français naturel, le bot génère les écritures comptables complètes avec numéros de comptes, débits/crédits et analyse fiscale.

**Exemples :**
```
Achat de marchandises 500 000 FCFA TTC à crédit
Vente de produits 1 200 000 FCFA TTC, payée par virement
Dotation amortissement matériel 8 000 000 FCFA sur 4 ans, 2ème année
Paiement salaires : brut 600 000, CNPS salarié, IRPP
```

### 📄 Générateur de Documents
| Commande | Description |
|----------|-------------|
| `/facture` | Modèle de facture camerounaise conforme (NIU, TVA) |
| `/fiche_paie` | Fiche de paie OHADA avec exemple chiffré |

### 🎯 Quiz de Formation
| Commande | Description |
|----------|-------------|
| `/quiz` | Question aléatoire (fiscalité ou comptabilité) |
| `/quiz_fiscal` | Quiz fiscalité uniquement |
| `/quiz_compta` | Quiz comptabilité uniquement |
| `/score` | Votre bilan de performance |

### 📅 Rappels Mensuels Automatiques
| Commande | Description |
|----------|-------------|
| `/rappel` | Activer/désactiver les rappels du 1er du mois |

Chaque 1er du mois à 7h00 (heure Douala), les abonnés reçoivent automatiquement les échéances fiscales du mois (TVA, IS, CNPS, patente…).

### 🔄 Base CGI Auto-Évolutive
| Commande | Description |
|----------|-------------|
| `/nouveautes` | Voir toutes les mises à jour CGI enregistrées |
| `/lf 2027` | Dispositions d'une année spécifique |
| `/maj_cgi CODE ANNEE TITRE \| CONTENU` | *(Admin)* Ajouter une nouvelle disposition |

Le bot intègre automatiquement toutes les nouvelles dispositions dans **toutes ses réponses IA**, permettant une mise à jour du droit fiscal sans redéploiement.

### 🌐 Autres
| Commande | Description |
|----------|-------------|
| `/aide` | Menu complet de toutes les commandes |
| `/lang` | Basculer entre Français 🇫🇷 et Anglais 🇬🇧 |
| `/reset` | Effacer l'historique de conversation |
| `/start` | Message de bienvenue |

---

## 🚀 Installation

### Prérequis
- Python 3.11+
- Compte Telegram + Bot Token (via [@BotFather](https://t.me/BotFather))
- Clé API Groq (via [console.groq.com](https://console.groq.com))

### 1. Cloner le dépôt
```bash
git clone https://github.com/kamdemjoseph06/JKBOT.git
cd JKBOT
```

### 2. Installer les dépendances
```bash
cd telegram-bot
pip install python-telegram-bot[job-queue] groq httpx pytz apscheduler
```

### 3. Configurer les variables d'environnement
Créez un fichier `.env` ou exportez les variables :
```bash
export TOKEN_TELEGRA="votre_token_telegram"
export CLE_GRO="votre_cle_api_groq"
export JKBOT_ADMIN_CODE="votre_code_admin"   # pour /maj_cgi
```

### 4. Lancer le bot
```bash
cd telegram-bot
python bot.py
```

---

## 🗂️ Structure du projet

```
JKBOT/
├── telegram-bot/
│   ├── bot.py                    # Code principal du bot (~1 900 lignes)
│   ├── cgi_updates.json          # Base CGI auto-évolutive (mises à jour annuelles)
│   ├── rappel_subscribers.json   # Liste des abonnés aux rappels mensuels
│   └── historiques.json          # Historiques de conversations (auto-généré)
├── artifacts/
│   └── api-server/               # Serveur API Express (infrastructure Replit)
├── README.md
└── replit.md
```

---

## ⚙️ Architecture technique

| Composant | Technologie |
|-----------|------------|
| Bot framework | `python-telegram-bot` 22.x (async) |
| Modèle IA | `llama-3.3-70b-versatile` via Groq API |
| Planificateur | APScheduler (JobQueue intégré PTB) |
| Persistance | JSON fichiers locaux |
| Runtime | Python 3.11 |

### Flux de traitement d'un message

```
Message utilisateur
       │
       ▼
  Réponse quiz ? ──→ Correction + explication
       │
       ▼
  Calcul automatique ? ──→ Résultat chiffré (IS/TVA/IRPP/CNPS…)
       │
       ▼
  Mode DSF actif ? ──→ Écritures SYSCOHADA (prompt spécialisé)
       │
       ▼
  Réponse IA normale (SYSTEM_PROMPT + mises à jour CGI + langue)
```

### Système de prompt dynamique
Le bot charge `cgi_updates.json` à chaque requête IA et injecte automatiquement les nouvelles dispositions fiscales dans le system prompt — aucun redéploiement nécessaire pour mettre à jour la base légale.

---

## 🔐 Sécurité

- Les tokens et clés API sont stockés en variables d'environnement (jamais en clair dans le code)
- La commande `/maj_cgi` est protégée par un code admin (`JKBOT_ADMIN_CODE`)
- Le code admin par défaut doit être changé en production

---

## 📊 Calculs fiscaux implémentés

### Impôt sur les Sociétés (IS) — CGI 2026
- Taux normal : **30%** (CA ≥ 3 Mds FCFA)
- Taux réduit PME : **25%** (CA < 3 Mds FCFA)
- Taux agricole : **20%**
- Centimes additionnels communaux (CAC) : **10%** de l'IS

### IRPP mensuel — Barème progressif
| Tranche (mensuel) | Taux |
|-------------------|------|
| 0 – 62 000 FCFA | 0% |
| 62 001 – 125 000 FCFA | 11% |
| 125 001 – 250 000 FCFA | 16,5% |
| 250 001 – 417 000 FCFA | 27,5% |
| > 417 000 FCFA | 38,5% |

### TVA
- Taux normal : **19,25%**
- Exportations et opérations assimilées : **0%**

### CNPS
| Cotisation | Taux | Plafond |
|-----------|------|---------|
| Salarié (AVID) | 2,8% | 750 000 FCFA |
| Patronal AVID | 4,2% | 750 000 FCFA |
| Allocations familiales | 7% | — |
| AT/MP | 1,75% | — |

---

## 🤝 Contribuer

1. Forkez le dépôt
2. Créez une branche : `git checkout -b feature/nouvelle-fonctionnalite`
3. Committez vos changements
4. Pushez et ouvrez une Pull Request

Pour ajouter de nouvelles dispositions CGI sans modifier le code, utilisez directement la commande `/maj_cgi` dans le bot (accès admin requis).

---

## 📝 Licence

MIT — Voir le fichier [LICENSE](LICENSE) pour les détails.

---

*Développé pour les professionnels de la fiscalité et de la comptabilité au Cameroun 🇨🇲*
