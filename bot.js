const { Telegraf } = require('telegraf');

// Токен твоего бота
const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { 
    apiRoot: 'http://2.26.51.20:8088/bot' 
  }
});

// Твой юзернейм без собаки (чтобы бот знал кому присылать заявки)
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
    
    // Пополнение баланса
    if (data.action === 'deposit') {
      const amount = data.amount;
      await ctx.replyWithInvoice({
        title: `Пополнение на ${amount} ⭐`,
        description: `Покупка ${amount} игровых звезд`,
        payload: `deposit_${amount}_${ctx.from.id}`,
        provider_token: '', 
        currency: 'XTR', 
        prices: [{ label: 'Звезды', amount: amount }]
      });
    }

    // Заявка на вывод
    if (data.action === 'withdraw') {
      const itemName = data.itemName;
      const itemPrice = data.itemPrice;
      const userName = data.userName || ctx.from.username || ctx.from.first_name;
      
      // Отправляем сообщение тебе (админу)
      try {
        await bot.telegram.sendMessage(`@${ADMIN_USERNAME}`, 
          ` **НОВАЯ ЗАЯВКА НА ВЫВОД**\n\n` +
          `👤 Пользователь: ${userName}\n` +
          ` Подарок: ${itemName}\n` +
          ` Стоимость: ${itemPrice} ⭐\n\n` +
          `Свяжитесь с пользователем для выдачи.`, 
          { parse_mode: 'Markdown' }
        );
      } catch (e) {
        console.log("Не удалось отправить сообщение админу. Возможно, он не писал боту /start.");
      }
      
      await ctx.reply('Заявка на вывод обрабатывается. Ожидайте сообщения от администратора.');
    }

  } catch (e) {
    console.error(e);
    ctx.reply('Ошибка при обработке данных.');
  }
});

bot.on('successful_payment', async (ctx) => {
  const payment = ctx.message.successful_payment;
  const amount = payment.total_amount;
  ctx.reply(`Оплата прошла успешно! Вы купили ${amount} звезд.`);
});

bot.launch();
console.log('Бот запущен!');
