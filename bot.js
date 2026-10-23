const { Telegraf } = require('telegraf');

const TOKEN = process.env.BOT_TOKEN;
const API_ROOT =
  process.env.MISUGRAM_API_ROOT || 'http://2.26.51.20:8088/bot';

const DROP_CHANCE = Number(
  process.env.PRIZE_DROP_CHANCE || '0.001'
);

if (!TOKEN) {
  throw new Error('Добавь BOT_TOKEN в Environment на Render');
}

if (
  !Number.isFinite(DROP_CHANCE) ||
  DROP_CHANCE < 0 ||
  DROP_CHANCE > 1
) {
  throw new Error('PRIZE_DROP_CHANCE должен быть от 0 до 1');
}

const bot = new Telegraf(TOKEN, {
  telegram: {
    apiRoot: API_ROOT
  }
});

// Участники каждого чата
const participants = new Map();

const PRIZES = [
  { name: 'Чёрный фон', chance: 5 },
  { name: 'Алмаз с росписью', chance: 65 },
  { name: 'Случайный NFT', chance: 30 }
];

function choosePrize() {
  const roll = Math.random() * 100;
  let cumulative = 0;

  for (const prize of PRIZES) {
    cumulative += prize.chance;

    if (roll < cumulative) {
      return prize.name;
    }
  }

  return PRIZES[PRIZES.length - 1].name;
}

function getChatParticipants(chatId) {
  if (!participants.has(chatId)) {
    participants.set(chatId, new Map());
  }

  return participants.get(chatId);
}

// Команда запуска
bot.start(async (ctx) => {
  await ctx.reply('Готов к работе.');
});

// Обработка сообщений участников
bot.on('text', async (ctx) => {
  try {
    const chat = ctx.chat;
    const user = ctx.from;

    if (!chat || !user || user.is_bot) return;

    // Розыгрыш только в группах
    if (chat.type !== 'group' && chat.type !== 'supergroup') {
      return;
    }

    const chatUsers = getChatParticipants(chat.id);

    // Запоминаем пользователя по ID
    chatUsers.set(user.id, {
      id: user.id,
      username: user.username || null,
      first_name: user.first_name || 'Участник'
    });

    // Проверяем случайный шанс выпадения
    if (Math.random() >= DROP_CHANCE) return;

    const users = Array.from(chatUsers.values());

    if (users.length === 0) return;

    // Случайный победитель
    const winner = users[
      Math.floor(Math.random() * users.length)
    ];

    // Случайный приз
    const prize = choosePrize();

    const mention = winner.username
      ? `@${winner.username}`
      : winner.first_name;

    await ctx.reply(
      `Поздравляем, ${mention}! Вы выиграли приз: ${prize}.`
    );

    console.log(
      `Чат: ${chat.id}; победитель: ${winner.id}; приз: ${prize}`
    );
  } catch (error) {
    console.error(
      'Ошибка обработки сообщения:',
      error.message
    );
  }
});

bot.catch((error) => {
  console.error('Ошибка бота:', error.message);
});

bot.launch()
  .then(() => console.log('Бот запущен'))
  .catch((error) => {
    console.error(
      'Не удалось запустить бота:',
      error.message
    );
    process.exitCode = 1;
  });

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
