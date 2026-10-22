const { Telegraf } = require('telegraf');
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const bot = new Telegraf('1780243237:1w2CHS4zqtHz5dJ5QJEBdwHKTNEwjWPiUQY', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_CHAT_ID = '-100243'; 
const ADMIN_IDS = ['1780243206']; 
const SITE_URL = 'https://misu-site.vercel.app/'; 

const BALANCE_FILE = path.join(__dirname, 'balances.json');
const EVENT_FILE = path.join(__dirname, 'event.json');

// Загрузка/сохранение балансов
function loadBalances() {
  if (!fs.existsSync(BALANCE_FILE)) return {};
  try { return JSON.parse(fs.readFileSync(BALANCE_FILE, 'utf8')); } catch (e) { return {}; }
}
function saveBalances(data) { fs.writeFileSync(BALANCE_FILE, JSON.stringify(data, null, 2)); }
function addBalance(userId, amount) {
  const balances = loadBalances();
  if (!balances[userId]) balances[userId] = 0;
  balances[userId] += amount;
  saveBalances(balances);
}
function resetAllBalances() {
  saveBalances({});
}

// Загрузка/сохранение ивента
function loadEvent() {
  if (!fs.existsSync(EVENT_FILE)) return { totalPoints: 0 };
  try { return JSON.parse(fs.readFileSync(EVENT_FILE, 'utf8')); } catch (e) { return { totalPoints: 0 }; }
}
function saveEvent(data) { fs.writeFileSync(EVENT_FILE, JSON.stringify(data, null, 2)); }

// ===== ВЕБ-СЕРВЕР =====
const app = express();
app.use(cors()); 
app.use(express.json());

app.get('/api/get_balance/:userId', (req, res) => {
  const balances = loadBalances();
  const userId = req.params.userId;
  res.json({ balance: balances[userId] || 0 });
});

app.post('/api/admin/reset_all', async (req, res) => {
  resetAllBalances();
  try { fs.unlinkSync(EVENT_FILE); } catch(e) {}
  res.status(200).send('OK');
});

app.post('/api/withdraw', async (req, res) => {
  try {
    const { userId, userName, itemName, itemPrice } = req.body;
    const adminMsg = `📥 **ЗАЯВКА НА ВЫВОД**\n\n👤 Игрок: ${userName}\n🆔 ID: ${userId}\n🎁 Подарок: ${itemName}\n💰 Стоимость: ${itemPrice} ⭐`;
    
    const replyMarkup = {
      inline_keyboard: [[
        { text: '✅ Выдать', callback_data: `approve_wd_${userId}` },
        { text: '❌ Отклонить', callback_data: `reject_wd_${userId}` }
      ]]
    };

    try { await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, { parse_mode: 'Markdown', reply_markup: replyMarkup }); } catch (e) {}
    try { await bot.telegram.sendMessage(ADMIN_IDS[0], adminMsg, { parse_mode: 'Markdown', reply_markup: replyMarkup }); } catch (e) {}
    
    res.status(200).send('OK');
  } catch (e) {
    res.status(500).send('Error');
  }
});

app.listen(process.env.PORT || 3000, () => {
  console.log('✅ Сервер для заявок запущен!');
  startBot();
});

// ===== УМНЫЙ ЗАПУСК БОТА =====
async function startBot() {
  try {
    await bot.telegram.deleteWebhook({ drop_pending_updates: true });
    await bot.launch({ dropPendingUpdates: true });
    console.log('✅ Бот запущен!');
  } catch (err) {
    console.log(`⚠️ Ошибка при запуске: ${err.message}. Перезапуск через 5 секунд...`);
    setTimeout(startBot, 5000);
  }
}

// ===== ЛОГИКА БОТА =====
const waitingForAmount = new Set();

bot.start((ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  const gameUrl = `${SITE_URL}?tg_id=${userId}&name=${encodeURIComponent(username)}`;

  const isAdmin = ADMIN_IDS.includes(userId);
  
  const keyboard = [
    [{ text: '🎮 Открыть игру', web_app: { url: gameUrl } }],
    [{ text: '💰 Пополнить баланс', callback_data: 'deposit_start' }]
  ];

  if (isAdmin) {
    keyboard.push([{ text: '🛠 Админ-панель', callback_data: 'admin_panel' }]);
  }

  ctx.reply(`Добро пожаловать, ${username}!\nТвой ID: ${userId}\n\nВыбери действие:`, {
    reply_markup: { inline_keyboard: keyboard }
  });
});

