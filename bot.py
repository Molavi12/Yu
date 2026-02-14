import os
import requests
import re
import time
import random
import telebot
from telebot import types
from bs4 import BeautifulSoup
from PIL import Image, ImageEnhance
import io

# ========== تنظیمات بات (خواندن از متغیرهای محیطی) ==========
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("لطفاً متغیر محیطی BOT_TOKEN را تنظیم کنید.")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_states = {}
user_data = {}

# شناسه سوپرگروه برای ارسال لاگ‌ها (اختیاری - می‌تواند از محیط خوانده شود)
SUPERGROUP_ID = os.environ.get("SUPERGROUP_ID")
if SUPERGROUP_ID:
    SUPERGROUP_ID = int(SUPERGROUP_ID)

# ========== توابع کمکی بانکی ==========
def analyze_bank_card(card_number):
    """تحلیل شماره کارت و شناسایی بانک"""
    BANK_DB = {
        '603799': ['بانک ملی ایران', '017'],
        '589210': ['بانک سپه', '015'],
        '603769': ['بانک صادرات ایران', '019'],
        '610433': ['بانک ملت', '012'],
        '627353': ['بانک تجارت', '018'],
        '589463': ['بانک رفاه کارگران', '013'],
        '628023': ['بانک مسکن', '014'],
        '603770': ['بانک کشاورزی', '016'],
        '622106': ['بانک پارسیان', '054'],
        '627412': ['بانک اقتصاد نوین', '055'],
        '621986': ['بانک سامان', '056'],
        '502229': ['بانک پاسارگاد', '057'],
        '627648': ['بانک توسعه صادرات', '020'],
        '627961': ['بانک صنعت و معدن', '011'],
        '627760': ['پست بانک ایران', '021'],
        '502908': ['بانک توسعه تعاون', '022'],
        '627488': ['بانک کارآفرین', '053'],
        '639346': ['بانک سینا', '059'],
        '502806': ['بانک شهر', '061'],
        '502938': ['بانک دی', '066'],
        '606373': ['بانک قرض‌الحسنه مهر', '060'],
        '504172': ['بانک قرض‌الحسنه رسالت', '070'],
        '505416': ['بانک گردشگری', '064'],
        '639599': ['بانک قوامین', '052'],
        '627381': ['بانک انصار', '063'],
        '639607': ['بانک سرمایه', '058'],
        '636949': ['بانک حکمت ایرانیان', '065'],
        '636214': ['بانک آینده', '062']
    }

    clean_number = ''.join(filter(str.isdigit, card_number))

    if len(clean_number) != 16:
        return {
            'bank_name': 'نامشخص',
            'sheba_code': 'نامشخص',
            'is_valid': False,
            'formatted_card': clean_number
        }

    prefix = clean_number[:6]
    bank_info = BANK_DB.get(prefix, ['نامشخص', 'نامشخص'])
    bank_name, sheba_code = bank_info

    def luhn_check(num):
        total = 0
        reverse_digits = num[::-1]
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0

    is_valid = luhn_check(clean_number)
    formatted_card = f"{clean_number[:4]}-{clean_number[4:8]}-{clean_number[8:12]}-{clean_number[12:16]}"

    return {
        'bank_name': bank_name,
        'sheba_code': sheba_code,
        'is_valid': is_valid,
        'formatted_card': formatted_card
    }

