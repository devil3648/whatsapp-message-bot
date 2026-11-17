import re
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote

MAX_REPEATS = 100


def normalize_number(raw):
    digits = re.sub(r"\D", "", raw)
    if 7 <= len(digits) <= 15:
        return digits
    return None


def build_combined_message(message, times):
    return "\n".join([message] * times)


def build_whatsapp_url(number, text):
    return f"https://wa.me/{number}?text={quote(text, safe='')}"


class WhatsAppBotApp:
    def __init__(self, root):
        self.root = root
        self.step = None
        self.number = None
        self.message = None
        self.combined = None

        root.title("WhatsApp Message Bot")
        root.geometry("640x640")
        root.minsize(560, 540)

        style = ttk.Style()
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Hint.TLabel", foreground="#666666")

        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        header = ttk.Label(main, text="WhatsApp Message Bot", style="Header.TLabel")
        header.pack(anchor="w")

        bot_frame = ttk.Frame(main)
        bot_frame.pack(fill="x", pady=(6, 10))

        self.bot_canvas = tk.Canvas(
            bot_frame,
            width=90,
            height=90,
            highlightthickness=0,
            bg="#F0FDF4",
            cursor="hand2",
        )
        self.bot_canvas.pack(side="left")
        self.draw_bot()
        self.bot_canvas.bind("<Button-1>", lambda event: self.start_conversation())

        hint = ttk.Label(
            bot_frame,
            text="Click the bot to start a new message.\n\n"
            "It will ask for a number, the message,\n"
            "and how many times to repeat it.",
            style="Hint.TLabel",
            justify="left",
        )
        hint.pack(side="left", padx=(14, 0))

        chat_frame = ttk.Frame(main)
        chat_frame.pack(fill="both", expand=True)

        self.chat = tk.Text(
            chat_frame,
            wrap="word",
            height=10,
            state="disabled",
            bg="#FFFFFF",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 10),
            spacing1=3,
            spacing3=3,
            padx=8,
            pady=8,
        )
        chat_scroll = ttk.Scrollbar(chat_frame, command=self.chat.yview)
        self.chat.config(yscrollcommand=chat_scroll.set)
        self.chat.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")

        self.chat.tag_config("bot", foreground="#075E54")
        self.chat.tag_config("user", foreground="#128C7E", lmargin1=24, lmargin2=24)

        input_frame = ttk.Frame(main)
        input_frame.pack(fill="x", pady=(8, 4))

        self.input_var = tk.StringVar()
        self.entry = ttk.Entry(input_frame, textvariable=self.input_var, state="disabled")
        self.send_button = ttk.Button(
            input_frame, text="Send", command=self.on_send, state="disabled", width=10
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.send_button.pack(side="left", padx=(8, 0))
        self.entry.bind("<Return>", lambda event: self.on_send())

        preview_frame = ttk.LabelFrame(main, text="Combined message (message only)", padding=6)
        preview_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.preview_text = tk.Text(
            preview_frame,
            wrap="word",
            height=5,
            state="disabled",
            bg="#FAFAFA",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 10),
            padx=6,
            pady=6,
        )
        preview_scroll = ttk.Scrollbar(preview_frame, command=self.preview_text.yview)
        self.preview_text.config(yscrollcommand=preview_scroll.set)
        self.preview_text.pack(side="left", fill="both", expand=True)
        preview_scroll.pack(side="right", fill="y")

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(10, 0))

        self.send_wa_button = ttk.Button(
            actions,
            text="Send to WhatsApp",
            command=self.send_to_whatsapp,
            state="disabled",
        )
        self.send_wa_button.pack(side="left")

        restart = ttk.Button(actions, text="Start Over", command=self.start_conversation)
        restart.pack(side="right")

    def draw_bot(self):
        c = self.bot_canvas
        c.create_oval(6, 6, 84, 84, fill="#25D366", outline="")
        c.create_line(45, 28, 45, 16, fill="#075E54", width=2)
        c.create_oval(41, 10, 49, 18, fill="#075E54", outline="")
        c.create_rectangle(22, 28, 68, 68, fill="#FFFFFF", outline="#075E54", width=2)
        c.create_oval(32, 40, 40, 48, fill="#075E54", outline="")
        c.create_oval(50, 40, 58, 48, fill="#075E54", outline="")
        c.create_line(36, 58, 54, 58, fill="#075E54", width=2)

    def append_bot(self, text):
        self.chat.config(state="normal")
        self.chat.insert("end", "Bot: " + text + "\n", "bot")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def append_user(self, text):
        self.chat.config(state="normal")
        self.chat.insert("end", "You: " + text + "\n", "user")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def start_conversation(self):
        self.step = "number"
        self.number = None
        self.message = None
        self.combined = None

        self.chat.config(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.config(state="disabled")

        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.config(state="disabled")

        self.send_wa_button.config(state="disabled")
        self.entry.config(state="normal")
        self.send_button.config(state="normal")
        self.input_var.set("")

        self.append_bot(
            "Hi! Enter the WhatsApp number with country code (digits only, "
            "for example 919876543210):"
        )
        self.entry.focus_set()

    def on_send(self):
        raw = self.input_var.get().strip()
        if not raw or self.step is None:
            return

        self.input_var.set("")
        self.append_user(raw)

        if self.step == "number":
            self.handle_number(raw)
        elif self.step == "message":
            self.handle_message(raw)
        elif self.step == "times":
            self.handle_times(raw)

    def handle_number(self, raw):
        number = normalize_number(raw)
        if number is None:
            self.append_bot("That number doesn't look right. Use 7-15 digits with the country code.")
            return
        self.number = number
        self.step = "message"
        self.append_bot("Number saved. Now type the message you want to send.")

    def handle_message(self, raw):
        self.message = raw
        self.step = "times"
        self.append_bot(f"How many times should that message be repeated? (1-{MAX_REPEATS})")

    def handle_times(self, raw):
        try:
            times = int(raw)
        except ValueError:
            self.append_bot("Enter a whole number, for example 3.")
            return

        if not 1 <= times <= MAX_REPEATS:
            self.append_bot(f"Choose a number between 1 and {MAX_REPEATS}.")
            return

        self.combined = build_combined_message(self.message, times)
        self.step = None
        self.append_bot(f"Done. The message was repeated {times} time(s). Check the preview below.")

        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", self.combined)
        self.preview_text.config(state="disabled")
        self.send_wa_button.config(state="normal")
        self.entry.config(state="disabled")
        self.send_button.config(state="disabled")

        if len(self.combined) > 1800:
            self.append_bot("Note: this text is long and some browsers may shorten the WhatsApp link.")

    def send_to_whatsapp(self):
        if not self.number or not self.combined:
            return
        url = build_whatsapp_url(self.number, self.combined)
        try:
            webbrowser.open(url)
            self.append_bot("WhatsApp opened with your number and combined message. Press Send there.")
        except Exception as exc:
            messagebox.showerror("Could not open WhatsApp", str(exc))


def main():
    root = tk.Tk()
    WhatsAppBotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
