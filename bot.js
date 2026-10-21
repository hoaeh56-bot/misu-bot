const { Telegraf } = require('telegraf');

const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { 
    apiRoot: 'http://2.26.51.20:8088/bot' 
  }
});

const ADMIN_USERNAME = 'GHOUL'; 

bot.start((ctx) => {
  ctx.reply('Привет! Нажми кнопку ниже, чтобы играть.', {
    reply_markup: {
      inline_keyboard: [[
        { text: '🎮 Открыть игру', web_app: { url: 'https://misyrade.netlify.app' } }
      ]]
    }
  });
});

bot.on('web_app_data', async (ctx) => {
  try {
    const data = JSON.parse(ctx.message.web_app_data.data);
    
    // ПОПОЛНЕНИЕ
    if (data.action === 'deposit') {
      const amount = data.amount;
      const chatId = ctx.chat.id;
      
      // Пытаемся отправить счет (может не сработать в Мисуграме)
      try {
        await ctx.replyWithInvoice({
          title: `Пополнение на ${amount} ⭐`,
          description: `Покупка ${amount} игровых звезд`,
          payload: `deposit_${amount}_${chatId}`,
          provider_token: '', 
          currency: 'XTR', 
          prices: [{ label: 'Звезды', amount: amount }]
        });
      } catch (error) {
        // Если Мисуграм не поддерживает оплату в чате, отправляем ссылку
        ctx.reply(`Ошибка создания счета. Для пополнения на ${amount} ⭐ свяжитесь с администратором: @${ADMIN_USERNAME}`);
      }
    }

    // ВЫВОД
    if (data.action === 'withdraw') {
      const itemName = data.itemName;
      const itemPrice = data.itemPrice;
      const userName = data.userName || ctx.from.username || ctx.from.first_name;
      
      try {
        await bot.telegram.sendMessage(`@${ADMIN_USERNAME}`, 
          `📥 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n\n` +
          `👤 Пользователь: ${userName}\n` +
          `🎁 Подарок: ${itemName}\n` +
          `💰 Стоимость: ${itemPrice} ⭐\n\n` +
          `Свяжитесь с пользователем для выдачи.`, 
          { parse_mode: 'Markdown' }
        );
      } catch (e) {
        console.log("Не удалось отправить сообщение админу.");
      }
      
      await ctx.reply('Заявка на вывод обрабатывается. Ожидайте сообщения от администратора.');
    }

  } catch (e) {
    console.error(e);
    ctx.reply('Ошибка при обработке данных. Попробуйте еще раз.');
  }
});

bot.on('successful_payment', async (ctx) => {
  const payment = ctx.message.successful_payment;
  const amount = payment.total_amount;
  ctx.reply(`Оплата прошла успешно! Вы купили ${amount} звезд.`);
});

bot.launch();
console.log('Бот запущен!');
