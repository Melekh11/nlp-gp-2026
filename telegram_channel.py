import json
from typing import Any

from aiogram.types import Update
from rasa.core.channels.channel import UserMessage
from rasa.core.channels.telegram import TelegramInput, TelegramOutput
from rasa.shared.constants import INTENT_MESSAGE_PREFIX
from rasa.shared.core.constants import USER_INTENT_RESTART
from sanic import Blueprint, response


class FixedTelegramInput(TelegramInput):
    def blueprint(self, on_new_message):
        telegram_webhook = Blueprint("telegram_webhook", __name__)

        @telegram_webhook.route("/", methods=["GET"])
        async def health(_):
            return response.json({"status": "ok"})

        @telegram_webhook.route("/set_webhook", methods=["GET", "POST"])
        async def set_webhook(_):
            out_channel = TelegramOutput(self.access_token)
            ok = await out_channel.set_webhook(self.webhook_url)
            return response.text("Webhook setup successful" if ok else "Invalid webhook")

        @telegram_webhook.route("/webhook", methods=["GET", "POST"])
        async def message(request):
            if request.method != "POST":
                return response.text("success")
            out_channel = TelegramOutput(self.access_token)
            request_dict: Any = request.json
            if isinstance(request_dict, str):
                request_dict = json.loads(request_dict)
            update = Update(**request_dict)
            if self._is_button(update):
                msg = update.callback_query.message
                text = update.callback_query.data
            elif self._is_edited_message(update):
                msg = update.edited_message
                text = update.edited_message.text
            else:
                msg = update.message
                if self._is_user_message(msg):
                    text = msg.text.replace("/bot", "")
                elif self._is_location(msg):
                    text = '{{"lng":{0}, "lat":{1}}}'.format(
                        msg.location.longitude, msg.location.latitude
                    )
                else:
                    return response.text("success")
            sender_id = msg.chat.id
            metadata = self.get_metadata(request)
            try:
                if text == (INTENT_MESSAGE_PREFIX + USER_INTENT_RESTART):
                    await on_new_message(
                        UserMessage(
                            text,
                            out_channel,
                            sender_id,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
                    await on_new_message(
                        UserMessage(
                            "/start",
                            out_channel,
                            sender_id,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
                else:
                    await on_new_message(
                        UserMessage(
                            text,
                            out_channel,
                            sender_id,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
            except Exception:
                if self.debug_mode:
                    raise
            return response.text("success")

        return telegram_webhook
