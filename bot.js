const { Telegraf } = require('telegraf');

// Твой токен
const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { 
    apiRoot: 'http://2.26.51.20:8088/bot' // Адрес API Мисуграма
  }
});

bot.start((ctx) => {
  ctx.reply('Привет! Нажми кнопку ниже, чтобы играть.', {
    reply_markup: {
      inline_keyboard: [[
        { text: '🎮 Открыть игру', web_app: { url: 'https://example.com' } }
      ]]
    }
  });
});

bot.on('web_app_data', async (ctx) => {
  try {
    const data = JSON.parse(ctx.message.web_app_data.data);
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
  } catch (e) {
    console.error(e);
    ctx.reply('Ошибка при создании счета.');
  }
});

bot.on('successful_payment', async (ctx) => {
  const payment = ctx.message.successful_payment;
  ctx.reply(`Оплата прошла успешно! Вы купили ${payment.total_amount} звезд.`);
});

bot.launch();
console.log('Бот запущен!');
