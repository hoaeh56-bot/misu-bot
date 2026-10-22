const { Telegraf } = require('telegraf');
const sqlite3 = require('sqlite3').verbose();

const bot = new Telegraf('1780243247:BLnX3Vx_8memKeCIAc1wldxkGl5mlAHFMAG', {
  telegram: { apiRoot: 'http://2.26.51.20:8088/bot' }
});

const ADMIN_USERNAME = 'GHOUL'; 
const SECRET_CODE = '1misugram200'; 
const HINT_TEXT = 'Подсказка: первые две буквы шифра — 1m'; 

// ===== БАЗА ДАННЫХ =====
const db = new sqlite3.Database('./contest.db');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS participants (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    is_winner INTEGER DEFAULT 0
  )`);
});

function registerUser(userId, username) {
  return new Promise((resolve) => {
    db.run(`INSERT OR IGNORE INTO participants (user_id, username) VALUES (?, ?)`, [userId, username], () => {
      resolve();
    });
  });
}

function getAllParticipants() {
  return new Promise((resolve, reject) => {
    db.all(`SELECT * FROM participants`, [], (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
}

// ===== ЛОГИКА =====
bot.start(async (ctx) => {
  const userId = ctx.from.id.toString();
  const username = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

  await registerUser(userId, username);

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
    db.get(`SELECT is_winner FROM participants WHERE user_id = ?`, [userId], async (err, row) => {
      if (row && row.is_winner === 1) {
        return ctx.reply('Вы уже победили ранее.');
      }

      db.run(`UPDATE participants SET is_winner = 1 WHERE user_id = ?`, [userId]);

      const winnerName = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;

      ctx.reply(`Поздравляю вас с победой! Напишите в лс создателю конкурса @${ADMIN_USERNAME}`);

      try {
        const participants = await getAllParticipants();
        
        for (const p of participants) {
          if (p.user_id !== userId) {
            try {
              await bot.telegram.sendMessage(p.user_id, `${winnerName} ПОБЕДИЛ В КОНКУРСЕ НА 3 ЧЕРНЫХ ФОНА. ПОЗДРАВЛЯЕМ!`);
            } catch (e) {
              // Игнорируем
            }
          }
        }
      } catch (e) {
        console.error('Ошибка рассылки:', e);
      }
    });
  } else {
    ctx.reply('Неправильный ответ');
  }
});

bot.launch();
console.log('Бот-конкурс запущен!');
