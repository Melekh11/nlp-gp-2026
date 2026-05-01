# Rasa Telegram Бот

Этот репозиторий содержит чат-бота на базе Rasa, интегрированного с Telegram. В него включен специальный скрипт для запуска, который исправляет ошибку `asyncio` event loop в Windows.

## Инструкции по настройке

1. **Клонируйте репозиторий:**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Создайте виртуальное окружение и установите зависимости:**
   ```bash
   conda create -n rasa python=3.10 -y
   conda init
   conda activate rasa
   pip install -r requirements.txt
   ```

3. **Переменные окружения:**
   Скопируйте файл примера переменных окружения и добавьте свои данные Telegram:
   ```bash
   cp .env.example .env
   ```
   Откройте `.env` и заполните:
   - `TELEGRAM_TOKEN`: Ваш токен Telegram Bot API от @BotFather
   - `TELEGRAM_WEBHOOK_URL`: Ваш URL вебхука (например, от ngrok: `https://<your-ngrok-url>/webhooks/telegram/webhook`)

4. **Запуск Ngrok (для локальной разработки):** (прописывать полный путь до ngrok)
   ```bash
   ngrok http 5005
   ```
   *(Не забывайте обновлять `TELEGRAM_WEBHOOK_URL` в `.env` каждый раз, когда меняется URL в ngrok).*

5. **Обучение модели (если необходимо):**
   ```bash
   rasa train
   ```

6. **Запуск сервера действий (Action Server):**
   В отдельном терминале выполните:
   ```bash
   rasa run actions
   ```

7. **Запуск сервера Rasa:**
   Используйте кастомный скрипт для запуска сервера. Этот скрипт автоматически применяет патч ("monkey patch") для исправления ошибок `asyncio`, связанных с каналом Telegram.
   ```bash
   python run_rasa.py run --enable-api
   ```
# Групповой проект по курсу NLP

## бот подбора вакансий

Технологии:
- open-scource RASA

Команда:
- Тимофей Морозов, 
- Дарья Осина, 
- Шинкарев Роман, 
- Мелехин Матвей
