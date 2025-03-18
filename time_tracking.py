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
        self.root.title("Time Tracking")
        self.entries = {}
        self.active_entry = None
        self.rename_map = {}
        self.working_folder = os.getcwd()  # Set default working folder to the script's directory

        self.first_entry_date = None  # Track the first entry date
        self.csv_filename = None  # Track the current CSV file name
        self.csv_file = None  # CSV file handle
        self.csv_writer = None  # CSV writer object
        self.rename_map = {}  # Map entry IDs to base names
        self.entry_counter = 0  # Counter to generate unique IDs

        # Create a frame to hold the browse button and the dropdown
        self.browse_frame = tk.Frame(root)
        self.browse_frame.pack(pady=5)

        self.working_folder_var = tk.StringVar(value=self.working_folder)
        self.working_folder_entry = tk.Entry(self.browse_frame, textvariable=self.working_folder_var, width=50)
        self.working_folder_entry.pack(side=tk.LEFT, padx=5)

        self.browse_button = tk.Button(self.browse_frame, text="Browse", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT, padx=5)

        self.csv_var = tk.StringVar()
        self.csv_var.trace('w', self.on_csv_dropdown_change)  # Add trace to trigger function on value change
        self.csv_dropdown = tk.OptionMenu(self.browse_frame, self.csv_var, "")
        self.csv_dropdown.pack(side=tk.LEFT, padx=5)

        self.create_ui()
        self.update_csv_dropdown()  # Populate the dropdown with CSV files from the default folder
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

        self.save_simplified_button = tk.Button(self.root, text="Save Simplified CSV", command=self.save_simplified_csv)
        self.save_simplified_button.pack()

        self.new_entry_checkbox_var = tk.BooleanVar()
        self.new_entry_checkbox = tk.Checkbutton(self.root, text="Create new entry for every line", variable=self.new_entry_checkbox_var)
        self.new_entry_checkbox.pack()

        # Create a canvas and a scrollbar for the entries
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def refresh_ui(self):
        self.update_total_time()
        self.update_window_size()

    def add_time_to_selected(self):
        time_str = self.global_time_entry.get()
        if time_str:
            for entry in self.entries.values():
                if entry.selected.get():
                    entry.elapsed_time += entry.time_to_seconds(time_str)
                    entry.label.config(text=time.strftime("%H:%M:%S", time.gmtime(entry.elapsed_time)))
                    self.log_to_csv("Add Time", entry)
            self.refresh_ui()

    def remove_time_from_selected(self):
        time_str = self.global_time_entry.get()
        if time_str:
            for entry in self.entries.values():
                if entry.selected.get():
                    entry.elapsed_time -= entry.time_to_seconds(time_str)
                    entry.label.config(text=time.strftime("%H:%M:%S", time.gmtime(entry.elapsed_time)))
                    self.log_to_csv("Remove Time", entry)
            self.refresh_ui()

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
        selected_entries = [entry for entry in self.entries.values() if entry.selected.get()]
        if not selected_entries:
            return

        combined_name = selected_entries[0].name_var.get()
        total_elapsed_time = sum(entry.elapsed_time for entry in selected_entries)

        for entry in selected_entries:
            self.log_to_csv("Remove", entry, comment=f"Merged into {combined_name}")
            self.remove_entry(entry.id)

        combined_time_str = time.strftime("%H:%M:%S", time.gmtime(total_elapsed_time))
        new_entry = self.add_entry(name=combined_name, elapsed_time=combined_time_str)

        self.log_to_csv("Combine", new_entry, comment="Combined entry")

    def update_total_time(self):
        total_seconds = 0
        for entry_t in self.entries.values():
            total_seconds += entry_t.elapsed_time
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(total_seconds))
        self.total_time_label.config(text=f"Total Elapsed Time: {formatted_time}")

    def browse_folder(self):
        self.close_csv()
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.working_folder = folder_selected
            self.working_folder_var.set(self.working_folder)  # Update the text box
            self.update_csv_dropdown()

    def update_csv_dropdown(self):
        csv_files = [f for f in os.listdir(self.working_folder) if f.endswith('.csv')]
        menu = self.csv_dropdown['menu']
        menu.delete(0, 'end')
        today_date = datetime.today().strftime('%Y-%m-%d')
        default_csv = f"{today_date} - time tracking.csv"
        if default_csv not in csv_files:
            self.create_csv_file(default_csv)
            csv_files.append(default_csv)
        for csv_file in csv_files:
            menu.add_command(label=csv_file, command=lambda value=csv_file: self.csv_var.set(value))
        self.csv_var.set(default_csv)

    def on_csv_dropdown_change(self, *args):
        selected_csv = self.csv_var.get()
        print(f"CSV dropdown changed to: {selected_csv}")
        self.load_csv(selected_csv)

    def create_csv_file(self, file_name):
        file_path = os.path.join(self.working_folder, file_name)
        with open(file_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Timestamp", "Action", "Name", "Elapsed Time", "Entry Date", "Comment"])

    def open_csv(self, file_name):
        if self.csv_filename == file_name and self.csv_file and not self.csv_file.closed and self.csv_writer:
            print(f"CSV file {file_name} is already open.")
            return

        if self.csv_filename != file_name and self.csv_file and not self.csv_file.closed:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            print(f"Closed CSV file: {self.csv_filename}")

        available_files = [f for f in os.listdir(self.working_folder) if f.endswith("- time tracking.csv")]
        expected_headers = ["Timestamp", "Action", "Name", "Elapsed Time", "Entry Date", "Comment"]
        if file_name in available_files:
            open_path = os.path.join(self.working_folder, file_name)
            self.csv_file = open(open_path, "a+", newline='')
            reader = csv.reader(self.csv_file)
            self.csv_file.seek(0)

            headers = next(reader, None)
            if headers != expected_headers:
                rows = list(reader)
                self.csv_file.close()
                print(f"Invalid headers in CSV file: {headers}\nExpected: {expected_headers}")
                return
            print(f"Opened existing CSV file: {file_name}")
        else:
            self.csv_file = open(file_name, "a", newline='')
            csv.writer(self.csv_file).writerow(expected_headers)
            print(f"Created new CSV file: {file_name}")

        self.csv_writer = csv.writer(self.csv_file)
        self.csv_filename = file_name

    def close_csv(self):
        if self.csv_file and not self.csv_file.closed:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            print(f"Closed CSV file: {self.csv_filename}")

    def log_to_csv(self, action, entry, comment=""):
        if self.csv_writer:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.csv_writer.writerow([timestamp, action, entry.name_var.get(),
                                      time.strftime("%H:%M:%S", time.gmtime(entry.elapsed_time)),
                                      entry.entry_date, comment])
            self.csv_file.flush()
        else:
            print(f"CSV file is not open. Cannot log action: {action}")

    def load_from_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.load_csv(file_path)

    def load_csv(self, file_path):
        selected_csv = self.csv_var.get()
        if selected_csv:
            self.open_csv(selected_csv)
            if not self.csv_writer:
                print("Cannot log due to failure to open CSV file.")
                return

            print(f"Loading CSV file: {file_path}")
            if not self.new_entry_checkbox_var.get():
                self.clear_entries()  # Clear current entries

            existing_entries = {(entry.name_var.get(), entry.entry_date) for entry in self.entries.values()}
            try:
                #Set cursor to the beginning of the file
                self.csv_file.seek(0)
                reader = csv.reader(self.csv_file)
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
                        elif action == "Rename":
                            #TODO revoir le rename
                            new_name, old_name = name, comment.split("Renamed from ")[1]
                            if old_name in last_entries:
                                del last_entries[old_name]
                                last_entries[new_name] = (elapsed_time, entry_date)
                        elif name == '':
                            print(f"Skipping row with missing name: {row}")
                        else:
                            last_entries[name] = (elapsed_time, entry_date)
                    else:
                        print(f"Skipping row with invalid data formatting: {row}")

                for name, (elapsed_time, entry_date) in last_entries.items():
                    if ((name, entry_date) not in existing_entries) or self.new_entry_checkbox_var.get():
                        self.add_entry(name, elapsed_time, entry_date)
                self.refresh_ui()
                print("CSV file loaded and UI updated.")
            except Exception as e:
                print(f"Failed to load CSV file: {e}")
                traceback.print_exc()

    def save_simplified_csv(self):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        simplified_file_name = f"{timestamp} simplified - time tracking.csv"
        simplified_file_path = os.path.join(self.working_folder, simplified_file_name)
        with open(simplified_file_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Timestamp", "Action", "Name", "Elapsed Time", "Entry Date", "Comment"])
            for entry in self.entries.values():
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Latest Status", entry.name_var.get(),
                                 time.strftime("%H:%M:%S", time.gmtime(entry.elapsed_time)), entry.entry_date, ""])
        print(f"Simplified CSV saved to {simplified_file_path}")

    def add_entry(self, name="", elapsed_time="00:00:00", entry_date=None):
        if not self.first_entry_date:
            self.first_entry_date = datetime.today().strftime('%Y-%m-%d')
        entry_id = self.entry_counter
        self.entry_counter += 1
        entry = StopwatchEntry(self.scrollable_frame, self, entry_id)
        entry.set_values(name, elapsed_time, entry_date or self.first_entry_date)
        self.entries[entry_id] = entry  # Store the entry by its ID
        self.rename_map[entry_id] = name  # Add the entry ID to the rename_map
        self.refresh_ui()
        return entry  # Return the newly created entry

    def remove_entry(self, entry_id):
        entry = self.entries.pop(entry_id, None)
        if entry:
            if self.active_entry == entry:
                self.active_entry = None
            entry.frame.destroy()
            self.log_to_csv("Remove", entry)
            self.refresh_ui()

    def clear_entries(self):
        for entry in self.entries.values():
            entry.frame.destroy()
        self.entries.clear()
        self.refresh_ui()

    def update_window_size(self):
        name_length = 0
        if len(self.entries) != 0:
            self.root.update_idletasks()  # Ensure all widgets are updated
            for entry in self.entries.values():
                name_length = max(name_length, len(entry.name_var.get()))
            for entry in self.entries.values():
                entry.name_entry.config(width=name_length + 2)  # Add some padding
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
    def __init__(self, parent, app, entry_id):
        self.parent = parent
        self.app = app
        self.id = entry_id  # Unique ID for the entry
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

        self.rename_button = tk.Button(self.frame, text="Rename", command=self.rename)
        self.rename_button.pack(side=tk.LEFT, padx=5)

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

    def stop(self):
        if self.running:
            self.running = False
            self.elapsed_time = time.time() - self.start_time
            self.app.set_inactive_entry(self)
            self.app.log_to_csv("Stop", self)


    def reset(self):
        self.running = False
        self.start_time = None
        self.elapsed_time = 0
        self.label.config(text="00:00:00")

    def remove(self):
        self.app.remove_entry(self)

    # Update the rename method in the StopwatchEntry class
    def rename(self):
        entry_id = self.id
        base_name = self.app.rename_map.get(entry_id, self.name_var.get())
        new_name = self.name_entry.get()
        self.app.log_to_csv("Rename", self, comment=f"Renamed from {base_name}")
        self.name_var.set(new_name)

    def update(self):
        if self.running:
            self.elapsed_time = time.time() - self.start_time
            formatted_time = time.strftime("%H:%M:%S", time.gmtime(self.elapsed_time))
            self.label.config(text=formatted_time)
            self.app.refresh_ui()
            self.parent.after(1000, self.update)

    def add_custom_time(self):
        time_str = self.custom_time_entry.get()
        if time_str:
            self.elapsed_time += self.time_to_seconds(time_str)
            self.label.config(text=time.strftime("%H:%M:%S", time.gmtime(self.elapsed_time)))
            self.app.log_to_csv("Add Time", self)

    def time_to_seconds(self, time_str):
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s

if __name__ == "__main__":
    root = tk.Tk()
    app = StopwatchApp(root)
    root.mainloop()
