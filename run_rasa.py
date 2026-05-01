import asyncio
import atexit
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = Path(os.getenv("DOTENV_PATH", BASE_DIR / ".env"))

# Загружаем переменные из .env перед импортом rasa.
# В Docker переменные из env_file уже находятся в os.environ, поэтому override=False
# оставляет приоритет за окружением контейнера.
load_dotenv(dotenv_path=ENV_PATH, override=False)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


def env_flag(name: str, default: bool) -> bool:
    """Read a boolean flag from environment variables."""
    value = os.getenv(name)
    if value is None:
        return default

    normalized_value = value.strip().lower()
    if normalized_value in TRUE_VALUES:
        return True
    if normalized_value in FALSE_VALUES:
        return False

    logger.warning(
        "Invalid boolean value %r for %s. Falling back to %s.",
        value,
        name,
        default,
    )
    return default


def is_rasa_server_run_command(argv: list[str]) -> bool:
    """Return True only for `rasa run`, not for `rasa run actions`."""
    args = argv[1:]
    if not args or args[0] != "run":
        return False

    # `rasa run actions` starts the action server. Ngrok is needed only for
    # the main Rasa HTTP server that receives Telegram webhooks.
    return not (len(args) > 1 and args[1] == "actions")


def get_rasa_port(argv: list[str]) -> str:
    """Detect the Rasa HTTP port from CLI args or environment variables."""
    args = argv[1:]
    for index, arg in enumerate(args):
        if arg in {"--port", "-p"} and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith("--port="):
            return arg.split("=", 1)[1]

    return os.getenv("RASA_NGROK_PORT", os.getenv("PORT", "5005"))


def build_telegram_webhook_url(public_url: str) -> str:
    """Build the full Telegram webhook URL from an ngrok public URL."""
    webhook_path = os.getenv("TELEGRAM_WEBHOOK_PATH", "/webhooks/telegram/webhook")
    webhook_path = webhook_path.strip() or "/webhooks/telegram/webhook"
    if not webhook_path.startswith("/"):
        webhook_path = f"/{webhook_path}"

    return f"{public_url.rstrip('/')}{webhook_path}"


def update_dotenv_value(dotenv_path: Path, key: str, value: str) -> None:
    """Create or update a single key in .env without printing secrets."""
    dotenv_path = dotenv_path.expanduser()
    new_line = f"{key}={value}\n"
    key_pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")

    try:
        dotenv_path.parent.mkdir(parents=True, exist_ok=True)

        if dotenv_path.exists():
            lines = dotenv_path.read_text(encoding="utf-8").splitlines(keepends=True)
        else:
            lines = []

        updated = False
        for index, line in enumerate(lines):
            if key_pattern.match(line):
                lines[index] = new_line
                updated = True
                break

        if not updated:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] = f"{lines[-1]}\n"
            lines.append(new_line)

        dotenv_path.write_text("".join(lines), encoding="utf-8")
        logger.info("Updated %s in %s.", key, dotenv_path)
    except OSError as error:
        logger.warning(
            "Could not update %s: %s. The generated value will be used only "
            "inside the current process.",
            dotenv_path,
            error,
        )


def build_pyngrok_config():
    """Build a pyngrok config using writable paths in Docker by default."""
    from pyngrok.conf import PyngrokConfig  # type: ignore[import-not-found]

    config_path = os.getenv("PYNGROK_CONFIG_PATH") or os.getenv("NGROK_CONFIG_PATH")
    ngrok_path = os.getenv("PYNGROK_NGROK_PATH") or os.getenv("NGROK_PATH")
    region = os.getenv("NGROK_REGION")

    kwargs = {}
    if region:
        kwargs["region"] = region

    if config_path:
        config_path_path = Path(config_path).expanduser()
        config_path_path.parent.mkdir(parents=True, exist_ok=True)
        kwargs["config_path"] = str(config_path_path)

    if ngrok_path:
        ngrok_path_path = Path(ngrok_path).expanduser()
        ngrok_path_path.parent.mkdir(parents=True, exist_ok=True)
        kwargs["ngrok_path"] = str(ngrok_path_path)

    return PyngrokConfig(**kwargs)


