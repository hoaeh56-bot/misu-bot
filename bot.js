const { Telegraf } = require('telegraf');

const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_CHAT_ID = '-100243'; 
const SITE_URL = 'https://misu-site.vercel.app/'; 

// ===== ОБРАБОТКА /start (С ПАРАМЕТРАМИ ОТ САЙТА) =====
bot.start(async (ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  const payload = ctx.startPayload; // То, что передал сайт (dep_100 или wd_75_Tamagochi)

  // Если пришли с сайта с заявкой на пополнение
  if (payload && payload.startsWith('dep_')) {
    const amount = parseInt(payload.split('_')[1]);
    
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
    } catch (e) { console.log("Ошибка отправки:", e.message); }

    return ctx.reply(`Заявка на пополнение ${amount} ⭐ создана!\n\n👉 Переведи ${amount} звезд на аккаунт @misurade.\nПосле перевода админ начислит тебе баланс.`);
  }

  // Если пришли с заявкой на вывод
  if (payload && payload.startsWith('wd_')) {
    const parts = payload.split('_');
    const price = parts[1];
    const itemName = decodeURIComponent(parts[2] || 'Подарок');

    const adminMsg = `📥 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n\n👤 Игрок: ${username}\n🆔 ID: ${userId}\n🎁 Подарок: ${itemName}\n💰 Стоимость: ${price} ⭐`;

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

    return ctx.reply(`Заявка на вывод "${itemName}" создана. Ожидайте.`);
  }

  // Обычный старт
  const gameUrl = `${SITE_URL}?tg_id=${userId}&name=${encodeURIComponent(username)}`;
  ctx.reply(`Добро пожаловать, ${username}!\nТвой ID: ${userId}\n\nНажми кнопку ниже, чтобы играть.`, {
    reply_markup: {
      inline_keyboard: [[ { text: '🎮 Открыть игру', web_app: { url: gameUrl } } ]]
    }
  });
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

bot.launch({ dropPendingUpdates: true });
console.log('Бот запущен!');
