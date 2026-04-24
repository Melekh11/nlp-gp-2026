import sys
import asyncio
import logging
import os
from dotenv import load_dotenv

# Загружаем переменные из .env перед импортом rasa
load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Monkey patch for Rasa Telegram channel
try:
    from rasa.core.channels.telegram import TelegramInput, TelegramOutput, TelegramAPIError, RasaException
    
    def patched_get_output_channel(self) -> TelegramOutput:
        """Loads the telegram channel with fixed asyncio session closing."""
        import re
        
        # Принудительно подставляем переменные окружения в токен
        token = self.access_token
        if token and token.startswith("${") and token.endswith("}"):
            token = os.getenv(token[2:-1], token)
            
        # И в webhook_url (Rasa может использовать его позже)
        if self.webhook_url and "${" in self.webhook_url:
            self.webhook_url = re.sub(r"\${(\w+)}", lambda m: os.getenv(m.group(1), m.group(0)), self.webhook_url)

        channel = TelegramOutput(token)

        async def _set_webhook():
            await channel.set_webhook(url=self.webhook_url)
            if hasattr(channel, '_session') and channel._session:
                await channel._session.close()

        try:
            asyncio.run(_set_webhook())
        except TelegramAPIError as error:
            raise RasaException(
                "Failed to set channel webhook: " + str(error)
            ) from error

        return channel
    
    TelegramInput.get_output_channel = patched_get_output_channel
    logging.getLogger(__name__).info("Applied TelegramInput monkey patch for aiogram event loop bug.")
except ImportError:
    pass

from rasa.__main__ import main

if __name__ == "__main__":
    main()