import tkinter as tk
import time
import csv
from datetime import datetime
from tkinter import filedialog
import os
import traceback

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
        self.load_latest_csv()  # Load the latest CSV file upon starting
        self.update_window_size()

    def create_ui(self):
        self.total_time_label = tk.Label(self.root, text="Total Elapsed Time: 00:00:00")
        self.total_time_label.pack()

        self.add_button = tk.Button(self.root, text="Add Entry", command=self.add_entry)
        self.add_button.pack()

        self.load_button = tk.Button(self.root, text="Load from CSV", command=self.load_from_csv)
        self.load_button.pack()

        self.combine_button = tk.Button(self.root, text="Combine Selected", command=self.combine_selected_entries)
        self.combine_button.pack()

        time_frame = tk.Frame(self.root)
        time_frame.pack()

        time_label = tk.Label(time_frame, text="Time")
        time_label.pack(side=tk.LEFT)

        self.global_time_entry = tk.Entry(time_frame, width=10)
        self.global_time_entry.insert(0, "00:15:00")
        self.global_time_entry.pack(side=tk.LEFT)
        self.global_time_entry.bind("<MouseWheel>", self.scroll_time_entry)

        self.add_time_button = tk.Button(time_frame, text="+", command=self.add_time_to_selected)
        self.add_time_button.pack(side=tk.LEFT)

        self.remove_time_button = tk.Button(time_frame, text="-", command=self.remove_time_from_selected)
        self.remove_time_button.pack(side=tk.LEFT)

        self.csv_label = tk.Label(self.root, text="Active CSV: None")
        self.csv_label.pack()

    def add_time_to_selected(self):
        time_str = self.global_time_entry.get()
        if time_str:
            for entry in self.entries:
                if entry.selected.get():
                    entry.elapsed_time += entry.time_to_seconds(time_str)
                    entry.label.config(text=time.strftime("%H:%M:%S", time.gmtime(entry.elapsed_time)))
                    self.log_to_csv("Add Time", entry)
            self.save_to_csv()  # Save automatically
            self.update_total_time()

    def remove_time_from_selected(self):
        time_str = self.global_time_entry.get()
        if time_str:
            for entry in self.entries:
                if entry.selected.get():
                    entry.elapsed_time -= entry.time_to_seconds(time_str)
                    entry.label.config(text=time.strftime("%H:%M:%S", time.gmtime(entry.elapsed_time)))
                    self.log_to_csv("Remove Time", entry)
            self.save_to_csv()  # Save automatically
            self.update_total_time()

    def scroll_time_entry(self, event):
        current_time = self.global_time_entry.get()
        if not current_time:
            current_time = "00:00:00"
        h, m, s = map(int, current_time.split(":"))
        increment = 5 * 60  # 5 minutes in seconds
        total_seconds = h * 3600 + m * 60 + s

        if event.delta > 0:
            total_seconds += increment
        else:
            total_seconds -= increment

        h, remainder = divmod(total_seconds, 3600)
        m, s = divmod(remainder, 60)
        new_time = f"{h:02}:{m:02}:{s:02}"
        self.global_time_entry.delete(0, tk.END)
        self.global_time_entry.insert(0, new_time)

    def combine_selected_entries(self):
        selected_entries = [entry for entry in self.entries if entry.selected.get()]
        if not selected_entries:
            return

        combined_name = selected_entries[0].name_var.get()
        total_elapsed_time = sum(entry.elapsed_time for entry in selected_entries)

        for entry in selected_entries:
            self.log_to_csv("Remove", entry, comment=f"Merged into {combined_name}")
            self.remove_entry(entry, log_removal=False)

        combined_time_str = time.strftime("%H:%M:%S", time.gmtime(total_elapsed_time))
        new_entry = self.add_entry(name=combined_name, elapsed_time=combined_time_str)

        self.save_to_csv()
        self.log_to_csv("Combine", new_entry, comment="Combined entry")

    def update_total_time(self):
        total_seconds = sum(entry.elapsed_time for entry in self.entries)
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(total_seconds))
        self.total_time_label.config(text=f"Total Elapsed Time: {formatted_time}")

    def open_csv(self):
        today_date = datetime.today().strftime('%Y-%m-%d')
        expected_headers = ["Timestamp", "Action", "Name", "Elapsed Time", "Entry Date", "Comment"]
        csv_files = [f for f in os.listdir() if f.endswith("- time tracking.csv")]
        if csv_files:
            latest_file = max(csv_files, key=os.path.getctime)
            self.csv_file = open(latest_file, "a+", newline='')
            self.csv_label.config(text=f"Active CSV: {latest_file}")
            self.csv_file.seek(0)
            reader = csv.reader(self.csv_file)
            headers = next(reader, None)
            if headers != expected_headers:
                rows = list(reader)
                self.csv_file.close()
                self.csv_file = open(latest_file, "w", newline='')
                writer = csv.writer(self.csv_file)
                writer.writerow(expected_headers)
                for row in rows:
                    if len(row) < len(expected_headers):
                        row.extend([""] * (len(expected_headers) - len(row)))
                    writer.writerow(row)
        else:
            file_name = f"{self.first_entry_date or today_date} to {today_date} - time tracking.csv"
            self.csv_file = open(file_name, "a", newline='')
            self.csv_label.config(text=f"Active CSV: {file_name}")
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(expected_headers)
        self.csv_writer = csv.writer(self.csv_file)

    def log_to_csv(self, action, entry, comment=""):
        if self.csv_writer:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.csv_writer.writerow([timestamp, action, entry.name_var.get(),
                                      time.strftime("%H:%M:%S", time.gmtime(entry.elapsed_time)),
                                      entry.entry_date, comment])
            self.csv_file.flush()

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
        print("Loading latest CSV file...")
        csv_files = [f for f in os.listdir() if f.endswith("- time tracking.csv")]
        if csv_files:
            latest_file = max(csv_files, key=os.path.getctime)
            print(f"Latest CSV file found: {latest_file}")
            try:
                self.load_csv(latest_file)
                print("CSV file loaded successfully.")
            except Exception as e:
                print(f"Failed to load CSV file: {e}")
                self.open_csv()
        else:
            print("No CSV files found. Creating a new one.")
            self.open_csv()

    def load_csv(self, file_path):
        print(f"Loading CSV file: {file_path}")
        self.clear_entries()  # Clear current entries
        existing_entries = {(entry.name_var.get(), entry.entry_date) for entry in self.entries}
        try:
            with open(file_path, "r", newline='') as csv_file:
                self.csv_label.config(text=f"Active CSV: {file_path}")
                reader = csv.reader(csv_file)
                header = next(reader, None)  # Read header row
                if header is None:
                    print("CSV file is empty.")
                    return
                last_entries = {}
                for row in reader:
                    if len(row) == 6:
                        action, name, elapsed_time, entry_date, comment = row[1], row[2], row[3], row[4], row[5]
                        if action == "Remove":
                            if name in last_entries:
                                del last_entries[name]
                        else:
                            last_entries[name] = (elapsed_time, entry_date)
                for name, (elapsed_time, entry_date) in last_entries.items():
                    if (name, entry_date) not in existing_entries:
                        self.add_entry(name, elapsed_time, entry_date)
                self.update_total_time()
                self.update_window_size()  # Update window size to fit new entries
                print("CSV file loaded and UI updated.")
        except Exception as e:
            print(f"Failed to load CSV file: {e}")
            traceback.print_exc()

    def add_entry(self, name="", elapsed_time="00:00:00", entry_date=None):
        if not self.first_entry_date:
            self.first_entry_date = datetime.today().strftime('%Y-%m-%d')
        entry = StopwatchEntry(self.root, self)
        entry.set_values(name, elapsed_time, entry_date or self.first_entry_date)
        self.entries.append(entry)
        self.update_total_time()
        self.update_window_size()
        self.save_to_csv()  # Save automatically
        return entry  # Return the newly created entry

    def remove_entry(self, entry, log_removal=True):
        if self.active_entry == entry:
            self.active_entry = None
        entry.frame.destroy()
        self.entries.remove(entry)
        if log_removal:
            self.log_to_csv("Remove", entry)
        self.update_total_time()
        self.update_window_size()
        self.save_to_csv()  # Save automatically

    def clear_entries(self):
        for entry in self.entries:
            entry.frame.destroy()
        self.entries.clear()
        self.update_total_time()
        self.update_window_size()

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
        self.selected = tk.BooleanVar()

        self.frame = tk.Frame(self.parent, bg="white")
        self.frame.pack(pady=5, fill='x')

        self.checkbox = tk.Checkbutton(self.frame, variable=self.selected)
        self.checkbox.pack(side=tk.LEFT, padx=5)

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
