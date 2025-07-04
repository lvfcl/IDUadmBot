import importlib
import configC
import zipfile 
import asyncio
import config
import glob
import time
import os
from aiogram.filters import StateFilter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile, ContentType, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from typing import Dict

bot = Bot(token=configC.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
admin_sessions: Dict[int, asyncio.Task] = {}
admin_lock = asyncio.Lock()
authorized_admins = {}
active_forms = {}
submissions = {}
ADMIN_TIMEOUT = 600

photo_responses = {
    "🎓 Спеціальності": "Спеціальності.jpg",
    "🗓 Календар вступу": "Календар вступу.jpg",
    "📋 Умови відбору": "Умови відбору.jpg",
    "📊 Вимоги до конкурсного балу": "Вимоги до конкурсного балу.jpg",
    "💸 Джерела фінансування": "Джерела фінансування.jpg",
    "📄 Конкурсні пропозиції Навчально-наукового інституту \"Інститут державного управління\" на основі повної загальної середньої освіти":
        "Конкурсні пропозиції Навчально-наукового інституту 'Інститут державного управління' на основі повної загальної середньої освіти.jpg",
    "🎓 Конкурсні пропозиції на основі фахового молодшого бакалавра, молодшого бакалавра, молодшого спеціаліста":
        "Конкурсні пропозиції на основі фахового молодшого бакалавра, молодшого бакалавра, молодшого спеціаліста.jpg",
    "🎓 Конкурсні пропозиції на основі здобутого рівня вищої освіти (2 вища освіта)":
        "Конкурсні пропозиції на основі здобутого рівня вищої освіти (2 вища освіта).jpg",
    "📞 Контакти": "Контакти.jpg"
}

class AdminState(StatesGroup):
    waiting_for_password = State()
    waiting_for_config = State()
    waiting_for_config_media_zip = State()


menu_start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎓 Студент")], [KeyboardButton(text="🚀 Вступник")],
        [KeyboardButton(text="⚙️ Панель адміністратора")],
    ],
    resize_keyboard=True
)  

menu_student_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Розклад")],
        [KeyboardButton(text="🏫 Довідка про місце навчання")],
        [KeyboardButton(text="⚠️ Скарги та звернення")],
        [KeyboardButton(text="🎓 Cтудентська рада")],
        [KeyboardButton(text="🌐 Соціальні мережі")],
        [KeyboardButton(text="📞 Консультація")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True
)

menu_complaints_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Скарги та звернення"), KeyboardButton(text="Повідомлення про порушення")],
        [KeyboardButton(text="🔙 Повернутись")],
    ],
    resize_keyboard=True
)

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Відміна")]
    ],
    resize_keyboard=True
)

entrant_main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📘 Абітурієнту"), KeyboardButton(text="❓ Як вступити")],
        [KeyboardButton(text="💰 Фінансові питання"), KeyboardButton(text= "🔙 Назад")],
    ],
    resize_keyboard=True
)

entrant_info_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎓 Спеціальності")],
        [KeyboardButton(text="🗓 Календар вступу")],
        [KeyboardButton(text="📋 Умови відбору")],
        [KeyboardButton(text="📊 Вимоги до конкурсного балу")],
        [KeyboardButton(text="💸 Джерела фінансування")],
        [KeyboardButton(text='📄 Конкурсні пропозиції Навчально-наукового інституту "Інститут державного управління" на основі повної загальної середньої освіти')],
        [KeyboardButton(text="🎓 Конкурсні пропозиції на основі фахового молодшого бакалавра, молодшого бакалавра, молодшого спеціаліста")],
        [KeyboardButton(text="🎓 Конкурсні пропозиції на основі здобутого рівня вищої освіти (2 вища освіта)")],
        [KeyboardButton(text="📞 Контакти")],
        [KeyboardButton(text="🔙 Повернутись до вибору")],
    ],
    resize_keyboard=True
)


