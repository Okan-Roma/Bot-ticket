import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter

# ========================
# PARSE TANGGAL
# ========================

def parse_tanggal(text):
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except:
            continue

    return None

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
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

data_sheet = client.open(SHEET_NAME).worksheet("Data")
teknisi_sheet = client.open(SHEET_NAME).worksheet("Teknisi")

# ========================
# STATE USER
# ========================
user_state = {}

# ========================
# MENU UTAMA
# ========================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📥 Input Tiket"))
    markup.row(KeyboardButton("📊 Laporan"), KeyboardButton("👨‍🔧 Teknisi"))
    markup.row(KeyboardButton("❓ Help"))
    return markup

# ========================
# START
# ========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "Halo 👋\nBot Rekap Tiket siap digunakan.",
        reply_markup=main_menu()
    )


# ========================
# MENU HANDLER
# ========================
@bot.message_handler(func=lambda m: m.text == "📥 Input Tiket")
def menu_input(message):
    user_state[message.chat.id] = {}
    bot.send_message(message.chat.id, "Masukkan No Tiket (contoh: INC12345678)")

@bot.message_handler(func=lambda m: m.text == "📊 Laporan")
def menu_laporan(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📅 Hari Ini", "📆 Bulan Ini")
    markup.row("⬅️ Kembali")
    bot.send_message(message.chat.id, "Pilih laporan:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👨‍🔧 Teknisi")
def menu_teknisi(message):
    data = teknisi_sheet.get_all_records()
    text = "📋 Daftar Teknisi:\n\n"
    for row in data:
        text += f"{row['Labor Code']} - {row['Nama']}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def menu_help(message):
    bot.send_message(message.chat.id,
"""
📌 Cara pakai:

✅ Input cepat:
INC12345678 20991234

✅ Menu:
Gunakan tombol untuk input & laporan
""")

@bot.message_handler(func=lambda m: m.text == "⬅️ Kembali")
def kembali(message):
    bot.send_message(message.chat.id, "Menu utama", reply_markup=main_menu())

# ========================
# INPUT FLOW (STEP 1)
# ========================
@bot.message_handler(func=lambda m: m.chat.id in user_state and 'tiket' not in user_state[m.chat.id])
def input_tiket(message):
    tiket = message.text.upper()

    if not tiket.startswith("INC"):
        bot.reply_to(message, "Format tiket harus INC12345678")
        return

    user_state[message.chat.id]['tiket'] = tiket

    # tampilkan teknisi
    show_teknisi(message.chat.id)

# ========================
# TAMPIL TEKNISI (AUTO COMPLETE)
# ========================
def show_teknisi(chat_id):
    data = teknisi_sheet.get_all_records()

    markup = InlineKeyboardMarkup()

    for row in data:
        kode = str(row['Labor Code'])
        nama = row['Nama']
        markup.add(InlineKeyboardButton(nama, callback_data=f"tek_{kode}"))

    bot.send_message(chat_id, "Pilih Teknisi:", reply_markup=markup)

# ========================
# PILIH TEKNISI
# ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("tek_"))
def pilih_teknisi(call):
    labor_code = call.data.split("_")[1]
    tiket = user_state[call.message.chat.id]['tiket']

    user = call.from_user.username or call.from_user.first_name
    now = datetime.now()

    # cek duplikat
    data = data_sheet.get_all_records()
    existing = [row['No Tiket'] for row in data]

    if tiket in existing:
        bot.send_message(call.message.chat.id, "⚠️ Tiket sudah ada")
        return

    data_sheet.append_row([
        str(now),
        user,
        tiket,
        labor_code
    ])

    bot.send_message(call.message.chat.id, "✅ Data berhasil disimpan", reply_markup=main_menu())
    del user_state[call.message.chat.id]

# ========================
# AUTO INPUT CEPAT
# ========================
@bot.message_handler(func=lambda m: True)
def auto_input(message):
    try:
        parts = message.text.split()

        if len(parts) != 2:
            return

        tiket = parts[0].upper()
        labor = parts[1]

        if not tiket.startswith("INC"):
            return

        if not labor.isdigit():
            return

        user = message.from_user.username or message.from_user.first_name
        now = datetime.now()

        data = data_sheet.get_all_records()
        existing = [row['No Tiket'] for row in data]

        if tiket in existing:
            bot.reply_to(message, "⚠️ Tiket sudah ada")
            return

        data_sheet.append_row([
            str(now),
            user,
            tiket,
            labor
        ])

        bot.reply_to(message, "✅ Data tersimpan")

    except:
        pass

# ========================
# LAPORAN HARIAN
# ========================
from collections import Counter

@bot.message_handler(func=lambda m: "Hari Ini" in m.text)
def laporan_harian(message):
    data = sheet.get_all_records()

    today = datetime.now().date()
    users = []
    teknisi = []

    for row in data:
        try:
            tgl = datetime.strptime(row['Timestamp'], "%Y-%m-%d %H:%M:%S.%f").date()
        except:
            continue

        if tgl == today:
            users.append(row['User'])
            teknisi.append(row['Labor Code'])

    if not users:
        bot.reply_to(message, "Belum ada data hari ini")
        return

    user_count = Counter(users)
    teknisi_count = Counter(teknisi)

    text = "📊 Laporan Hari Ini\n\n👤 User:\n"

    for u, c in user_count.items():
        text += f"- {u}: {c}\n"

    text += "\n🛠 Teknisi:\n"

    for t, c in teknisi_count.most_common():
        text += f"- {t}: {c}\n"

    bot.send_message(message.chat.id, text)



# ========================
# LAPORAN BULANAN
# ========================
@bot.message_handler(func=lambda m: "Bulan Ini" in m.text)
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
            teknisi.append(row['Labor Code'])

    if not users:
        bot.reply_to(message, "Belum ada data bulan ini.")
        return

    u_count = Counter(users)
    t_count = Counter(teknisi)

    text = f"📊 Laporan Bulan {now.strftime('%B %Y')}\n\n"

    text += "👤 Per User:\n"
    for u, c in u_count.items():
        text += f"- {u}: {c}\n"

    text += "\n🛠 Teknisi Terbanyak:\n"
    for i, (t, c) in enumerate(t_count.most_common(), start=1):
        text += f"{i}. {t} → {c} tiket\n"

    bot.send_message(message.chat.id, text)

# ========================
# RUN
# ========================
print("Bot running...")
bot.infinity_polling()