bot.action('deposit_start', (ctx) => {
  ctx.answerCbQuery();
  waitingForAmount.add(ctx.from.id);
  ctx.reply('Введите сумму в звездах (только цифры, например: 100):');
});

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

    try { await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, { parse_mode: 'Markdown', reply_markup: replyMarkup }); } catch (e) {}
    try { await bot.telegram.sendMessage(ADMIN_IDS[0], adminMsg, { parse_mode: 'Markdown', reply_markup: replyMarkup }); } catch (e) {}

    ctx.reply(`✅ Заявка на ${amount} ⭐ создана!\n\n👉 Переведи ${amount} звезд на аккаунт @misurade.\nПосле перевода админ начислит тебе баланс.`);
    waitingForAmount.delete(userId);
    return;
  }
  ctx.reply('Нажми /start, чтобы открыть меню.');
});

// ===== НАЧИСЛЕНИЕ =====
bot.action(/approve_dep_(\d+)_(\d+)/, async (ctx) => {
  const adminId = ctx.from.id.toString();
  const targetUserId = ctx.match[1];
  const amount = parseInt(ctx.match[2]);

  if (!ADMIN_IDS.includes(adminId)) {
    return ctx.answerCbQuery('У вас нет прав.', { show_alert: true });
  }

  addBalance(targetUserId, amount);

  ctx.answerCbQuery('Начислено!');
  ctx.editMessageText(`✅ Пополнение на ${amount} ⭐ для игрока ${targetUserId} ОДОБРЕНО.`);
  
  try { await bot.telegram.sendMessage(targetUserId, `✅ Ваше пополнение на ${amount} ⭐ одобрено! Перезайдите в игру.`); } catch (e) {}
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

// ===== ВЫВОД =====
bot.action(/approve_wd_(\d+)/, async (ctx) => {
  const adminId = ctx.from.id.toString();
  const targetUserId = ctx.match[1];

  if (!ADMIN_IDS.includes(adminId)) {
    return ctx.answerCbQuery('У вас нет прав.', { show_alert: true });
  }

  ctx.answerCbQuery('Выдано!');
  ctx.editMessageText(`✅ Вывод для игрока ${targetUserId} ОДОБРЕН.`);
  try { await bot.telegram.sendMessage(targetUserId, `✅ Ваша заявка на вывод одобрена!`); } catch (e) {}
});

bot.action(/reject_wd_(\d+)/, async (ctx) => {
  const adminId = ctx.from.id.toString();
  const targetUserId = ctx.match[1];

  if (!ADMIN_IDS.includes(adminId)) {
    return ctx.answerCbQuery('У вас нет прав.', { show_alert: true });
  }

  ctx.answerCbQuery('Отклонено!');
  ctx.editMessageText(`❌ Заявка на вывод для игрока ${targetUserId} ОТКЛОНЕНА.`);
  try { await bot.telegram.sendMessage(targetUserId, `❌ Ваша заявка на вывод отклонена.`); } catch (e) {}
});

// ===== АДМИН-ПАНЕЛЬ =====
bot.action('admin_panel', (ctx) => {
  if (!ADMIN_IDS.includes(ctx.from.id.toString())) {
    return ctx.answerCbQuery('Нет прав', { show_alert: true });
  }
  ctx.editMessageText('🛠 Админ-панель\nВыберите действие:', {
    reply_markup: {
      inline_keyboard: [
        [{ text: '💸 Обнулить всем звёзды', callback_data: 'admin_reset_balances' }],
        [{ text: '🔄 Обнулить ивент (Сброс)', callback_data: 'admin_reset_event' }],
        [{ text: '🔙 Назад', callback_data: 'admin_back' }]
      ]
    }
  });
});

bot.action('admin_back', (ctx) => {
  if (!ADMIN_IDS.includes(ctx.from.id.toString())) return;
  bot.start(ctx);
});

// ОБНУЛЕНИЕ БАЛАНСОВ
bot.action('admin_reset_balances', async (ctx) => {
  if (!ADMIN_IDS.includes(ctx.from.id.toString())) {
    return ctx.answerCbQuery('Нет прав', { show_alert: true });
  }
  resetAllBalances();
  ctx.answerCbQuery('Балансы обнулены!');
  ctx.editMessageText('✅ Все балансы игроков обнулены до 0 ⭐.');
});

// ОБНУЛЕНИЕ ИВЕНТА
bot.action('admin_reset_event', async (ctx) => {
  if (!ADMIN_IDS.includes(ctx.from.id.toString())) {
    return ctx.answerCbQuery('Нет прав', { show_alert: true });
  }
  saveEvent({ totalPoints: 0, leaderboard: [] });
  ctx.answerCbQuery('Ивент сброшен!');
  ctx.editMessageText('✅ Ивент успешно обнулен.');
});
