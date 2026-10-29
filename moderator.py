@dp.message(Command("create_request"))
async def cmd_create_request(message: Message):
    if message.from_user.id != ADMIN_ID: return
    
    # Юзернейм или ID того, кого хочешь верифицировать
    target = "@твой_канал_или_бот" 
    
    try:
        # Вызов метода API для создания заявки (как в Telegram)
        await bot.session.make_request(
            method="setCustomVerification",
            data={
                "enabled": True,
                "peer": target, 
                "custom_description": "Проверено Corporate Freezers"
            }
        )
        await message.answer(f"✅ Заявка для {target} отправлена! Проверь панель.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
