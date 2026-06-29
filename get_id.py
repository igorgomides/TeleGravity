import os
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Tenta carregar do .env se existir
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"\n✅ SEU ID É: {user_id}")
    print("Copie este número para o seu arquivo .env no campo AUTHORIZED_USER_ID\n")
    await update.message.reply_text(f"Seu ID detectado: {user_id}")
    # Encerra o script após capturar o ID
    os._exit(0)

if __name__ == '__main__':
    # Se não houver token no .env, pede ao usuário
    if not TOKEN or "your_telegram_bot_token" in TOKEN:
        TOKEN = input("Digite o TOKEN do seu bot (fornecido pelo BotFather): ").strip()
    
    if not TOKEN:
        print("Erro: Nenhum token fornecido.")
        sys.exit(1)

    try:
        app = ApplicationBuilder().token(TOKEN).build()
        print("\n--- Buscador de ID do Telegram ---")
        print("1. Vá no Telegram e envie QUALQUER mensagem para o SEU BOT.")
        print("2. O ID aparecerá aqui embaixo assim que você enviar.")
        print("----------------------------------\n")
        
        app.add_handler(MessageHandler(filters.ALL, get_id))
        app.run_polling()
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")