how_to_apply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📑 Які документи потрібні для вступу?"), KeyboardButton(text="🧮 Калькулятор балу НМТ")],
        [KeyboardButton(text="🌐 Якщо хочете вступити онлайн"), KeyboardButton(text="✍️ Шаблон мотиваційного листа")],
        [KeyboardButton(text="🔙 Повернутись до вибору")],
    ],
    resize_keyboard=True
)

financial_info_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Вартість навчання"), KeyboardButton(text="🎓 Стипендії?")],
        [KeyboardButton(text="🏅 Військова кафедра?"), KeyboardButton(text="🏠 Гуртожиток?")],
        [KeyboardButton(text="🔙 Повернутись до вибору")],
    ],
    resize_keyboard=True
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📘 Інструкція з експлуатації бота")],
        [KeyboardButton(text="📄 Config file"), KeyboardButton(text="📝 New config file")],
        [KeyboardButton(text="🗃 Config_media"), KeyboardButton(text="📥 New config_media")],
        [KeyboardButton(text="📜 Архiв")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True
)


@dp.message(F.text == "/start")
async def start_command(message: types.Message):
    await message.answer("Вітаємо! Оберіть потрібний розділ:", reply_markup=menu_start_keyboard)
    

@dp.message(F.text == "🎓 Студент")
async def student_command(message: types.Message):
    await message.answer("""
Вітаємо на платформі «Адміністрація в телеграм» Інституту державного управління! Ця платформа створена для того, щоб спростити комунікацію та зробити Ваше навчання легше та цікавішим!

Чим можемо Вам допомогти ?
""", reply_markup=menu_student_keyboard)


@dp.message(F.text == "📅 Розклад")
async def schedule_command(message: types.Message):
    await message.answer(config.link_schedule)


@dp.message(F.text == "🏫 Довідка про місце навчання")
async def info_command(message: types.Message):
    await message.answer(config.link_info)


@dp.message(F.text == "⚠️ Скарги та звернення")
async def complaints_command(message: types.Message):
    await message.answer("Оберіть потрібний розділ:", reply_markup=menu_complaints_keyboard)
    

@dp.message(F.text == "Скарги та звернення")
async def complaints_command(message: types.Message):
    active_forms[message.from_user.id] = "Скарги та звернення"
    await message.answer("Будь ласка, залиште тут Ваше звернення (Також, будь ласка, вкажіть Ваш ПІБ та академічну групу).", reply_markup=back_keyboard)


@dp.message(F.text == "Повідомлення про порушення")
async def violations_command(message: types.Message):
    active_forms[message.from_user.id] = "Повідомлення про порушення"
    await message.answer("Будь ласка, напишіть про порушення та надішліть підкріплюючі докази (за можливістю). Вона буде передана анонімно.", reply_markup=back_keyboard)


@dp.message(F.text == "🔙 Повернутись")
async def back_command(message: types.Message):
    await message.answer("Оберіть потрібний розділ:", reply_markup=menu_student_keyboard)


@dp.message(F.text == "🔙 Назад")
async def fullback_command(message: types.Message):
    await message.answer("Оберіть потрібний розділ:", reply_markup=menu_start_keyboard)


@dp.message(F.text == "🔙 Повернутись до вибору")
async def back_to_entrant_command(message: types.Message):
    await message.answer("Оберіть що Вам підказати:", reply_markup=entrant_main_keyboard)


@dp.message(F.text == "🎓 Cтудентська рада")
async def send_student_council_info(message: types.Message):
    caption = (
        "🎓 Студентська рада ННІ «ІДУ» — це серце нашого студентського життя, місце ідей, драйву та дій! 💥\n\n"
        "💡 Тут ти можеш не просто навчатися, а творити зміни, реалізовувати проєкти, знайомитися з однодумцями та бути в епіцентрі всіх подій!\n\n"
        "📌 Хочеш більше, ніж просто пари? Тут тебе почують, підтримають і надихнуть!\n\n"
        f"📲 <a href='{config.studrada_tg_link}'>Клікай</a> — і доєднуйся до ком’юніті активних! 🌟"
    )

    await message.answer_photo(
    photo=FSInputFile(configC.MEDIA_PATH + "studrada.jpg"),
    caption=caption,
    parse_mode="HTML"
    )   

