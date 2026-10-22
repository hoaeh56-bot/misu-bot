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

// Загрузка ивента (просто для сброса)
function loadEvent() {
  if (!fs.existsSync(EVENT_FILE)) return { totalPoints: 0 };
  try { return JSON.parse(fs.readFileSync(EVENT_FILE, 'utf8')); } catch (e) { return { totalPoints: 0 }; }
}
function saveEvent(data) { fs.writeFileSync(EVENT_FILE, JSON.stringify(data, null, 2)); }

const app = express();
app.use(cors()); 
app.use(express.json());

app.get('/api/get_balance/:userId', (req, res) => {
  const balances = loadBalances();
  const userId = req.params.userId;
  res.json({ balance: balances[userId] || 0 });
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

app.listen(process.env.PORT || 3000, () => console.log('Сервер для заявок запущен!'));

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

// Админ-панель
bot.action('admin_panel', (ctx) => {
  if (!ADMIN_IDS.includes(ctx.from.id.toString())) {
    return ctx.answerCbQuery('Нет прав', { show_alert: true });
  }
  ctx.editMessageText('🛠 Админ-панель\nВыберите действие:', {
    reply_markup: {
      inline_keyboard: [
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

bot.action('admin_reset_event', async (ctx) => {
  if (!ADMIN_IDS.includes(ctx.from.id.toString())) {
    return ctx.answerCbQuery('Нет прав', { show_alert: true });
  }
  saveEvent({ totalPoints: 0, leaderboard: [] });
  ctx.answerCbQuery('Ивент сброшен!');
  ctx.editMessageText('✅ Ивент успешно обнулен.');
});

// ... (продолжение логики пополнения и вывода как в прошлом файле)
