import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter

# ========================
# CONFIG
# ========================
TOKEN = "8731304294:AAGDNCUw228IWVS5N3Jcd0P_HnFhrJmesyU"
SHEET_NAME = "Rekap Infra RJW"

bot = telebot.TeleBot(TOKEN)

# ========================
# GOOGLE SHEETS CONNECT
# ========================
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)
client = gspread.authorize(creds)

data_sheet = client.open(SHEET_NAME).worksheet('Data')
teknisi_sheet = client.open(SHEET_NAME).worksheet('Teknisi')

# ========================
# STATE USER
# ========================
user_state = {}

# ========================
# PARSE TANGGAL
# ========================
def parse_tanggal(text):
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except:
            continue
    return None

# ========================
# MAP TEKNISI
# ========================
def get_teknisi_map():
    data = teknisi_sheet.get_all_records()
    mapping = {}
    for row in data:
        mapping[str(row['Labor Code'])] = row['Nama']
    return mapping

# ========================
# MENU
# ========================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton('📥 Input Tiket'))
    markup.row(KeyboardButton('📊 Laporan'), KeyboardButton('👨‍🔧 Teknisi'))
    markup.row(KeyboardButton('❓ Help'))
    return markup

# ========================
# START
# ========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Halo 👋 Bot siap digunakan', reply_markup=main_menu())

# ========================
# MENU HANDLER
# ========================
@bot.message_handler(func=lambda m: m.text == '📥 Input Tiket')
def menu_input(message):
    user_state[message.chat.id] = {}
    bot.send_message(message.chat.id, 'Masukkan No Tiket (contoh: INC12345678)')