@dp.message(F.text == "🌐 Соціальні мережі")
async def social_command(message: types.Message):
    await message.answer(config.link_social)


@dp.message(F.text == "📞 Консультація")
async def consultation_command(message: types.Message):
    await message.answer(config.link_consultation)


@dp.message(F.text == "🚀 Вступник")
async def entrant_command(message: types.Message):
    await message.answer("""
Вітаємо в <b>Інституті державного управління</b>!\n\n
Ми — осередок майбутніх лідерів, що змінюють країну. Наш інститут формує управлінців нового покоління, здатних вирішувати складні завдання та впроваджувати інновації в державному управлінні, бізнесі та громадському секторі.\n
Ми не просто навчаємо — ми готуємо до реальних викликів. Наша мета — передати вам не лише знання, але й навички, що дозволяють знаходити ефективні рішення в умовах швидких змін. У нас ви отримаєте освіту, орієнтовану на результат, що відповідає найкращим міжнародним стандартам.\n
Приєднуйтесь до нас і станьте частиною покоління, яке впливатиме на майбутнє!\n
📩 Зарошуємо приєнатися до нашої комунікаційної групи, щоб слідкувати за актуальними новинами та у разі додаткових запитань: https://t.me/+kLxaztb5CndlNWYy

""", parse_mode="HTML", reply_markup=entrant_main_keyboard)


@dp.message(lambda message: message.text in photo_responses)
async def send_photo_from_dict(message: types.Message):
    file_name = photo_responses[message.text]
    await message.answer_photo(photo=FSInputFile(configC.MEDIA_PATH + file_name))


@dp.message(F.text == "📘 Абітурієнту")
async def entrant_info_command(message: types.Message):
    await message.answer("Оберіть що Вам підказати:", reply_markup=entrant_info_keyboard)


@dp.message(F.text == "❓ Як вступити")
async def how_to_apply_command(message: types.Message):
    await message.answer("Оберіть що Вам підказати:", reply_markup=how_to_apply_keyboard)


@dp.message(F.text == "📑 Які документи потрібні для вступу?")
async def documents_command(message: types.Message):
    await message.answer("""
📌 Вам знадобляться:
•  	Паспорт або ID-картка
•  	Ідентифікаційний код
•  	Атестат про повну загальну середню освіту та додаток до нього
•  	Сертифікати НМТ ( Без НМТ можуть вступати іноземці, абітурієнти з пільгами або ті, хто вже має диплом про вищу освіту. )
•  	Фото 3×4
""", reply_markup=how_to_apply_keyboard)


@dp.message(F.text == "🧮 Калькулятор балу НМТ")
async def calculator_command(message: types.Message):
    await message.answer(f"""
Калькулятор балу НМТ: 
{config.NMT_link}/\n
<a href='{config.coefficients_link}'>Тут</a> можете побачити коефіцієнти за нашими спеціальностями: 
""", parse_mode="HTML", reply_markup=how_to_apply_keyboard)


@dp.message(F.text == "🌐 Якщо хочете вступити онлайн")
async def online_entry_command(message: types.Message):
    await message.answer("Інформація оновлюється", reply_markup=how_to_apply_keyboard)


@dp.message(F.text == "✍️ Шаблон мотиваційного листа")
async def motivation_letter_command(message: types.Message):
    await message.answer_document(document=FSInputFile(configC.MEDIA_PATH + "Мотиваційний лист.docx"))
        
    await message.answer("""
📄 Мотиваційний лист має чітко відображати ваші цілі, бажання навчатися на обраній спеціальності та здатність до подолання складнощів.\n
Важливо зазначити, чому ви обрали саме цю програму та як плануєте використовувати отримані знання в майбутньому.
""", reply_markup=how_to_apply_keyboard)


