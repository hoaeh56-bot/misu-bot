const { Telegraf } = require('telegraf');
const express = require('express');
const cors = require('cors');

const bot = new Telegraf('1780243237:1w2CHS4zqtHz5dJ5QJEBdwHKTNEwjWPiUQY', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_CHAT_ID = '-100243'; 
const ADMIN_IDS = ['1780243206']; // Твой ID для ЛС
const SITE_URL = 'https://misu-site.vercel.app/'; 

// ===== СЕРВЕР =====
const app = express();
app.use(cors()); 
app.use(express.json());
app.listen(process.env.PORT || 3000, () => console.log('Сервер запущен!'));

const waitingForAmount = new Set();

// ===== ЛОГИКА БОТА =====
bot.start((ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  const gameUrl = `${SITE_URL}?tg_id=${userId}&name=${encodeURIComponent(username)}`;

  // Отправляем меню с кнопками
  ctx.reply(`Добро пожаловать, ${username}!\nТвой ID: ${userId}\n\nВыбери действие:`, {
    reply_markup: {
      inline_keyboard: [
        [{ text: '🎮 Открыть игру', web_app: { url: gameUrl } }],
        [{ text: '💰 Пополнить баланс', callback_data: 'deposit_start' }]
      ]
    }
  });
});

// Кнопка пополнения
bot.action('deposit_start', (ctx) => {
  ctx.answerCbQuery();
  waitingForAmount.add(ctx.from.id);
  ctx.reply('Введите сумму в звездах (только цифры, например: 100):');
});

// Ловим сумму
bot.on('text', async (ctx) => {
  const userId = ctx.from.id;
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  const text = ctx.message.text.trim();

  if (text === '/start') return;

  if (waitingForAmount.has(userId)) {
    const amount = parseInt(text);
    
    if (isNaN(amount) || amount < 1) {
      return ctx.reply('Введите корректную сумму цифрами (например, 100).');
    }

    const adminMsg = `💰 **ЗАЯВКА НА ПОПОЛНЕНИЕ**\n\n👤 Игрок: ${username}\n🆔 ID: ${userId}\n⭐ Сумма: ${amount} звезд`;
    
    const replyMarkup = {
      inline_keyboard: [[
        { text: '✅ Начислить', callback_data: `approve_dep_${userId}_${amount}` },
        { text: '❌ Отклонить', callback_data: `reject_dep_${userId}` }
      ]]
    };

    // 1. В чат
    try {
      await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
        parse_mode: 'Markdown',
        reply_markup: replyMarkup
      });
    } catch (e) { console.log("Ошибка чата:", e.message); }

    // 2. В ЛС
    try {
      await bot.telegram.sendMessage(ADMIN_IDS[0], adminMsg, {
        parse_mode: 'Markdown',
        reply_markup: replyMarkup
      });
    } catch (e) { console.log("Ошибка ЛС:", e.message); }

    ctx.reply(`✅ Заявка на ${amount} ⭐ создана!\n\n👉 Переведи ${amount} звезд на аккаунт @misurade.\nПосле перевода админ начислит тебе баланс.`);
    
    waitingForAmount.delete(userId);
    return;
  }

  ctx.reply('Нажми /start, чтобы открыть меню.');
});

// Кнопки
bot.action(/approve_dep_(\d+)_(\d+)/, async (ctx) => {
  const adminId = ctx.from.id.toString();
  const targetUserId = ctx.match[1];
  const amount = ctx.match[2];

  if (!ADMIN_IDS.includes(adminId)) {
    return ctx.answerCbQuery('У вас нет прав.', { show_alert: true });
  }

  ctx.answerCbQuery('Начислено!');
  ctx.editMessageText(`✅ Пополнение на ${amount} ⭐ для игрока ${targetUserId} ОДОБРЕНО.`);
  
  try { await bot.telegram.sendMessage(targetUserId, `✅ Ваше пополнение на ${amount} ⭐ одобрено!`); } catch (e) {}
});

bot.action(/reject_dep_(\d+)/, async (ctx) => {
  const adminId = ctx.from.id.toString();
  const targetUserId = ctx.match[1];

  if (!ADMIN_IDS.includes(adminId)) {
    return ctx.answerCbQuery('У вас нет прав.', { show_alert: true });
  }

  ctx.answerCbQuery('Отклонено!');
  ctx.editMessageText(`❌ Заявка на пополнение для игрока ${targetUserId} ОТКЛОНЕНА.`);
  
  try { await bot.telegram.sendMessage(targetUserId, `❌ Ваша заявка на пополнение отклонена.`); } catch (e) {}
});

// ===== ФИКС ОШИБКИ 409 (ЗАЩИТА ОТ ВЫЛЕТА) =====
bot.catch((err, ctx) => {
  if (err.message.includes('409')) {
    console.log('Ожидание закрытия старой сессии...');
  } else {
    console.error('Ошибка бота:', err.message);
  }
});

// Запускаем бота (без dropPendingUpdates, так как он иногда вызывает баг)
bot.launch().catch(err => {
  console.log('Ошибка при запуске, пробуем снова через 5 сек...');
  setTimeout(() => {
    bot.launch().catch(e => console.log('Повторная ошибка:', e.message));
  }, 5000);
});

// Чтобы Render не падал с ошибкой Exited 1
process.on('unhandledRejection', (reason) => {
  console.log('Отклоненный промис:', reason);
});
process.on('uncaughtException', (err) => {
  console.log('Необработанная ошибка:', err.message);
});

console.log('Бот запущен!');
