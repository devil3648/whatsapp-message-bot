# WhatsApp Message Bot

A small Python desktop app that guides you through preparing a WhatsApp message and opens it in WhatsApp via a `wa.me` link.

## Features

- Click the on-screen bot to start a new message.
- Enter the recipient's number with country code.
- Enter the message text.
- Choose how many times (1-100) to repeat the message.
- Preview the combined message in a text box (message text only).
- Open WhatsApp with the number and combined message prefilled, ready to send.
- Schedule a message for a specific date and time. At that time a notification appears and WhatsApp opens with the message prefilled.
- View or cancel scheduled messages. The queue is saved to `scheduled_messages.json`, so it survives app restarts.

## Requirements

- Python 3.x
- `tkinter` (included with standard Python installations on Windows)

No third-party packages are needed.

## Run

```bash
python whatsapp_bot.py
```

On Windows you can also double-click `whatsapp_bot.py`.

## How it works

1. Click the bot icon.
2. Type the WhatsApp number including its country code, digits only (for example `919876543210`).
3. Type the message.
4. Type the number of times to repeat it.
5. Check the combined message in the preview box.
6. Click **Send to WhatsApp** and press Send in WhatsApp.

To schedule instead, click **Schedule...**, enter a date (`YYYY-MM-DD`) and time (`HH:MM`, 24-hour), then confirm. Use **Scheduled: N** to see or cancel queued messages.

The app opens `https://wa.me/<number>?text=<message>` in your default browser. It does not send messages by itself; the final send happens in WhatsApp. Scheduled messages that expire while the app is closed are removed on the next launch.
