import re
import json
import uuid
import webbrowser
import tkinter as tk
from pathlib import Path
from datetime import datetime, timedelta
from tkinter import ttk, messagebox
from urllib.parse import quote

MAX_REPEATS = 100
SCHEDULE_FILE = Path(__file__).with_name("scheduled_messages.json")


def normalize_number(raw):
    digits = re.sub(r"\D", "", raw)
    if 7 <= len(digits) <= 15:
        return digits
    return None


def build_combined_message(message, times):
    return "\n".join([message] * times)


def build_whatsapp_url(number, text):
    return f"https://wa.me/{number}?text={quote(text, safe='')}"


def parse_schedule(date_text, time_text):
    try:
        return datetime.strptime(f"{date_text.strip()} {time_text.strip()}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError("Use YYYY-MM-DD for the date and HH:MM (24-hour) for the time.")


def load_jobs(path=SCHEDULE_FILE):
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        return []

    jobs = []
    for job in data:
        if not isinstance(job, dict):
            continue
        if not all(key in job for key in ("id", "number", "text", "due_at")):
            continue
        try:
            datetime.fromisoformat(job["due_at"])
        except (TypeError, ValueError):
            continue
        jobs.append(job)
    return jobs


def save_jobs(jobs, path=SCHEDULE_FILE):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(jobs, handle, indent=2)


class WhatsAppBotApp:
    def __init__(self, root):
        self.root = root
        self.step = None
        self.number = None
        self.message = None
        self.combined = None
        self.manager_tree = None
        self.startup_notice = None

        self.jobs = load_jobs()
        now = datetime.now()
        expired = [job for job in self.jobs if datetime.fromisoformat(job["due_at"]) <= now]
        if expired:
            self.jobs = [job for job in self.jobs if job not in expired]
            try:
                save_jobs(self.jobs)
            except OSError:
                pass
            self.startup_notice = (
                f"Removed {len(expired)} scheduled message(s) that expired while the app was closed."
            )

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
            "It asks for a number, the message,\n"
            "and how many times to repeat it.\n"
            "You can also schedule it for later.",
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

        self.schedule_button = ttk.Button(
            actions, text="Schedule...", command=self.open_schedule_dialog, state="disabled"
        )
        self.schedule_button.pack(side="left", padx=(8, 0))

        self.scheduled_button = ttk.Button(
            actions, text=f"Scheduled: {len(self.jobs)}", command=self.open_schedule_manager
        )
        self.scheduled_button.pack(side="left", padx=(8, 0))

        restart = ttk.Button(actions, text="Start Over", command=self.start_conversation)
        restart.pack(side="right")

        self.root.after(2000, self.check_due_jobs)

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
        self.schedule_button.config(state="disabled")
        self.entry.config(state="normal")
        self.send_button.config(state="normal")
        self.input_var.set("")

        self.append_bot(
            "Hi! Enter the WhatsApp number with country code (digits only, "
            "for example 919876543210):"
        )
        if self.startup_notice:
            self.append_bot(self.startup_notice)
            self.startup_notice = None
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
        self.schedule_button.config(state="normal")
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

    def persist_jobs(self):
        try:
            save_jobs(self.jobs)
        except OSError as exc:
            messagebox.showerror("Could not save schedule", str(exc))
        self.update_schedule_label()
        self.refresh_manager()

    def update_schedule_label(self):
        self.scheduled_button.config(text=f"Scheduled: {len(self.jobs)}")

    def open_schedule_dialog(self):
        if not self.number or not self.combined:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Schedule message")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)

        date_var = tk.StringVar(value=datetime.now().date().isoformat())
        time_var = tk.StringVar(value=(datetime.now() + timedelta(minutes=5)).strftime("%H:%M"))

        ttk.Label(frame, text=f"To: {self.number}").pack(anchor="w")
        preview = self.combined.splitlines()[0]
        if len(preview) > 48:
            preview = preview[:45] + "..."
        ttk.Label(frame, text=f"Message: {preview}").pack(anchor="w", pady=(2, 10))

        fields = ttk.Frame(frame)
        fields.pack(fill="x")
        ttk.Label(fields, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", pady=3)
        date_entry = ttk.Entry(fields, textvariable=date_var, width=16)
        date_entry.grid(row=0, column=1, sticky="w", pady=3, padx=(8, 0))
        ttk.Label(fields, text="Time (HH:MM):").grid(row=1, column=0, sticky="w", pady=3)
        time_entry = ttk.Entry(fields, textvariable=time_var, width=16)
        time_entry.grid(row=1, column=1, sticky="w", pady=3, padx=(8, 0))
        date_entry.focus_set()

        def confirm():
            try:
                due = parse_schedule(date_var.get(), time_var.get())
            except ValueError as exc:
                messagebox.showerror("Invalid date or time", str(exc), parent=dialog)
                return
            if due <= datetime.now():
                messagebox.showerror(
                    "Invalid date or time", "Choose a time in the future.", parent=dialog
                )
                return
            self.jobs.append(
                {
                    "id": str(uuid.uuid4()),
                    "number": self.number,
                    "text": self.combined,
                    "due_at": due.isoformat(),
                    "created_at": datetime.now().isoformat(),
                }
            )
            self.persist_jobs()
            self.append_bot(f"Scheduled for {due.strftime('%Y-%m-%d %H:%M')}.")
            dialog.destroy()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Schedule", command=confirm).pack(side="right", padx=(0, 8))

    def open_schedule_manager(self):
        if self.manager_tree is not None and self.manager_tree.winfo_exists():
            self.manager_tree.winfo_toplevel().lift()
            return

        window = tk.Toplevel(self.root)
        window.title("Scheduled messages")
        window.geometry("600x320")
        window.minsize(500, 240)

        body = ttk.Frame(window)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        tree = ttk.Treeview(
            body, columns=("when", "number", "message"), show="headings", height=8
        )
        tree.heading("when", text="When")
        tree.heading("number", text="Number")
        tree.heading("message", text="Message")
        tree.column("when", width=150, anchor="w")
        tree.column("number", width=130, anchor="w")
        tree.column("message", width=280, anchor="w")
        scroll = ttk.Scrollbar(body, command=tree.yview)
        tree.config(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.manager_tree = tree
        self.refresh_manager()

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(
            buttons, text="Cancel selected", command=lambda: self.cancel_selected_jobs(tree)
        ).pack(side="left")
        ttk.Button(
            buttons, text="Close", command=lambda: self.close_schedule_manager(window)
        ).pack(side="right")
        window.protocol("WM_DELETE_WINDOW", lambda: self.close_schedule_manager(window))

    def close_schedule_manager(self, window):
        self.manager_tree = None
        window.destroy()

    def refresh_manager(self):
        tree = self.manager_tree
        if tree is None or not tree.winfo_exists():
            self.manager_tree = None
            return
        for item in tree.get_children():
            tree.delete(item)
        for job in sorted(self.jobs, key=lambda entry: entry["due_at"]):
            due = datetime.fromisoformat(job["due_at"])
            preview = job["text"].splitlines()[0] if job["text"] else ""
            if len(preview) > 48:
                preview = preview[:45] + "..."
            tree.insert(
                "",
                "end",
                iid=job["id"],
                values=(due.strftime("%Y-%m-%d %H:%M"), job["number"], preview),
            )

    def cancel_selected_jobs(self, tree):
        selected = list(tree.selection())
        if not selected:
            return
        if not messagebox.askyesno(
            "Cancel scheduled messages",
            f"Remove {len(selected)} scheduled message(s)?",
            parent=tree.winfo_toplevel(),
        ):
            return
        self.jobs = [job for job in self.jobs if job["id"] not in selected]
        self.persist_jobs()
        self.append_bot(f"Cancelled {len(selected)} scheduled message(s).")

    def check_due_jobs(self):
        now = datetime.now()
        due = [job for job in self.jobs if datetime.fromisoformat(job["due_at"]) <= now]
        if due:
            self.jobs = [job for job in self.jobs if job not in due]
            self.persist_jobs()
            for job in due:
                self.fire_job(job)
        self.root.after(2000, self.check_due_jobs)

    def fire_job(self, job):
        self.show_notification(job)
        try:
            webbrowser.open(build_whatsapp_url(job["number"], job["text"]))
            self.append_bot(f"Scheduled message to {job['number']} is due. WhatsApp opened.")
        except Exception as exc:
            self.append_bot(
                f"Scheduled message to {job['number']} is due, "
                f"but WhatsApp could not be opened: {exc}"
            )

    def show_notification(self, job):
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        width, height = 380, 115
        x = self.root.winfo_screenwidth() - width - 20
        y = self.root.winfo_screenheight() - height - 60
        toast.geometry(f"{width}x{height}+{x}+{y}")

        frame = ttk.Frame(toast, relief="solid", borderwidth=1, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame, text="Scheduled message due", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        preview = job["text"].splitlines()[0] if job["text"] else ""
        if len(preview) > 52:
            preview = preview[:49] + "..."
        ttk.Label(frame, text=f"To: {job['number']}\n{preview}", wraplength=350).pack(
            anchor="w", pady=(4, 0)
        )
        ttk.Button(frame, text="Dismiss", command=toast.destroy).pack(anchor="e", pady=(6, 0))
        toast.after(15000, toast.destroy)


def main():
    root = tk.Tk()
    WhatsAppBotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
