const { Telegraf } = require('telegraf');
const fs = require('fs');
const path = require('path');
const express = require('express'); // Добавляем Express для приема запросов с сайта
const bodyParser = require('body-parser');

const bot = new Telegraf('1780243237:aJtE4dMAq83AqeqH5OtQAdRqKcpB6yHJwTw', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_CHAT_ID = '-100243'; 
const SITE_URL = 'https://misu-site.vercel.app/'; 

// ===== СЕРВЕР ДЛЯ ПРИЕМА ЗАЯВОК С САЙТА =====
const app = express();
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.json());

// Прием пополнения
app.post('/api/deposit', async (req, res) => {
  try {
    const data = JSON.parse(req.body.data);
    const adminMsg = `💰 **ЗАЯВКА НА ПОПОЛНЕНИЕ**\n\n👤 Игрок: ${data.userName}\n🆔 ID: ${data.userId}\n⭐ Сумма: ${data.amount} звезд`;

    await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [[
          { text: '✅ Начислить', callback_data: `approve_dep_${data.userId}_${data.amount}` },
          { text: '❌ Отклонить', callback_data: `reject_dep_${data.userId}` }
        ]]
      }
    });
    res.status(200).send('OK');
  } catch (e) {
    console.error(e);
    res.status(500).send('Error');
  }
});

// Прием вывода
app.post('/api/withdraw', async (req, res) => {
  try {
    const data = JSON.parse(req.body.data);
    const adminMsg = `📥 **НОВАЯ ЗАЯВКА НА ВЫВОД**\n\n👤 Игрок: ${data.userName}\n🆔 ID: ${data.userId}\n🎁 Подарок: ${data.itemName}\n💰 Стоимость: ${data.itemPrice} ⭐`;

    await bot.telegram.sendMessage(ADMIN_CHAT_ID, adminMsg, {
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [[
          { text: '✅ Выдать', callback_data: `approve_wd_${data.userId}` },
          { text: '❌ Отклонить', callback_data: `reject_wd_${data.userId}` }
        ]]
      }
    });
    res.status(200).send('OK');
  } catch (e) {
    console.error(e);
    res.status(500).send('Error');
  }
});

app.listen(process.env.PORT || 3000, () => {
  console.log('Сервер для заявок запущен!');
});

// ===== ЛОГИКА БОТА =====
bot.start(async (ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
  
  // Получаем аватарку (если есть)
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

// Обработка кнопок подтверждения
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