@bot.message_handler(func=lambda m: m.text == '📊 Laporan')
def menu_laporan(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📅 Hari Ini', '📆 Bulan Ini')
    markup.row('⬅️ Kembali')
    bot.send_message(message.chat.id, 'Pilih laporan:', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '👨‍🔧 Teknisi')
def menu_teknisi(message):
    data = teknisi_sheet.get_all_records()
    text = '📋 Daftar Teknisi:\n\n'
    for row in data:
        text += f"{row['Labor Code']} - {row['Nama']}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '❓ Help')
def help_menu(message):
    bot.send_message(message.chat.id,
'''📌 Format input cepat:
INC12345678 20991234

Pastikan:
- Tiket diawali INC
- Labor code 8 digit angka''')

@bot.message_handler(func=lambda m: m.text == '⬅️ Kembali')
def kembali(message):
    bot.send_message(message.chat.id, 'Menu utama', reply_markup=main_menu())

# ========================
# INPUT STEP 1
# ========================
@bot.message_handler(func=lambda m: m.chat.id in user_state and 'tiket' not in user_state[m.chat.id])
def input_tiket(message):
    tiket = message.text.upper()

    if not tiket.startswith('INC') or len(tiket) < 10:
        bot.reply_to(message, '❌ Format tiket salah (contoh: INC12345678)')
        return

    user_state[message.chat.id]['tiket'] = tiket
    show_teknisi(message.chat.id)

# ========================
# SHOW TEKNISI
# ========================
def show_teknisi(chat_id):
    data = teknisi_sheet.get_all_records()

    markup = InlineKeyboardMarkup()

    for row in data:
        kode = str(row['Labor Code'])
        nama = row['Nama']
        markup.add(InlineKeyboardButton(nama, callback_data=f'tek_{kode}'))

    bot.send_message(chat_id, 'Pilih Teknisi:', reply_markup=markup)

# ========================
# PILIH TEKNISI
# ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith('tek_'))
def pilih_teknisi(call):
    labor_code = call.data.split('_')[1]
    tiket = user_state[call.message.chat.id]['tiket']

    user = call.from_user.username or call.from_user.first_name
    now = datetime.now()

    data = data_sheet.get_all_records()
    existing = [row['No Tiket'] for row in data]

    if tiket in existing:
        bot.send_message(call.message.chat.id, '⚠️ Tiket sudah ada')
        return

    data_sheet.append_row([
        str(now),
        user,
        tiket,
        labor_code
    ])

    bot.send_message(call.message.chat.id, '✅ Data berhasil disimpan', reply_markup=main_menu())
    del user_state[call.message.chat.id]

# ========================
# LAPORAN HARIAN
# ========================
@bot.message_handler(func=lambda m: m.text == '📅 Hari Ini')
def laporan_harian(message):
    data = data_sheet.get_all_records()
    today = datetime.now().date()

    users = []
    teknisi = []

    for row in data:
        tgl = parse_tanggal(row['Timestamp'])
        if not tgl:
            continue

        if tgl.date() == today:
            users.append(row['User'])
            teknisi.append(str(row['Labor Code']))

    if not users:
        bot.reply_to(message, 'Belum ada data hari ini.')
        return

    teknisi_map = get_teknisi_map()
    u_count = Counter(users)
    t_count = Counter(teknisi)

    text = '📊 Laporan Hari Ini\n\n'

    text += '👤 Per User:\n'
    for u, c in u_count.items():
        text += f'- {u}: {c}\n'

    text += '\n🛠 Teknisi Terbanyak:\n'
    for i, (kode, jumlah) in enumerate(t_count.most_common(), start=1):
        nama = teknisi_map.get(kode, 'Tidak diketahui')
        text += f'{i}. {nama} ({kode}) → {jumlah} tiket\n'

    bot.send_message(message.chat.id, text)

# ========================
# LAPORAN BULANAN
# ========================
@bot.message_handler(func=lambda m: m.text == '📆 Bulan Ini')
def laporan_bulanan(message):
    data = data_sheet.get_all_records()
    now = datetime.now()

    users = []
    teknisi = []

    for row in data:
        tgl = parse_tanggal(row['Timestamp'])
        if not tgl:
            continue

        if tgl.month == now.month and tgl.year == now.year:
            users.append(row['User'])
            teknisi.append(str(row['Labor Code']))

    if not users:
        bot.reply_to(message, 'Belum ada data bulan ini.')
        return

    teknisi_map = get_teknisi_map()
    u_count = Counter(users)
    t_count = Counter(teknisi)

    text = f'📊 Laporan Bulan {now.strftime("%B %Y")}\n\n'

    text += '👤 Per User:\n'
    for u, c in u_count.items():
        text += f'- {u}: {c}\n'

    text += '\n🛠 Teknisi Terbanyak:\n'
    for i, (kode, jumlah) in enumerate(t_count.most_common(), start=1):
        nama = teknisi_map.get(kode, 'Tidak diketahui')
        text += f'{i}. {nama} ({kode}) → {jumlah} tiket\n'

    bot.send_message(message.chat.id, text)

# ========================
# AUTO INPUT (STRICT FILTER)
# ========================
@bot.message_handler(func=lambda m: True)
def auto_input(message):
    try:
        text = message.text.strip()
        parts = text.split()

        # hanya format 2 bagian
        if len(parts) != 2:
            return

        tiket = parts[0].upper()
        labor = parts[1]

        # validasi tiket
        if not tiket.startswith('INC') or len(tiket) < 10:
            bot.reply_to(message, '❌ Format tiket salah (INCxxxxxx)')
            return

        # validasi labor code
        if not labor.isdigit() or len(labor) != 8:
            bot.reply_to(message, '❌ Labor code harus 8 digit angka')
            return

        user = message.from_user.username or message.from_user.first_name
        now = datetime.now()

        data = data_sheet.get_all_records()
        existing = [row['No Tiket'] for row in data]

        if tiket in existing:
            bot.reply_to(message, '⚠️ Tiket sudah ada')
            return

        data_sheet.append_row([
            str(now),
            user,
            tiket,
            labor
        ])

        bot.reply_to(message, '✅ Data tersimpan')

    except:
        pass

# ========================
# RUN
# ========================
print('Bot running...')
bot.infinity_polling()