def process_captcha_image(image_bytes):
    """بهبود کیفیت تصویر کپچا"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert('L')

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        output_buffer = io.BytesIO()
        image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    except:
        return image_bytes

# ========== کلاس استعلام ==========
class CardInfoInquiry:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://ib.bki.ir"
        self.source_card = "6037701135763164"
        self.target_card = None
        self.amount = "1000000"
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
        }

    def make_request(self, url, method='GET', data=None):
        try:
            time.sleep(random.uniform(1.5, 3))
            headers = self.get_headers()

            if method == 'POST':
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                response = self.session.post(url, data=data, headers=headers, timeout=20)
            else:
                response = self.session.get(url, headers=headers, timeout=20)

            if response.status_code == 200:
                return response
        except:
            pass
        return None

    def get_form_page(self):
        self.session.cookies.clear()
        url = f"{self.base_url}/pid43.lmx"
        response = self.make_request(url)

        if response and 'درخواست شما مسدود شده است' not in response.text:
            return response.text
        return None

    def extract_captcha_url(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        img = soup.find('img', {'class': '-am-captcha-img'})

        if img and img.get('src'):
            return f"{self.base_url}/{img['src']}" if not img['src'].startswith('http') else img['src']

        for i in soup.find_all('img'):
            if 'captcha' in i.get('src', '').lower():
                src = i['src']
                return f"{self.base_url}/{src}" if not src.startswith('http') else src
        return None

    def extract_viewstate(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        fields = {}

        for input_tag in soup.find_all('input'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')
            if name:
                fields[name] = value
        return fields

    def submit_form(self, html, target_card, captcha_text):
        soup = BeautifulSoup(html, 'html.parser')
        form_data = self.extract_viewstate(html)

        form_data['ctl00$ContentPlaceHolder1$txtFomToCard$txtFromCardNo$txtCardNO'] = self.source_card
        form_data['ctl00$ContentPlaceHolder1$txtFomToCard$txtToCardNo$txtCardNO'] = target_card
        form_data['ctl00$ContentPlaceHolder1$txtMab'] = self.amount
        form_data['ctl00$ContentPlaceHolder1$Captcha$CaptchaText'] = captcha_text

        btn = soup.find('input', {'type': 'submit', 'id': 'ContentPlaceHolder1_btnSubmit'})
        if btn:
            form_data[btn.get('name')] = 'ثبت'

        form_data['__EVENTTARGET'] = ''
        form_data['__EVENTARGUMENT'] = ''

        response = self.make_request(f"{self.base_url}/pid43.lmx", method='POST', data=form_data)

        if response:
            return response.text
        return None

    def parse_result(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator='\n')
        info = {'name': None, 'account': None}

        name_match = re.search(r'متعلق به\s*([^\n]+?)\s*بانک', text)
        if name_match:
            name = name_match.group(1).strip()
            if "بانک" not in name:
                info['name'] = name

        acc_match = re.search(r'به شماره حساب\s*(\d+)', text)
        if acc_match:
            info['account'] = acc_match.group(1)

        return info

# ========== هندلرهای ربات ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    user_states[user_id] = 'waiting_for_card'
    bot.send_message(user_id, "🔐 لطفاً شماره کارت ۱۶ رقمی را ارسال کنید:")

@bot.message_handler(commands=['cancel'])
def cancel_operation(message):
    user_id = message.chat.id
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_data:
        del user_data[user_id]
    bot.send_message(user_id, "❌ عملیات کنسل شد.")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'waiting_for_card')
def receive_card_number(message):
    user_id = message.chat.id
    card_input = message.text.strip().replace('-', '').replace(' ', '')

    try:
        bot.delete_message(user_id, message.message_id)
    except:
        pass

    if not card_input.isdigit() or len(card_input) != 16:
        bot.send_message(user_id, "❌ شماره کارت نامعتبر است. لطفاً ۱۶ رقم وارد کنید.")
        return

    card_analysis = analyze_bank_card(card_input)
    inquiry = CardInfoInquiry()
    page_html = inquiry.get_form_page()

    if not page_html:
        bot.send_message(user_id, "❌ خطا در ارتباط با سرور بانک.")
        return

    captcha_url = inquiry.extract_captcha_url(page_html)
    if not captcha_url:
        bot.send_message(user_id, "❌ خطا.")
        return

    captcha_img = inquiry.make_request(captcha_url)
    if not captcha_img:
        bot.send_message(user_id, "❌ خطا.")
        return

    processed_img = process_captcha_image(captcha_img.content)

    msg = bot.send_photo(user_id, processed_img, caption="🔡 کد داخل تصویر را ارسال کنید:")

    user_data[user_id] = {
        'card': card_input,
        'inquiry': inquiry,
        'html': page_html,
        'analysis': card_analysis,
        'last_msg_id': msg.message_id
    }
    user_states[user_id] = 'waiting_for_captcha'

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'waiting_for_captcha')
def receive_captcha(message):
    user_id = message.chat.id
    captcha_text = message.text.strip()

    if not captcha_text:
        return

    try:
        bot.delete_message(user_id, message.message_id)
    except:
        pass

    try:
        if user_id in user_data and 'last_msg_id' in user_data[user_id]:
            bot.delete_message(user_id, user_data[user_id]['last_msg_id'])
    except:
        pass

    if user_id not in user_data:
        bot.send_message(user_id, "❌ نشست منقضی شده. /start")
        return

    loading_msg = bot.send_message(user_id, "⏳ در حال استعلام...")

    try:
        data = user_data[user_id]
        inquiry = data['inquiry']
        page_html = data['html']
        card_number = data['card']
        card_analysis = data['analysis']

        result_html = inquiry.submit_form(page_html, card_number, captcha_text)

        if not result_html:
            bot.edit_message_text("❌ خطا در دریافت پاسخ از سرور.", user_id, loading_msg.message_id)
            return

        if "کد امنیتی صحیح نمی باشد" in result_html or "کد امنیتی اشتباه" in result_html:
            bot.edit_message_text("❌ کد امنیتی اشتباه است.\nدوباره تلاش کنید.", user_id, loading_msg.message_id)
            return

        info = inquiry.parse_result(result_html)

        sheba_raw = "یافت نشد"
        sheba_display = "یافت نشد"

        if info['account'] and card_analysis['sheba_code'] != 'نامشخص':
            account_19 = info['account'].zfill(19)
            bank_code = card_analysis['sheba_code']
            sheba_raw = f"IR(){bank_code}{account_19}"
            sheba_display = ' '.join([sheba_raw[i:i+4] for i in range(0, len(sheba_raw), 4)])

        response_text = (
            f"✅ <b>اطلاعات کارت بانکی</b>\n\n"
            f"🏦 <b>بانک:</b>\n{card_analysis['bank_name']}\n\n"
            f"👤 <b>نام دارنده:</b>\n{info['name'] if info['name'] else 'یافت نشد'}\n\n"
            f"🔢 <b>شماره حساب:</b>\n{info['account'] if info['account'] else 'یافت نشد'}\n\n"
            f"💳 <b>شماره شبا:</b>\n<code>{sheba_display}</code>"
        )

        bot.edit_message_text(response_text, user_id, loading_msg.message_id, parse_mode='HTML')

        # ارسال لاگ به سوپرگروه (اگر تعریف شده باشد)
        if SUPERGROUP_ID:
            try:
                username = message.from_user.username
                user_id_log = message.from_user.id
                user_identity = f"@{username}" if username else f"ID: {user_id_log}"
                log_text = (
                    f"🔺 <b>استعلام جدید انجام شد</b>\n"
                    f"👤 <b>کاربر:</b> {user_identity}\n"
                    f"💳 <b>شماره کارت:</b> {card_number}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{response_text}"
                )
                bot.send_message(SUPERGROUP_ID, log_text, parse_mode='HTML')
            except:
                pass

        markup = types.InlineKeyboardMarkup()
        if sheba_raw != "یافت نشد":
            markup.add(types.InlineKeyboardButton("📋 کپی شماره شبا", callback_data=f"copy_sheba_{sheba_raw}"))
        markup.add(types.InlineKeyboardButton("🔄 استعلام جدید", callback_data="new_search"))

        bot.send_message(user_id, "ابزارها:", reply_markup=markup)
        user_states[user_id] = 'completed'

    except Exception as e:
        bot.edit_message_text("❌ خطای ناشناخته رخ داد.", user_id, loading_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("copy_sheba_"):
        sheba = call.data.split("copy_sheba_")[1]
        bot.answer_callback_query(call.id, "کپی شد")
        bot.send_message(call.message.chat.id, f"`{sheba}`", parse_mode='Markdown')
    elif call.data == "new_search":
        user_id = call.message.chat.id
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_data:
            del user_data[user_id]
        bot.send_message(user_id, "🔄 برای شروع مجدد شماره کارت را بفرستید:")
        user_states[user_id] = 'waiting_for_card'
        bot.answer_callback_query(call.id)

# ========== اجرا ==========
if __name__ == "__main__":
    print("ربات شروع به کار کرد...")
    bot.polling(none_stop=True)
