import tkinter as tk
import time
import csv
from datetime import datetime
from tkinter import filedialog
import os

class StopwatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")

        self.entries = []  # Store individual stopwatches
        self.active_entry = None  # Track the currently running stopwatch
        self.first_entry_date = None  # Track the first entry date
        self.csv_file = None  # CSV file handle
        self.create_ui()
        self.open_csv()
        self.load_latest_csv()
        self.update_window_size()

    def create_ui(self):
        self.total_time_label = tk.Label(self.root, text="Total Elapsed Time: 00:00:00")
        self.total_time_label.pack()

        self.add_button = tk.Button(self.root, text="Add Entry", command=self.add_entry)
        self.add_button.pack()

        self.load_button = tk.Button(self.root, text="Load from CSV", command=self.load_from_csv)
        self.load_button.pack()

        self.csv_label = tk.Label(self.root, text="Active CSV: None")
        self.csv_label.pack()

    def update_total_time(self):
        total_seconds = sum(entry.elapsed_time for entry in self.entries)
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(total_seconds))
        self.total_time_label.config(text=f"Total Elapsed Time: {formatted_time}")

    def open_csv(self):
        today_date = datetime.today().strftime('%Y-%m-%d')
        file_name = f"{self.first_entry_date or today_date} to {today_date} - time tracking.csv"
        self.csv_file = open(file_name, "a", newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_label.config(text=f"Active CSV: {file_name}")

    def log_to_csv(self, action, entry):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.csv_writer.writerow([timestamp, action, entry.name_var.get(), entry.label.cget("text"), entry.entry_date])
        self.csv_file.flush()

    def add_entry(self, name="", elapsed_time="00:00:00", entry_date=None):
        if not self.first_entry_date:
            self.first_entry_date = datetime.today().strftime('%Y-%m-%d')
        entry = StopwatchEntry(self.root, self)
        entry.set_values(name, elapsed_time, entry_date or self.first_entry_date)
        self.entries.append(entry)
        self.log_to_csv("Add Entry", entry)
        self.update_total_time()
        self.update_window_size()
        self.save_to_csv()  # Save automatically

    def add_entry_without_logging(self, name="", elapsed_time="00:00:00", entry_date=None):
        if not self.first_entry_date:
            self.first_entry_date = datetime.today().strftime('%Y-%m-%d')
        entry = StopwatchEntry(self.root, self)
        entry.set_values(name, elapsed_time, entry_date or self.first_entry_date)
        self.entries.append(entry)
        self.update_total_time()
        self.update_window_size()
        self.save_to_csv()  # Save automatically

    def remove_entry(self, entry):
        if self.active_entry == entry:
            self.active_entry = None
        entry.frame.destroy()
        self.entries.remove(entry)
        self.update_total_time()
        self.update_window_size()
        self.save_to_csv()  # Save automatically

    def save_to_csv(self):
        if not self.entries:
            return
        self.csv_file.close()
        self.open_csv()

    def load_from_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.load_csv(file_path)

    def load_latest_csv(self):
        csv_files = [f for f in os.listdir() if f.endswith("- time tracking.csv")]
        if csv_files:
            latest_file = max(csv_files, key=os.path.getctime)
            try:
                self.load_csv(latest_file)
            except Exception as e:
                print(f"Failed to load CSV file: {e}")
                self.open_csv()
        else:
            self.open_csv()

    def load_csv(self, file_path):
        try:
            with open(file_path, "r") as file:
                reader = csv.reader(file)
                header = next(reader)  # Skip header row
                for row in reader:
                    if len(row) == 5:
                        name, elapsed_time, entry_date = row[2], row[3], row[4]
                        existing_entry = None
                        for e in self.entries:
                            if e.name_var.get() == name:
                                existing_entry = e
                                break
                        if existing_entry:
                            existing_entry.elapsed_time = self.time_to_seconds(elapsed_time)
                            existing_entry.label.config(text=elapsed_time)
                        else:
                            self.add_entry_without_logging(name, elapsed_time, entry_date)
                self.csv_label.config(text=f"Active CSV: {os.path.abspath(file_path)}")
                self.update_total_time()
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            raise

    def update_window_size(self):
        self.root.update_idletasks()
        self.root.geometry(f"{self.root.winfo_reqwidth()}x{self.root.winfo_reqheight()}")

    def set_active_entry(self, entry):
        if self.active_entry and self.active_entry != entry:
            self.active_entry.stop()
        self.active_entry = entry
        entry.frame.config(bg="lightgreen")

    def set_inactive_entry(self, entry):
        if self.active_entry == entry:
            self.active_entry.frame.config(bg="white")
            self.active_entry = None

    def time_to_seconds(self, time_str):
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
class StopwatchEntry:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.running = False
        self.start_time = None
        self.elapsed_time = 0
        self.entry_date = datetime.today().strftime('%Y-%m-%d')

        self.frame = tk.Frame(self.parent, bg="white")
        self.frame.pack(pady=5, fill='x')

        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(self.frame, textvariable=self.name_var, width=20)
        self.name_entry.pack(side=tk.LEFT, padx=5)

        self.label = tk.Label(self.frame, text="00:00:00", width=10)
        self.label.pack(side=tk.LEFT)

        self.start_button = tk.Button(self.frame, text="Start", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(self.frame, text="Stop", command=self.stop)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = tk.Button(self.frame, text="Reset", command=self.reset)
        self.reset_button.pack(side=tk.LEFT, padx=5)

        self.remove_button = tk.Button(self.frame, text="Remove", command=self.remove)
        self.remove_button.pack(side=tk.LEFT, padx=5)

        self.custom_time_entry = tk.Entry(self.frame, width=10)
        self.custom_time_entry.pack(side=tk.LEFT, padx=5)

        self.add_time_button = tk.Button(self.frame, text="+Time", command=self.add_custom_time)
        self.add_time_button.pack(side=tk.LEFT, padx=5)

        self.app.update_window_size()

    def set_values(self, name, elapsed_time, entry_date):
        self.name_var.set(name)
        self.elapsed_time = self.time_to_seconds(elapsed_time)
        self.label.config(text=elapsed_time)
        self.entry_date = entry_date

    def start(self):
        if not self.running:
            self.app.set_active_entry(self)
            self.running = True
            self.start_time = time.time() - self.elapsed_time
            self.update()
            self.app.log_to_csv("Start", self)
            self.app.save_to_csv()  # Save automatically

    def stop(self):
        if self.running:
            self.running = False
            self.elapsed_time = time.time() - self.start_time
            self.app.set_inactive_entry(self)
            self.app.log_to_csv("Stop", self)
            self.app.save_to_csv()  # Save automatically

    def reset(self):
        self.running = False
        self.start_time = None
        self.elapsed_time = 0
        self.label.config(text="00:00:00")

    def remove(self):
        self.app.remove_entry(self)

    def update(self):
        if self.running:
            self.elapsed_time = time.time() - self.start_time
            formatted_time = time.strftime("%H:%M:%S", time.gmtime(self.elapsed_time))
            self.label.config(text=formatted_time)
            self.app.update_total_time()
            self.parent.after(1000, self.update)

    def add_custom_time(self):
        time_str = self.custom_time_entry.get()
        if time_str:
            self.elapsed_time += self.time_to_seconds(time_str)
            self.label.config(text=time.strftime("%H:%M:%S", time.gmtime(self.elapsed_time)))
            self.app.log_to_csv("Add Time", self)
            self.app.save_to_csv()  # Save automatically

    def time_to_seconds(self, time_str):
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s

if __name__ == "__main__":
    root = tk.Tk()
    app = StopwatchApp(root)
    root.mainloop()
