from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from services.cross_rate import get_cross_rate
from services.pair_storage import add_watched_pair

TOKEN_A, TOKEN_B, ENTER_RATE = range(3)

temp_data = {}

async def start_monitoring_scene(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = await update.message.reply_text("Введіть перший токен (наприклад, BNB):")
    context.user_data["scene_messages"] = [msg.message_id]
    return TOKEN_A

async def token_a_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    token_a = update.message.text.upper()
    temp_data[update.effective_user.id] = {"token_a": token_a}
    context.user_data["scene_messages"].append(update.message.message_id)

    msg = await update.message.reply_text("Введіть другий токен (наприклад, ETH):")
    context.user_data["scene_messages"].append(msg.message_id)
    return TOKEN_B

async def token_b_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    token_b = update.message.text.upper()
    temp_data[update.effective_user.id]["token_b"] = token_b
    context.user_data["scene_messages"].append(update.message.message_id)

    msg = await update.message.reply_text("Введіть стартовий крос-курс або напишіть `auto`, щоб розрахувати автоматично:")
    context.user_data["scene_messages"].append(msg.message_id)
    return ENTER_RATE

async def enter_cross_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    context.user_data["scene_messages"].append(update.message.message_id)

    token_a = temp_data[user_id]["token_a"]
    token_b = temp_data[user_id]["token_b"]
    text = update.message.text.strip()

    try:
        if text.lower() == "auto":
            cross_rate = await get_cross_rate(token_a, token_b)
        else:
            cross_rate = float(text)

        add_watched_pair(token_a, token_b, cross_rate)

        # Видаляємо всі повідомлення сцени
        chat_id = update.effective_chat.id
        for msg_id in context.user_data.get("scene_messages", []):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except:
                pass

        context.user_data["scene_messages"] = []

        await update.message.reply_text(f"✅ Пара {token_a}/{token_b} додана з курсом {cross_rate:.6f}")
        return ConversationHandler.END

    except Exception as e:
        msg = await update.message.reply_text(f"❌ Помилка: {e}")
        context.user_data["scene_messages"].append(msg.message_id)
        return ENTER_RATE
