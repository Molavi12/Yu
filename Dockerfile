FROM python:3.9-slim

WORKDIR /app

# نصب وابستگی‌های سیستم (در صورت نیاز)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل وابستگی‌ها و نصب آنها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی بقیه فایل‌ها
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
