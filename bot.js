const { Telegraf } = require('telegraf');
const fs = require('fs');
const path = require('path');

const bot = new Telegraf('1780243247:BLnX3Vx_8memKeCIAc1wldxkGl5mlAHFMAG', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_USERNAME = 'GHOUL'; 
const SECRET_CODE = '1misugram200'; 
const HINT_TEXT = 'Подсказка: первые две буквы шифра — 1m'; 

// Файл для хранения участников (вместо базы данных)
const DB_FILE = path.join(__dirname, 'participants.json');

// Загрузка списка участников
function loadParticipants() {
  if (!fs.existsSync(DB_FILE)) {
    return {};
  }
  try {
    const data = fs.readFileSync(DB_FILE, 'utf8');
    return JSON.parse(data);
  } catch (e) {
    return {};
  }
}

// Сохранение списка участников
function saveParticipants(participants) {
  fs.writeFileSync(DB_FILE, JSON.stringify(participants, null, 2));
}

// ===== ЛОГИКА =====
bot.start(async (ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

  // Регистрируем юзера
  let participants = loadParticipants();
  if (!participants[userId]) {
    participants[userId] = { username: username, is_winner: false };
    saveParticipants(participants);
  }

  ctx.reply(`Вы приняли участие в разгадывании шифра.\nПриз: 3 черных фона в misugram.\n\nУ вас есть возможность взять только одну подсказку.`, {
    reply_markup: {
      inline_keyboard: [
        [{ text: 'Взять подсказку', callback_data: 'get_hint' }],
        [{ text: 'Начать разгадывать шифр', callback_data: 'start_guess' }]
      ]
    }
  });
});

bot.action('get_hint', async (ctx) => {
  ctx.answerCbQuery();
  ctx.reply(HINT_TEXT, {
    reply_markup: {
      inline_keyboard: [
        [{ text: 'Начать разгадывать шифр', callback_data: 'start_guess' }]
      ]
    }
  });
});

bot.action('start_guess', async (ctx) => {
  ctx.answerCbQuery();
  ctx.reply('Впишите шифр:');
});

// Ловим ввод текста
bot.on('text', async (ctx) => {
  const text = ctx.message.text.trim();
  const userId = ctx.from.id.toString();

  if (text === '/start') return;

  if (text === SECRET_CODE) {
    let participants = loadParticipants();

    // Проверка, не выиграл ли уже
    if (participants[userId] && participants[userId].is_winner) {
      return ctx.reply('Вы уже победили ранее.');
    }

    // Записываем победу
    if (participants[userId]) {
      participants[userId].is_winner = true;
      saveParticipants(participants);
    }

    const winnerName = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

    ctx.reply(`Поздравляю вас с победой! Напишите в лс создателю конкурса @${ADMIN_USERNAME}`);

    // Раccылка всем участникам
    try {
      const allUsers = Object.keys(participants);
      
      for (const uid of allUsers) {
        if (uid !== userId) {
          try {
            await bot.telegram.sendMessage(uid, `${winnerName} ПОБЕДИЛ В КОНКУРСЕ НА 3 ЧЕРНЫХ ФОНА. ПОЗДРАВЛЯЕМ!`);
          } catch (e) {
            // Пропускаем, если заблокировал
          }
        }
      }
    } catch (e) {
      console.error('Ошибка рассылки:', e);
    }
  } else {
    ctx.reply('Неправильный ответ');
  }
});

bot.launch();
console.log('Бот-конкурс запущен!');
