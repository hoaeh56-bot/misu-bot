const { Telegraf } = require('telegraf');
const express = require('express');
const cors = require('cors');

const bot = new Telegraf('1780243237:1w2CHS4zqtHz5dJ5QJEBdwHKTNEwjWPiUQY', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_CHAT_ID = '-100243'; 
const SITE_URL = 'https://misu-site.vercel.app/'; 

// ===== СЕРВЕР =====
const app = express();
app.use(cors()); 
app.use(express.json());

app.post('/api/deposit', async (req, res) => {
  try {
    const { userId, userName, amount } = req.body;
    const adminMsg = `💰 **ЗАЯВКА НА ПОПОЛНЕНИЕ**\n\n👤 Игрок: ${userName}\n🆔 ID: ${userId}\n⭐ Сумма: ${amount} звезд`;

    await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [[
          { text: '✅ Начислить', callback_data: `approve_dep_${userId}_${amount}` },
          { text: '❌ Отклонить', callback_data: `reject_dep_${userId}` }
        ]]
      }
    });
    res.status(200).send('OK');
  } catch (e) {
    res.status(500).send('Error');
  }
});

app.post('/api/withdraw', async (req, res) => {
  try {
    const { userId, userName, itemName, itemPrice } = req.body;
    const adminMsg = `📥 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n\n👤 Игрок: ${userName}\n🆔 ID: ${userId}\n🎁 Подарок: ${itemName}\n💰 Стоимость: ${itemPrice} ⭐`;

    await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [[
          { text: '✅ Выдать', callback_data: `approve_wd_${userId}` },
          { text: '❌ Отклонить', callback_data: `reject_wd_${userId}` }
        ]]
      }
    });
    res.status(200).send('OK');
  } catch (e) {
    res.status(500).send('Error');
  }
});

// Запускаем сервер, а затем бота
const server = app.listen(process.env.PORT || 3000, () => {
  console.log('Сервер для заявок запущен!');
  
  // Небольшая задержка перед запуском бота, чтобы Render не дублировал процесс
  setTimeout(() => {
    bot.launch({ dropPendingUpdates: true }).then(() => {
      console.log('Бот запущен!');
    }).catch(err => {
      console.error('Ошибка запуска бота:', err.message);
    });
  }, 3000); // Ждем 3 секунды
});

// ===== ЛОГИКА БОТА =====
bot.start(async (ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  
  let avatarUrl = "https://via.placeholder.com/40";
  try {
    const photos = await ctx.telegram.getUserProfilePhotos(userId, 0, 1);
    if (photos.total_count > 0) {
      const fileId = photos.photos[0][0].file_id;
      const fileLink = await ctx.telegram.getFileLink(fileId);
      avatarUrl = fileLink.href;
    }
  } catch (e) {}

  const gameUrl = `${SITE_URL}?tg_id=${userId}&name=${encodeURIComponent(username)}&avatar=${encodeURIComponent(avatarUrl)}`;

  ctx.reply(`Добро пожаловать, ${username}!\nТвой ID: ${userId}\n\nНажми кнопку ниже, чтобы играть.`, {
    reply_markup: {
      inline_keyboard: [[ { text: '🎮 Открыть игру', web_app: { url: gameUrl } } ]]
    }
  });
});

// Обработка кнопок
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
