1780243233:jdmYR3YJAJCPYU5qNN7HLtwYHZXvrWvS57h
const { Telegraf } = require('telegraf');

const TOKEN = '1780243233:jdmYR3YJAJCPYU5qNN7HLtwYHZXvrWvS57h';
const API_ROOT = 'http://2.26.51.20:8088/bot';
const DROP_CHANCE = 0.001;

if (!TOKEN || TOKEN.startsWith('1780243233:jdmYR3YJAJCPYU5qNN7HLtwYHZXvrWvS57h')) {
  throw new Error('Укажи токен бота в начале файла');
}

const bot = new Telegraf(TOKEN, {
  telegram: { apiRoot: API_ROOT }
});

const participants = new Map();

function getParticipants(chatId) {
  if (!participants.has(chatId)) {
    participants.set(chatId, new Map());
  }

  return participants.get(chatId);
}

function choosePrize() {
  const roll = Math.random() * 100;

  if (roll < 5) return 'Чёрный фон';
  if (roll < 70) return 'Алмаз с росписью';
  return 'Случайный NFT';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[char]);
}

function mentionUser(user) {
  if (user.username) return `@${user.username}`;

  return `<a href="tg://user?id=${user.id}">${
    escapeHtml(user.firstName)
  }</a>`;
}

bot.start(async (ctx) => {
  try {
    await ctx.reply('Готов к работе.');
  } catch (error) {
    console.error('[START]', error.message);
  }
});

bot.on('text', async (ctx) => {
  try {
    const { chat, from, message } = ctx;

    if (!chat || !from || from.is_bot || !message) return;
    if (!['group', 'supergroup'].includes(chat.type)) return;

    if (/^\/start(?:@\w+)?(?:\s|$)/i.test(message.text)) return;

    const members = getParticipants(chat.id);

    members.set(from.id, {
      id: from.id,
      username: from.username || null,
      firstName: from.first_name || 'Участник'
    });

    if (Math.random() >= DROP_CHANCE) return;

    const users = Array.from(members.values());
    if (!users.length) return;

    const winner = users[
      Math.floor(Math.random() * users.length)
    ];

    const prize = choosePrize();

    await ctx.reply(
      `Поздравляем, ${mentionUser(winner)}! Вы выиграли приз: ` +
      `<b>${escapeHtml(prize)}</b>.`,
      { parse_mode: 'HTML' }
    );

    console.log(
      `[PRIZE] chat=${chat.id} winner=${winner.id} prize=${prize}`
    );
  } catch (error) {
    console.error('[MESSAGE]', error.message);
  }
});

bot.catch((error) => {
  console.error('[BOT ERROR]', error.message);
});

process.on('unhandledRejection', (error) => {
  console.error('[UNHANDLED REJECTION]', error);
});

let stopping = false;
let retryTimer;

async function startBot() {
  try {
    await bot.telegram.deleteWebhook({ drop_pending_updates: true });
    await bot.launch({ dropPendingUpdates: true });
    console.log('Бот запущен.');
  } catch (error) {
    console.error('[BOOT]', error.message);

    if (!stopping) {
      retryTimer = setTimeout(startBot, 5000);
    }
  }
}

function shutdown(signal) {
  if (stopping) return;
  stopping = true;

  if (retryTimer) clearTimeout(retryTimer);
  bot.stop(signal);
}

process.once('SIGINT', () => shutdown('SIGINT'));
process.once('SIGTERM', () => shutdown('SIGTERM'));

startBot();
