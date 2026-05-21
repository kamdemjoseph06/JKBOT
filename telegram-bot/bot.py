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
        f"👋 Bonjour {prenom} !\nJe suis JKBOT 🇨🇲 expert fiscal.\nPosez vos questions !"
    )

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    historiques[user_id] = []
    sauvegarder_historiques(historiques)
    await update.message.reply_text("🔄 Historique effacé !")

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
            messages=[{
                "role": "system",
                "content": "Tu es JKBOT, expert fiscal camerounais (LF 2025). TVA 19.25%, IS 30%, IRPP barème progressif. Réponds en français avec émojis."
            }] + historiques[user_id],
            max_tokens=1024,
            temperature=0.7
        )

        texte = reponse.choices[0].message.content
        historiques[user_id].append({"role": "assistant", "content": texte})
        if len(historiques[user_id]) > 20:
            historiques[user_id] = historiques[user_id][-20:]

        sauvegarder_historiques(historiques)
        await update.message.reply_text(texte)
    except Exception as e:
        print(f"❌ Erreur Groq: {e}")
        await update.message.reply_text("❌ Erreur technique. Réessayez.")

def main():
    if not TOKEN_TELEGRAM:
        print("❌ TOKEN_TELEGRA manquant dans les variables d'environnement")
        sys.exit(1)
    if not CLE_GROQ:
        print("❌ CLE_GRO manquante dans les variables d'environnement")
        sys.exit(1)

    print("🤖 Initialisation de JKBOT...")
    app = Application.builder().token(TOKEN_TELEGRAM).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre))

    print("✅ Configuration terminée. Connexion à Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