@dp.message(F.text == "💰 Фінансові питання")
async def financial_info_command(message: types.Message):
    await message.answer("Оберіть що Вам підказати:", reply_markup=financial_info_keyboard)


@dp.message(F.text == "💰 Вартість навчання")
async def tuition_fee_command(message: types.Message):
    await message.answer("💰 Вартість навчання залежить від спеціальності.\nНаразі ціновий діапазон у стадії формування.") 


@dp.message(F.text == "🎓 Стипендії?")
async def scholarships_command(message: types.Message):
    await message.answer("""
🎓 Так, є декілька категорій студентів хто може отримувати стипендію під час навчання: \n
1300 грн - соціальну стипендію отримують студенти які підпадають в незахищені категорії населення.\n
2000 грн - академічну стипендію отримують студенти з кращими результатами в навчанні в своїй академічній групі ( тільки для студентів бюджетної форми навчання ).\n
3000 грн - підвищену академічну стипендію отримують студенти з найкращими результатами в університеті ( тільки для студентів бюджетної форми навчання ).\n
Навіть якщо Ви вступили на контракт у Вас може бути можливість перевестися на бюджет.
""")


@dp.message(F.text == "🏅 Військова кафедра?")
async def military_department_command(message: types.Message):
    await message.answer("""
🎖️ Так, студенти можуть пройти навчання на військовій кафедрі.\n
Від вересня 2025 року для студентів в Україні стартує обов'язкова базова загальновійськова підготовка (БЗВП).\n
Вона включатиме теоретичну частину, яку викладатимуть у закладах освіти, та практиктичну – у військових частинах і центрах.\n
""")


@dp.message(F.text == "🏠 Гуртожиток?")
async def dormitory_command(message: types.Message):
    await message.answer("🏠 Так, гуртожиток є.\n\n Вартість проживання – від 520 грн на місяць.\n\n Гуртожитки є в різних частинах міста, можна обрати зручний варант для себе.")


@dp.message(F.text == "⚙️ Панель адміністратора")
async def admin_command(message: types.Message, state: FSMContext):
    await message.answer("Введіть пароль:", reply_markup=back_keyboard)
    await state.set_state(AdminState.waiting_for_password)


def is_admin_authorized(user_id: int) -> bool:
    now = time.time()
    if user_id in authorized_admins:
        authorized_time = authorized_admins[user_id]
        if now - authorized_time < ADMIN_TIMEOUT:
            return True
        else:
            authorized_admins.pop(user_id)
    return False


@dp.message(AdminState.waiting_for_password)
async def check_admin_password(message: types.Message, state: FSMContext):
    if message.text == "❌ Відміна":
        await message.answer("❌ Відміна входу в панель адміністратора.", reply_markup=menu_start_keyboard)
        return await state.clear()
    
    if message.text != config.admins_password:
        return await message.answer("❌ Неправильний пароль! Спробуйте ще раз.")

    authorized_admins[message.from_user.id] = time.time()
    await message.answer("✅ Вхід в панель адміністратора.", reply_markup=admin_keyboard)
    await message.answer(
        "Ваша сесія триватиме 10 хвилин, після чого потрібно буде заново ввести пароль.\n"
        "Будь ласка, будьте обережні при внесенні змін.",
        reply_markup=admin_keyboard
    )
    await state.clear()


@dp.message(F.text == "📘 Інструкція з експлуатації бота")
async def sending_info(message: types.Message):
    await message.answer_document(FSInputFile("Як користуватись.docx"))


@dp.message(F.text == "📄 Config file")
async def sending_config_file(message: types.Message):
    if not is_admin_authorized(message.from_user.id):
        await message.answer("❌ Термін вашої адмін сесії закінчився.")
        return
    await message.answer("📄 Надсилаю нинішній файл *config.py*.", parse_mode="Markdown")
    await message.answer_document(FSInputFile("config.py"))


