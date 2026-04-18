import logging
import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("TG_TOKEN")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
MODEL = "google/gemma-3-27b-it:free"
LLM_URL = "https://openrouter.ai/api/v1/chat/completions"

logging.basicConfig(level=logging.INFO)

AGENTS = [
    {
        "name": "🔧 Pragmatic Engineer",
        "system": "You are a Pragmatic Engineer. Give concrete actionable steps, realistic estimates, specific tools. Skip theory. Be concise. Respond in the same language as the user.",
        "temperature": 0.5
    },
    {
        "name": "🧪 Mad Scientist",
        "system": "You are a Mad Scientist. Propose radical, unexpected, creative ideas. Ignore conventional constraints. Think in analogies and first-principles. Respond in the same language as the user.",
        "temperature": 0.95
    },
    {
        "name": "🛡 Sovereignty Hacker",
        "system": "You are a Sovereignty Hacker. Prioritize open-source, local-first, zero vendor lock-in. Identify hidden dependencies. Maximize user control. Be direct and technical. Respond in the same language as the user.",
        "temperature": 0.7
    }
]


async def call_agent(session: aiohttp.ClientSession, agent: dict, user_input: str) -> str:
    try:
        async with session.post(
            LLM_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": agent["system"]},
                    {"role": "user", "content": user_input}
                ],
                "temperature": agent["temperature"],
                "max_tokens": 600
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            data = await response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Ошибка: {e}]"


async def ask_all_agents(user_input: str) -> str:
    async with aiohttp.ClientSession() as session:
        tasks = [call_agent(session, agent, user_input) for agent in AGENTS]
        results = await asyncio.gather(*tasks)

    parts = []
    for agent, result in zip(AGENTS, results):
        parts.append(f"{agent['name']}:\n{result}")

    return "\n\n---\n\n".join(parts)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await update.message.reply_text("⏳ Спрашиваю трёх агентов...")

    response = await ask_all_agents(user_input)

    # Telegram лимит 4096 символов — режем если длиннее
    if len(response) > 4096:
        response = response[:4090] + "\n[...]"

    await update.message.reply_text(response)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет. Отправь любой вопрос — отвечу с трёх точек зрения:\n\n"
        "🔧 Pragmatic Engineer — что конкретно делать\n"
        "🧪 Mad Scientist — нестандартные идеи\n"
        "🛡 Sovereignty Hacker — независимость и контроль"
    )


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Бот запущен...")
app.run_polling()
