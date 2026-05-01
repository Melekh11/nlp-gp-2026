# Rasa Telegram Бот

Этот репозиторий содержит чат-бота на базе Rasa, интегрированного с Telegram.

Теперь `run_rasa.py` умеет автоматически:

- запускать `ngrok` при старте основного Rasa-сервера;
- получать публичную `https://...ngrok...` ссылку;
- собирать полный Telegram webhook URL вида `https://.../webhooks/telegram/webhook`;
- записывать его в `.env` как `TELEGRAM_WEBHOOK_URL`;
- передавать актуальное значение в Rasa до установки Telegram webhook.

Docker Compose синхронизирован с этим сценарием: при `docker compose up` запускаются action server, Rasa и автоматический ngrok-туннель.

## Переменные окружения

Создайте `.env` из примера и заполните секреты:

```bash
cp .env.example .env
```

Минимально нужны:

```env
TELEGRAM_TOKEN=<токен Telegram Bot API от @BotFather>
NGROK_AUTHTOKEN=<ваш ngrok authtoken> # получить здесь https://dashboard.ngrok.com/authtokens
```

`TELEGRAM_WEBHOOK_URL` вручную больше обновлять не нужно — скрипт сам перезапишет его при каждом новом запуске ngrok.

Полезные дополнительные переменные:

| Переменная | Значение по умолчанию | Для чего нужна |
| --- | --- | --- |
| `RASA_AUTO_NGROK` | `true` | Включает/выключает автоматический ngrok. |
| `RASA_AUTO_NGROK_REQUIRED` | `true` | Если `true`, Rasa не стартует при ошибке ngrok. |
| `TELEGRAM_WEBHOOK_PATH` | `/webhooks/telegram/webhook` | Путь Telegram webhook в Rasa. |
| `NGROK_REGION` | не задано | Регион ngrok, например `eu`. |
| `NGROK_DOMAIN` | не задано | Зарезервированный домен ngrok, если он есть в аккаунте. |

> Для современных аккаунтов ngrok обычно нужен `NGROK_AUTHTOKEN`. Его можно взять в dashboard ngrok.

## Запуск через Docker

1. Создайте и заполните `.env`.

2. Если модели ещё нет или вы меняли `data/`, `domain.yml` или `config.yml`, обучите модель:

```bash
docker compose run --rm --no-deps rasa train
```

3. Запустите проект:

```bash
docker compose up --build
```

Что произойдёт при запуске:

- сервис `actions` поднимет Rasa Action Server на `5055`;
- сервис `rasa` запустит `python /app/run_rasa.py run ...`;
- `run_rasa.py` запустит ngrok на порт `5005` внутри контейнера;
- актуальная ссылка будет записана в `.env` в `TELEGRAM_WEBHOOK_URL`;
- Rasa установит Telegram webhook на новый URL.

Для остановки:

```bash
docker compose down
```

Если нужно запустить Rasa без ngrok, добавьте в `.env`:

```env
RASA_AUTO_NGROK=false
```

## Локальный запуск без Docker

1. Создайте окружение и установите зависимости:

```bash
conda create -n rasa python=3.10 -y
conda activate rasa
pip install -r requirements.txt
```

2. Создайте и заполните `.env`:

```bash
cp .env.example .env
```

3. Обучите модель, если нужно:

```bash
rasa train
```

4. В отдельном терминале запустите action server:

```bash
rasa run actions
```

5. Запустите Rasa через wrapper-скрипт:

```bash
python run_rasa.py run --enable-api --port 5005 --cors "*"
```

`ngrok` вручную запускать не нужно. Скрипт сам скачает/запустит ngrok через `pyngrok`, получит публичную ссылку и обновит `.env`.

## Что изменено для Docker

- Добавлен корневой `Dockerfile` для Rasa с зависимостью `pyngrok`.
- `docker-compose.yml` теперь запускает Rasa через `run_rasa.py`, а не напрямую через официальный entrypoint.
- Добавлен `endpoints.docker.yml`, где action endpoint указывает на Docker service name `http://actions:5055/webhook`.
- Action Server собирается из `actions/Dockerfile`, а каталог `exports/` монтируется в контейнер.

## Групповой проект по курсу NLP

### Бот подбора вакансий

Технологии:

- open-source Rasa
- Telegram Bot API
- ngrok
- Docker Compose

Команда:

- Тимофей Морозов
- Дарья Осина
- Шинкарев Роман
- Мелехин Матвей