@dp.message(F.text == "📝 New config file")
async def ask_new_config(message: types.Message, state: FSMContext):
    if not is_admin_authorized(message.from_user.id):
        await message.answer("❌ Термін вашої адмін сесії закінчився.")
        return
    await message.answer(
        "Надішліть новий *config.py*\n\n*УВАГА!* після застосування конфіг файлу бот перезавантажиться і всі адмін сесії припиняться.",
        parse_mode="Markdown", reply_markup=back_keyboard)
    await state.set_state(AdminState.waiting_for_config)


@dp.message(AdminState.waiting_for_config, F.content_type == ContentType.DOCUMENT)
async def update_config_file(message: types.Message, state: FSMContext):
    if not is_admin_authorized(message.from_user.id):
        return

    if message.document.file_name != "config.py":
        return await message.answer("Будь ласка, надішліть файл *config.py*\nВін обов'язково повинен мати назву \"config.py\"",
                                     parse_mode="Markdown")

    tmp_path = f"config_new_{int(time.time())}.py"
    await bot.download(message.document, destination=tmp_path)

    os.replace(tmp_path, "config.py")

    try:
        for pyc in glob.glob("__pycache__/config*.pyc"):
            os.remove(pyc)
        importlib.reload(config)

        global admins_password, studrada_tg_link, coefficients_link, NMT_link, link_schedule, CHANNEL_ID, link_info, link_social, link_consultation
        admins_password = config.admins_password
        studrada_tg_link = config.studrada_tg_link
        coefficients_link = config.coefficients_link
        NMT_link = config.NMT_link
        link_schedule = config.link_schedule
        CHANNEL_ID = config.CHANNEL_ID
        link_info = config.link_info
        link_social = config.link_social
        link_consultation = config.link_consultation

        await message.answer("✅ Новий *config.py* застосовано.", parse_mode="Markdown", reply_markup=menu_start_keyboard)
    except Exception as e:
        await message.answer(f"❌ Помилка:\n`{e}`", parse_mode="Markdown")

    await state.clear()


@dp.message(F.text == "🗃 Config_media")
async def export_config_media(message: types.Message):
    if not is_admin_authorized(message.from_user.id):
        await message.answer("❌ Термін вашої адмін сесії закінчився.")
        return

    zip_path = "config_media.zip"
    folder_path = "config_media"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

    await message.answer("🗃 Надсилаю нинішній архів *config_media.zip*.", parse_mode="Markdown")
    await message.answer_document(FSInputFile(zip_path))
    os.remove(zip_path)


@dp.message(F.text == "📥 New config_media")
async def prompt_config_media_upload(message: types.Message, state: FSMContext):
    if not is_admin_authorized(message.from_user.id):
        return await message.answer("❌ Термін вашої адмін сесії закінчився.")

    await message.answer("Будь ласка, надішліть архів *config_media.zip*", parse_mode="Markdown", reply_markup=back_keyboard)
    await state.set_state(AdminState.waiting_for_config_media_zip)