def start_ngrok(port: str) -> str:
    """Start ngrok and return its public URL."""
    try:
        from pyngrok import ngrok  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError(
            "pyngrok is not installed. Run `pip install -r requirements.txt` "
            "locally or rebuild the Docker image with `docker compose build`."
        ) from error

    pyngrok_config = build_pyngrok_config()
    auth_token = os.getenv("NGROK_AUTHTOKEN") or os.getenv("NGROK_AUTH_TOKEN")
    if auth_token:
        ngrok.set_auth_token(auth_token, pyngrok_config=pyngrok_config)
    else:
        logger.warning(
            "NGROK_AUTHTOKEN is not set. If ngrok rejects anonymous tunnels, "
            "add NGROK_AUTHTOKEN to .env."
        )

    addr = os.getenv("RASA_NGROK_ADDR", f"127.0.0.1:{port}")
    connect_options: dict[str, Any] = {"bind_tls": True}

    # For reserved ngrok domains. NGROK_DOMAIN is used by ngrok v3, while
    # NGROK_HOSTNAME keeps compatibility with older setups.
    domain = os.getenv("NGROK_DOMAIN") or os.getenv("NGROK_HOSTNAME")
    if domain:
        connect_options["domain"] = domain

    logger.info("Starting ngrok tunnel to %s...", addr)
    tunnel = ngrok.connect(
        addr=addr,
        proto="http",
        pyngrok_config=pyngrok_config,
        **connect_options,
    )
    atexit.register(
        lambda: ngrok.disconnect(tunnel.public_url, pyngrok_config=pyngrok_config)
    )

    public_url = tunnel.public_url
    if not public_url.startswith("https://"):
        logger.warning(
            "Ngrok returned a non-HTTPS URL (%s). Telegram webhooks require HTTPS.",
            public_url,
        )

    logger.info("Ngrok tunnel is ready: %s", public_url)
    return public_url


def configure_auto_ngrok() -> None:
    """Start ngrok for `rasa run` and sync TELEGRAM_WEBHOOK_URL."""
    if not is_rasa_server_run_command(sys.argv):
        return

    if not env_flag("RASA_AUTO_NGROK", default=True):
        logger.info("Automatic ngrok startup is disabled by RASA_AUTO_NGROK.")
        return

    port = get_rasa_port(sys.argv)
    try:
        public_url = start_ngrok(port)
    except Exception as error:
        message = (
            "Failed to start ngrok automatically. Check NGROK_AUTHTOKEN in .env "
            "or set RASA_AUTO_NGROK=false to start Rasa without ngrok."
        )
        if env_flag("RASA_AUTO_NGROK_REQUIRED", default=True):
            raise RuntimeError(message) from error

        logger.exception("%s Continuing without ngrok.", message)
        return

    webhook_url = build_telegram_webhook_url(public_url)
    os.environ["TELEGRAM_WEBHOOK_URL"] = webhook_url
    update_dotenv_value(ENV_PATH, "TELEGRAM_WEBHOOK_URL", webhook_url)
    logger.info("TELEGRAM_WEBHOOK_URL is set to %s", webhook_url)


configure_auto_ngrok()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Monkey patch for Rasa Telegram channel
try:
    from rasa.core.channels.telegram import (
        RasaException,
        TelegramAPIError,
        TelegramInput,
        TelegramOutput,
    )

    def patched_get_output_channel(self) -> TelegramOutput:
        """Loads the telegram channel with fixed asyncio session closing."""
        import re

        # Принудительно подставляем переменные окружения в токен
        token = self.access_token
        if token and token.startswith("${") and token.endswith("}"):
            token = os.getenv(token[2:-1], token)

        # И в webhook_url (Rasa может использовать его позже)
        if self.webhook_url and "${" in self.webhook_url:
            self.webhook_url = re.sub(
                r"\${(\w+)}",
                lambda m: os.getenv(m.group(1), m.group(0)),
                self.webhook_url,
            )

        channel = TelegramOutput(token)

        async def _set_webhook():
            await channel.set_webhook(url=self.webhook_url)
            if hasattr(channel, "_session") and channel._session:
                await channel._session.close()

        try:
            asyncio.run(_set_webhook())
        except TelegramAPIError as error:
            raise RasaException(
                "Failed to set channel webhook: " + str(error)
            ) from error

        return channel

    TelegramInput.get_output_channel = patched_get_output_channel
    logging.getLogger(__name__).info(
        "Applied TelegramInput monkey patch for aiogram event loop bug."
    )
except ImportError:
    pass

from rasa.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
