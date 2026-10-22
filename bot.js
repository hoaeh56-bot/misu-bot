const { Telegraf } = require('telegraf');
const express = require('express');
const cors = require('cors');

const bot = new Telegraf('1780243237:1w2CHS4zqtHz5dJ5QJEBdwHKTNEwjWPiUQY', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_CHAT_ID = '-100243'; 
const SITE_URL = 'https://misu-site.vercel.app/'; 

// Сервер для сайта (чтобы не падал Render)
const app = express();
app.use(cors()); 
app.use(express.json());
app.listen(process.env.PORT || 3000, () => console.log('Сервер запущен!'));

// Переменная для ожидания ввода суммы
const waitingForAmount = new Set();

// ===== СТАРТ =====
bot.start((ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  
  // Ссылка на игру с ID игрока
  const gameUrl = `${SITE_URL}?tg_id=${userId}&name=${encodeURIComponent(username)}`;

  ctx.reply(`Добро пожаловать, ${username}!\nТвой ID: ${userId}\n\nВыбери действие:`, {
    reply_markup: {
      inline_keyboard: [
        [{ text: '🎮 Открыть игру', web_app: { url: gameUrl } }],
        [{ text: '💰 Пополнить баланс', callback_data: 'deposit_start' }]
      ]
    }
  });
});

// ===== КНОПКА ПОПОЛНЕНИЯ =====
bot.action('deposit_start', (ctx) => {
  ctx.answerCbQuery();
  waitingForAmount.add(ctx.from.id);
  ctx.reply('Введите сумму в звездах (только цифры, например: 100):');
});

// ===== ЛОВИМ СУММУ =====
bot.on('text', async (ctx) => {
  const userId = ctx.from.id;
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  const text = ctx.message.text.trim();

  if (text === '/start') return;

  // Если игрок в режиме ожидания суммы
  if (waitingForAmount.has(userId)) {
    const amount = parseInt(text);
    
    if (isNaN(amount) || amount < 1) {
      return ctx.reply('Пожалуйста, введите корректную сумму цифрами (например, 100).');
    }

    // Отправляем уведомление тебе
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
    } catch (e) {
      console.log("Ошибка отправки админу:", e.message);
    }

    // Инструкция игроку
    ctx.reply(`✅ Заявка на ${amount} ⭐ создана!\n\n👉 Переведи ${amount} звезд на аккаунт @misurade.\nПосле перевода админ начислит тебе баланс.`);
    
    waitingForAmount.delete(userId);
    return;
  }

  // Если просто пишет текст
  ctx.reply('Нажми /start, чтобы открыть меню.');
});

// ===== ОБРАБОТКА КНОПОК АДМИНА =====
bot.action(/approve_dep_(\d+)_(\d+)/, async (ctx) => {
  const targetUserId = ctx.match[1];
  const amount = ctx.match[2];
  
  ctx.answerCbQuery('Начислено!');
  ctx.editMessageText(`✅ Пополнение на ${amount} ⭐ для игрока ${targetUserId} ОДОБРЕНО.`);
  
  try { 
    await bot.telegram.sendMessage(targetUserId, `✅ Ваше пополнение на ${amount} ⭐ одобрено! Баланс пополнен.`); 
  } catch (e) {}
});

bot.action(/reject_dep_(\d+)/, async (ctx) => {
  const targetUserId = ctx.match[1];
  
  ctx.answerCbQuery('Отклонено!');
  ctx.editMessageText(`❌ Заявка на пополнение для игрока ${targetUserId} ОТКЛОНЕНА.`);
  
  try { 
    await bot.telegram.sendMessage(targetUserId, `❌ Ваша заявка на пополнение отклонена.`); 
  } catch (e) {}
});

// Запуск бота
bot.launch();
console.log('Бот запущен!');
