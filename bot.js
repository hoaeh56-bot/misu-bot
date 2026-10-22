const { Telegraf } = require('telegraf');
const fs = require('fs');
const path = require('path');

const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

// Твой ID чата для заявок
const ADMIN_CHAT_ID = '-100243'; 
const SITE_URL = 'https://misu-site.vercel.app/'; 

const DB_FILE = path.join(__dirname, 'users.json');

function loadDB() {
  if (!fs.existsSync(DB_FILE)) return { users: {} };
  try { return JSON.parse(fs.readFileSync(DB_FILE, 'utf8')); } 
  catch (e) { return { users: {} }; }
}

function saveDB(data) {
  fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2));
}

// Обработка /start
bot.start((ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

  const db = loadDB();
  db.users[userId] = { id: userId, username: username };
  saveDB(db);

  const gameUrl = `${SITE_URL}?tg_id=${userId}&name=${encodeURIComponent(username)}`;

  ctx.reply(`Добро пожаловать, ${username}!\nТвой ID: ${userId}\n\nНажми кнопку ниже, чтобы играть.`, {
    reply_markup: {
      inline_keyboard: [[ { text: '🎮 Открыть игру', web_app: { url: gameUrl } } ]]
    }
  });
});

// Ловим текстовые сообщения
bot.on('text', async (ctx) => {
  const text = ctx.message.text.trim();
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

  if (text === '/start') return;

  // ПОПОЛНЕНИЕ
  if (text.startsWith('+') && !isNaN(parseInt(text.slice(1)))) {
    const amount = parseInt(text.slice(1));
    
    const adminMsg = `💰 **ЗАЯВКА НА ПОПОЛНЕНИЕ**\n\n👤 Игрок: ${username}\n🆔 ID: ${userId}\n⭐ Сумма: ${amount} звезд`;

    try {
      await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [[
            { text: '✅ Начислить', callback_data: `approve_dep_${userId}_${amount}` },
            { text: '❌ Отклонить', callback_data: `reject_dep_${userId}` }
          ]]
        }
      });
    } catch (e) { console.log("Ошибка отправки в чат:", e.message); }

    return ctx.reply(`Заявка на пополнение ${amount} ⭐ создана!\n\n👉 Переведи ${amount} звезд на аккаунт @misurade.\nПосле перевода админ начислит тебе баланс.`);
  }

  // ВЫВОД
  if (text.startsWith('Вывод:')) {
    const adminMsg = `📥 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n\n👤 Игрок: ${username}\n🆔 ID: ${userId}\n${text}`;

    try {
      await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [[
            { text: '✅ Выдать', callback_data: `approve_wd_${userId}` },
            { text: '❌ Отклонить', callback_data: `reject_wd_${userId}` }
          ]]
        }
      });
    } catch (e) {}

    return ctx.reply(`Заявка на вывод "${text}" создана. Ожидайте.`);
  }

  ctx.reply('Нажми /start, чтобы открыть игру.');
});

// ===== ОБРАБОТКА КНОПОК В ЧАТЕ =====
bot.action(/approve_dep_(\d+)_(\d+)/, async (ctx) => {
  const targetUserId = ctx.match[1];
  const amount = ctx.match[2];
  ctx.answerCbQuery('Начислено!');
  ctx.editMessageText(`✅ Пополнение на ${amount} ⭐ для игрока ${targetUserId} ОДОБРЕНО.`);
  try { await bot.telegram.sendMessage(targetUserId, `✅ Ваше пополнение на ${amount} ⭐ одобрено!`); } catch (e) {}
});

bot.action(/approve_wd_(\d+)/, async (ctx) => {
  const targetUserId = ctx.match[1];
  ctx.answerCbQuery('Выдано!');
  ctx.editMessageText(`✅ Вывод для игрока ${targetUserId} ОДОБРЕН.`);
  try { await bot.telegram.sendMessage(targetUserId, `✅ Ваша заявка на вывод одобрена!`); } catch (e) {}
});

bot.action(/reject_dep_(\d+)/, async (ctx) => {
  const targetUserId = ctx.match[1];
  ctx.answerCbQuery('Отклонено!');
  ctx.editMessageText(`❌ Заявка на пополнение для игрока ${targetUserId} ОТКЛОНЕНА.`);
  try { await bot.telegram.sendMessage(targetUserId, `❌ Ваша заявка на пополнение отклонена.`); } catch (e) {}
});

bot.action(/reject_wd_(\d+)/, async (ctx) => {
  const targetUserId = ctx.match[1];
  ctx.answerCbQuery('Отклонено!');
  ctx.editMessageText(`❌ Заявка на вывод для игрока ${targetUserId} ОТКЛОНЕНА.`);
  try { await bot.telegram.sendMessage(targetUserId, `❌ Ваша заявка на вывод отклонена.`); } catch (e) {}
});

// Ловим данные с сайта (если Мисуграм поддерживает sendData)
bot.on('web_app_data', async (ctx) => {
  try {
    const data = JSON.parse(ctx.message.web_app_data.data);
    const userId = ctx.from.id;
    const userName = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

    if (data.action === 'deposit') {
      const amount = data.amount;
      const adminMsg = `💰 **ЗАЯВКА НА ПОПОЛНЕНИЕ (С САЙТА)**\n\n👤 Игрок: ${userName}\n🆔 ID: ${userId}\n⭐ Сумма: ${amount} звезд`;

      try {
        await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
          parse_mode: 'Markdown',
          reply_markup: {
            inline_keyboard: [[
              { text: '✅ Начислить', callback_data: `approve_dep_${userId}_${amount}` },
              { text: '❌ Отклонить', callback_data: `reject_dep_${userId}` }
            ]]
          }
        });
      } catch (e) {}
      await ctx.reply(`Заявка на ${amount} ⭐ создана.\nПереведи ${amount} звезд на @misurade.`);
    }

    if (data.action === 'withdraw') {
      const { itemName, itemPrice } = data;
      const adminMsg = `📥 **НОВАЯ ЗАЯВКА НА ВЫВОД (С САЙТА)**\n\n👤 Игрок: ${userName}\n🆔 ID: ${userId}\n🎁 Подарок: ${itemName}\n💰 Стоимость: ${itemPrice} ⭐`;

      try {
        await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
          parse_mode: 'Markdown',
          reply_markup: {
            inline_keyboard: [[
              { text: '✅ Выдать', callback_data: `approve_wd_${userId}` },
              { text: '❌ Отклонить', callback_data: `reject_wd_${userId}` }
            ]]
          }
        });
      } catch (e) {}
      await ctx.reply(`Заявка на вывод "${itemName}" создана.`);
    }
  } catch (e) { console.log("Ошибка web_app_data"); }
});

bot.launch({ dropPendingUpdates: true });
console.log('Бот запущен!');
