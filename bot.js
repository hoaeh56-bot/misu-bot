const { Telegraf } = require('telegraf');
const fs = require('fs');
const path = require('path');

const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_USERNAME = 'GHOUL'; 
const SITE_URL = 'https://misu-site.vercel.app/'; 
const DB_FILE = path.join(__dirname, 'requests.json');

function loadDB() {
  if (!fs.existsSync(DB_FILE)) return { withdrawals: [] };
  try { return JSON.parse(fs.readFileSync(DB_FILE, 'utf8')); } 
  catch (e) { return { withdrawals: [] }; }
}
function saveDB(data) { fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2)); }

// При нажатии старт передаем ID в ссылке
bot.start((ctx) => {
  const userId = ctx.from.id;
  // Добавляем ?tg_id=ID к ссылке
  const gameUrl = `${SITE_URL}?tg_id=${userId}`;

  ctx.reply('Добро пожаловать! Нажми кнопку ниже, чтобы играть.', {
    reply_markup: {
      inline_keyboard: [[ { text: '🎮 Открыть игру', web_app: { url: gameUrl } } ]]
    }
  });
});

// Ловим текстовые сообщения (для пополнения)
bot.on('text', async (ctx) => {
  const text = ctx.message.text;
  const userId = ctx.from.id;
  const userName = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

  // Если юзер написал +100 (без пробелов)
  if (text.startsWith('+') && !isNaN(parseInt(text.slice(1)))) {
    const amount = parseInt(text.slice(1));
    
    try {
      await bot.telegram.sendMessage(`@${ADMIN_USERNAME}`, 
        `💰 **ЗАЯВКА НА ПОПОЛНЕНИЕ**\n\n👤 Пользователь: ${userName} (ID: ${userId})\n⭐ Сумма: ${amount} звезд`, 
        { parse_mode: 'Markdown' }
      );
    } catch (e) {}
    return ctx.reply(`Заявка на пополнение (${amount} ⭐) отправлена. Админ свяжется с вами.`);
  }

  if (text === '/start') return; // Игнорируем команду старт

  ctx.reply('Нажмите кнопку выше, чтобы открыть игру.');
});

// Ловим вывод из игры (если Мисуграм всё-таки поддерживает sendData)
bot.on('web_app_data', async (ctx) => {
  try {
    const data = JSON.parse(ctx.message.web_app_data.data);
    const userId = ctx.from.id;
    const userName = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

    if (data.action === 'withdraw') {
      const { itemName, itemPrice } = data;
      
      const db = loadDB();
      db.withdrawals.push({ id: Date.now(), userId, userName, itemName, itemPrice, status: 'pending', date: new Date().toISOString() });
      saveDB(db);

      try {
        await bot.telegram.sendMessage(`@${ADMIN_USERNAME}`, 
          `📥 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n\n👤 Пользователь: ${userName}\n🎁 Подарок: ${itemName}\n💰 Стоимость: ${itemPrice} ⭐`, 
          { parse_mode: 'Markdown' }
        );
      } catch (e) {}
      
      await ctx.reply(`Заявка на вывод "${itemName}" создана. Ожидайте.`);
    }
  } catch (e) {}
});

bot.launch({ dropPendingUpdates: true });
console.log('Бот запущен!');
