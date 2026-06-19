import os
import base64
import httpx
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """Tu es un expert en trading Price Action avec 30 ans d'expérience, spécialisé dans les options binaires sur marchés OTC (Pocket Option). Tu analyses des graphiques de chandeliers japonais.

Ta stratégie s'appelle Phantom Reversal Pro. Elle est basée UNIQUEMENT sur le Price Action pur — zéro indicateur.

## TES RÈGLES D'ANALYSE

### Sur le graphique 5 min (contexte) :
- Identifier les niveaux clés : support et résistance (minimum 2 touches pour être valide)
- Lire la structure du marché : Uptrend (HH/HL), Downtrend (LH/LL), Range
- Identifier si le prix est SUR un niveau clé ou en milieu de nulle part

### Sur le graphique 1 min (entrée) :
- Pin Bar : longue mèche, petit corps → entrée opposée à la mèche
- Engulfing : bougie qui avale la précédente sur niveau clé → entrée dans la direction de l'engulfing
- Double Touch : 2ème contact sur le niveau → signal le plus fiable

### Checklist de confluence (5 critères) :
1. Niveau clé identifié et validé (2+ touches)
2. Signal bougie clair (Pin Bar, Engulfing, Double Touch)
3. Structure de marché favorable
4. Pas de bougie énorme en cours (trop tard pour entrer)
5. Zone de retournement nette visible

## TON FORMAT DE RÉPONSE

Réponds UNIQUEMENT dans ce format exact :

🎯 SIGNAL : [CALL 📈 / PUT 📉 / NO TRADE ⛔]
⭐ Confiance : [1-5]/5
🔗 Confluence : [0-5]/5
🕯 Signal bougie : [Pin Bar / Engulfing / Double Touch / Aucun]
📊 Niveau clé : [Support / Résistance / Aucun]
📈 Structure : [Uptrend / Downtrend / Range / Indéfini]

📝 Analyse :
[3-4 phrases d'analyse précise]

⚠️ Avertissement :
[Risques ou points d'attention, ou Aucun si signal propre]

---
Phantom Reversal Pro · Price Action pur · OTC 5min"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bienvenue sur *Phantom Reversal Pro* !\n\n"
        "📊 Envoie-moi un screenshot de ton graphique Pocket Option\n"
        "et je t'analyse le signal d'entrée selon la stratégie Price Action pure.\n\n"
        "⏰ *Fenêtres optimales :* 8h-10h et 13h-16h UTC\n"
        "🕯 *Timeframe :* Analyse 5min → Entrée 1min\n\n"
        "Envoie ton graphique maintenant ! 🚀",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Comment utiliser Phantom Reversal Pro :*\n\n"
        "1️⃣ Ouvre Pocket Option\n"
        "2️⃣ Passe en timeframe *5 min*\n"
        "3️⃣ Prends un screenshot du graphique\n"
        "4️⃣ Envoie-le ici\n"
        "5️⃣ Attends mon analyse\n\n"
        "*Signals possibles :*\n"
        "📈 CALL → Tu cliques ACHAT\n"
        "📉 PUT → Tu cliques VENTE\n"
        "⛔ NO TRADE → Tu passes ce trade\n\n"
        "⚠️ *Règle d'or :* Ne trade jamais avec une confluence < 3/5",
        parse_mode="Markdown"
    )


async def analyze_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Analyse en cours... Patiente 15 secondes.")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        async with httpx.AsyncClient() as client:
            photo_response = await client.get(file.file_path)
            image_data = base64.b64encode(photo_response.content).decode("utf-8")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 1000,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "Analyse ce graphique selon la stratégie Phantom Reversal Pro et donne-moi le signal d'entrée."
                                }
                            ]
                        }
                    ]
                }
            )

        data = response.json()
        analysis = data["content"][0]["text"]

        await update.message.reply_text(
            f"*📊 PHANTOM REVERSAL PRO*\n\n{analysis}",
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Erreur lors de l'analyse. Réessaie.\nDétail : {str(e)}"
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Envoie-moi un *screenshot de ton graphique* pour obtenir un signal.\n\n"
        "Tape /help pour voir comment utiliser le bot.",
        parse_mode="Markdown"
    )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).updater(None).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_chart))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Phantom Reversal Pro Bot demarre...")
    
    async def run():
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()

    asyncio.run(run())


if __name__ == "__main__":
    main()
