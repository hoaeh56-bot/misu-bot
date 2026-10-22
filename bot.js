const { Telegraf } = require('telegraf');
const fs = require('fs');
const path = require('path');

// Твой токен
const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_USERNAME = 'GHOUL'; 
const SITE_URL = 'https://misu-site.vercel.app/'; // Твоя ссылка на Vercel

// Файл для хранения заявок (чтобы не потерять, если сервер перезагрузится)
const DB_FILE = path.join(__dirname, 'requests.json');

function loadDB() {
  if (!fs.existsSync(DB_FILE)) return { withdrawals: [] };
  try { return JSON.parse(fs.readFileSync(DB_FILE, 'utf8')); } 
  catch (e) { return { withdrawals: [] }; }
}

function saveDB(data) {
  fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2));
}

// Обработка команды /start
bot.start((ctx) => {
  ctx.reply('Добро пожаловать в misugrader! Нажмите кнопку ниже, чтобы открыть игру.', {
    reply_markup: {
      inline_keyboard: [[
        { text: '🎮 Открыть игру', web_app: { url: SITE_URL } }
      ]]
    }
  });
});

// Обработка данных из игры (пополнение и вывод)
bot.on('web_app_data', async (ctx) => {
  try {
    const data = JSON.parse(ctx.message.web_app_data.data);
    const userId = ctx.from.id;
    const userName = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

    // 1. Запрос на пополнение
    if (data.action === 'deposit') {
      const amount = data.amount;
      
      // Отправляем уведомление тебе (админу)
      try {
        await bot.telegram.sendMessage(`@${ADMIN_USERNAME}`, 
          `💰 **ЗАЯВКА НА ПОПОЛНЕНИЕ**\n\n` +
          `👤 Пользователь: ${userName} (ID: ${userId})\n` +
          `⭐ Сумма: ${amount} звезд\n\n` +
          `Свяжитесь с пользователем для оплаты.`, 
          { parse_mode: 'Markdown' }
        );
      } catch (e) {
        console.log("Не удалось отправить сообщение админу (возможно, он не нажал /start).");
      }

      // Отвечаем игроку
      await ctx.reply(`Заявка на пополнение (${amount} ⭐) отправлена администратору. Ожидайте сообщения.`);
    }

    // 2. Запрос на вывод подарка
    if (data.action === 'withdraw') {
      const { itemName, itemPrice } = data;
      
      // Сохраняем заявку в файл
      const db = loadDB();
      const requestId = Date.now();
      db.withdrawals.push({
        id: requestId,
        userId: userId,
        userName: userName,
        itemName: itemName,
        itemPrice: itemPrice,
        status: 'pending',
        date: new Date().toISOString()
      });
      saveDB(db);

      // Отправляем уведомление тебе (админу)
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
        console.log("Не удалось отправить сообщение админу (возможно, он не нажал /start).");
      }

      // Отвечаем игроку
      await ctx.reply(`Заявка на вывод подарка "${itemName}" создана. Ожидайте сообщения от администратора.`);
    }

  } catch (e) {
    console.error('Ошибка обработки данных:', e);
    ctx.reply('Ошибка при обработке данных. Попробуйте еще раз.');
  }
});

// Запуск бота
bot.launch({
  dropPendingUpdates: true // Сбрасываем старые зависшие сообщения
});
console.log('Бот misugrader запущен!');