@dp.message(AdminState.waiting_for_config_media_zip, F.document)
async def import_config_media(message: types.Message, state: FSMContext):
    if not is_admin_authorized(message.from_user.id):
        return

    if message.document.file_name != "config_media.zip":
        return await message.answer("Будь ласка, надішліть архів *config_media.zip*\nВін обов'язково повинен мати назву \"*config_media.zip*\"",
                                     parse_mode="Markdown")

    zip_path = f"config_media_tmp_{int(time.time())}.zip"
    extract_path = "config_media_new"
    await bot.download(message.document, zip_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        if os.path.exists("config_media"):
            import shutil
            shutil.rmtree("config_media")
        os.rename(extract_path, "config_media")
        await message.answer("✅ Папку config_media успішно оновлено.", reply_markup=admin_keyboard)
    except Exception as e:
        await message.answer(f"❌ Помилка при імпорті: {e}", reply_markup=admin_keyboard)
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            import shutil
            shutil.rmtree(extract_path, ignore_errors=True)
        await state.clear()


@dp.message(F.text == "📜 Архiв")
async def archive_command(message: types.Message):
    if message.from_user.id not in authorized_admins:
        await message.answer("❌ Термін вашої адмін сесії закінчився.")
        return
    folder_map = {
        "Скарги та звернення": "Скарги та звернення",
        "Повідомлення про порушення": "Повідомлення про порушення",
        "Запити на вступ до Студради": "Запити на вступ до Студради"
    }
    zip_files = []
    for key, folder in folder_map.items():
        folder_path = os.path.join(configC.ARCHIVE_FOLDER, folder)
        if not os.path.exists(folder_path):
            continue
        zip_path = os.path.join(configC.ARCHIVE_FOLDER, f"{folder}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=folder_path)
                    zipf.write(file_path, arcname=arcname)
        zip_files.append(zip_path)
    
    if not zip_files:
        await message.answer("📂 Архів порожній.")
        return
    
    await message.answer("📜 Надсилаю архівні файли...")
    for zip_file in zip_files:
        document = FSInputFile(zip_file)
        await message.answer_document(document)

    for zip_file in zip_files:
        os.remove(zip_file)


@dp.message(StateFilter(AdminState.waiting_for_config, AdminState.waiting_for_config_media_zip), F.text == "❌ Відміна")
async def cancel_config_upload(message: types.Message, state: FSMContext):
    await message.answer("❌ Відміна оновлення конфігурації.", reply_markup=admin_keyboard)
    await state.clear()


@dp.message(F.from_user.id.in_(active_forms) & F.content_type.in_([ContentType.TEXT, ContentType.PHOTO]))
async def save_form_data(message: types.Message):
    user_id = message.from_user.id
    form_type = active_forms[user_id]

    if message.text == "❌ Відміна":
        active_forms.pop(user_id, None)
        submissions.pop(user_id, None)
        await message.answer(f"❌ Відміна подання звернення.", reply_markup=menu_student_keyboard)
        return
    
    folder = os.path.join(config.ARCHIVE_FOLDER, form_type)
    os.makedirs(folder, exist_ok=True)
    
    current_time = time.time()
    if user_id in submissions and (current_time - submissions[user_id]["last_update"] < 10):
        folder_path = submissions[user_id]["folder_path"]
        submissions[user_id]["last_update"] = current_time
    else:
        folder_name = "№" + str(int(current_time * 1000))
        folder_path = os.path.join(folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        submissions[user_id] = {"folder_path": folder_path, "last_update": current_time}
    
    text_content = (message.text or message.caption or "").strip()
    if text_content:
        text_file_path = os.path.join(folder_path, "text.txt")
        with open(text_file_path, "a", encoding="utf-8") as f:
            f.write(text_content + "\n" + ("-" * 40) + "\n")
    
    if message.photo:
        photo = message.photo[-1]
        photo_filename = "photo_" + str(int(time.time() * 1000)) + ".jpg"
        photo_path = os.path.join(folder_path, photo_filename)
        file_info = await bot.get_file(photo.file_id)
        await bot.download_file(file_path=file_info.file_path, destination=photo_path)

    file_id = message.photo[-1].file_id if message.photo else None
    caption = message.caption if message.caption else message.text or " "

    formatted_caption = f"📩 <b>Новий запис ({form_type})</b>\n\n{caption}"
    if file_id:
        await bot.send_photo(config.CHANNEL_ID, file_id, caption=formatted_caption, parse_mode="HTML")
    else:
        await bot.send_message(config.CHANNEL_ID, formatted_caption, parse_mode="HTML")

    active_forms.pop(user_id, None)
    submissions.pop(user_id, None)
    await message.answer("✅ Дані збережено. Дякуємо за звернення!", reply_markup=menu_start_keyboard)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

