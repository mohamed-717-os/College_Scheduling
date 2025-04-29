import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
import time
import threading

# Import the logic file (assumed to be scheduler_logic.py)
from scheduelModel import scheduelModel 

class Tooltip:
    """A class to create tooltips for widgets that appear on hover."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        """Display the tooltip when the mouse hovers over the widget."""
        if self.tooltip:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip, text=self.text, background="#FFF9C4", relief="solid", borderwidth=1)
        label.pack()
        self.tooltip.after(3000, self.hide_tooltip)

    def hide_tooltip(self, event=None):
        """Hide the tooltip when the mouse leaves the widget."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class PreferenceDialog:
    """A dialog to set time preferences for assistants and doctors."""
    def __init__(self, parent, days, periods, title, existing_prefs=None):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("400x300")
        self.days = list(range(1, days + 1))
        self.periods = list(range(1, periods + 1))
        
        # Initialize preferences with existing values if provided, else default to True
        self.preferences = {}
        if existing_prefs is not None:
            for d in self.days:
                for p in self.periods:
                    # Use existing preference if available, otherwise default to True
                    self.preferences[(d, p)] = tk.BooleanVar(value=bool(existing_prefs.get((d, p), 1)))
        else:
            self.preferences = {(d, p): tk.BooleanVar(value=True) for d in self.days for p in self.periods}
        
        # Create a grid of checkboxes for each day and period
        ttk.Label(self.top, text="Select preferred days and periods:").pack(pady=5)
        frame = ttk.Frame(self.top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header for periods
        ttk.Label(frame, text="Day").grid(row=0, column=0, padx=5, pady=5)
        for p in self.periods:
            ttk.Label(frame, text=f"P{p}").grid(row=0, column=p, padx=5, pady=5)
        
        # Checkboxes for each day and period
        for d in self.days:
            ttk.Label(frame, text=f"Day {d}").grid(row=d, column=0, padx=5, pady=5)
            for p in self.periods:
                chk = ttk.Checkbutton(frame, variable=self.preferences[(d, p)])
                chk.grid(row=d, column=p, padx=5, pady=5)
        
        # Buttons
        ttk.Button(self.top, text="Save", command=self.save).pack(pady=10)
        
        ttk.Button(self.top, text="Reset", command=self.reset).pack(pady=5)
        
        ttk.Button(self.top, text="Cancel", command=self.top.destroy).pack(pady=5)
        self.result = None

    def save(self):
        """Save the selected preferences as a dictionary."""
        self.result = {(d, p): 1 if self.preferences[(d, p)].get() else 0 for d in self.days for p in self.periods}
        self.top.destroy()

    def reset(self):
        """Reset all time preferences to the default value (True)."""
        for d in self.days:
            for p in self.periods:
                self.preferences[(d, p)].set(True)

class SubjectPreferenceDialog:
    """A dialog to set subject preferences for assistants and doctors."""
    def __init__(self, parent, subjects, title, existing_prefs=None):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("300x400")
        self.subjects = subjects
        
        # Initialize preferences with existing values if provided, else default to False
        self.preferences = {}
        if existing_prefs is not None:
            for s in self.subjects:
                # Use existing preference if available, otherwise default to False
                self.preferences[s] = tk.BooleanVar(value=bool(existing_prefs.get(s, 0)))
        else:
            self.preferences = {s: tk.BooleanVar(value=False) for s in subjects}
        
        # Create a list of checkboxes for each subject
        ttk.Label(self.top, text="Select preferred subjects:").pack(pady=5)
        frame = ttk.Frame(self.top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for idx, s in enumerate(self.subjects):
            chk = ttk.Checkbutton(frame, text=s, variable=self.preferences[s])
            chk.pack(anchor="w", padx=5, pady=2)
        
        # Buttons
        ttk.Button(self.top, text="Save", command=self.save).pack(pady=10)
        
        ttk.Button(self.top, text="Reset", command=self.reset).pack(pady=5)
        
        ttk.Button(self.top, text="Cancel", command=self.top.destroy).pack(pady=5)
        self.result = None

    def save(self):
        """Save the selected subject preferences as a dictionary."""
        self.result = {s: 1 if self.preferences[s].get() else 0 for s in self.subjects}
        self.top.destroy()

    def reset(self):
        """Reset all subject preferences to the default value (False)."""
        for s in self.subjects:
            self.preferences[s].set(False)

class SchedulingApp:
    """Main application class for collecting scheduling inputs."""
    def __init__(self, root):
        """Initialize the application with default values and setup the UI."""
        self.root = root
        self.root.title("College Scheduling Inputs")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)
        self.root.resizable(True, True)
        self.root.configure(bg="#F5F5F5")

        # Initialize variables for basic parameters
        self.halls = tk.StringVar(value="4")
        self.labs = tk.StringVar(value="9")
        self.days = tk.StringVar(value="5")
        self.periods = tk.StringVar(value="5")

        # Variables for assistant and doctor workload limits (AL and TL)
        self.assistant_max_periods = tk.StringVar(value="8")
        self.assistant_max_subjects = tk.StringVar(value="3")
        self.doctor_max_periods = tk.StringVar(value="5")
        self.doctor_max_subjects = tk.StringVar(value="3")

        # Initialize data structures
        self.environments = []
        self.groups = {}
        self.classes = {}
        self.subjects = {}
        self.assistants = {}  # {env: [assistants]} for UI purposes
        self.doctors = {}    # {env: [doctors]} for UI purposes
        # Flat dictionaries for preferences
        self.assistant_time_prefs = {}    # {assistant: {(d, p): 1 or 0}}
        self.doctor_time_prefs = {}       # {doctor: {(d, p): 1 or 0}}
        self.assistant_subject_prefs = {} # {assistant: {s: 1 or 0}}
        self.doctor_subject_prefs = {}    # {doctor: {s: 1 or 0}}

        self.setup_ui()

    def validate_positive_integer(self, value):
        """Validate that the input is a positive integer."""
        if value == "":
            return True
        try:
            val = int(value)
            return val > 0
        except ValueError:
            return False

    def check_entry(self, entry, var):
        """Update the entry widget's style based on input validation."""
        value = var.get()
        if self.validate_positive_integer(value):
            entry.configure(style="TEntry")
        else:
            entry.configure(style="Invalid.TEntry")

    def setup_ui(self):
        """Set up the user interface with a two-column layout."""
        # Configure styles for UI elements
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Custom.TLabelframe.Label", font=("Helvetica", 14, "bold"))

        style.configure(
            "Custom.TButton",
            font=("Helvetica", 10, "normal")
        )
        style.map(
            "Custom.TButton",
            foreground=[
                ('pressed', 'white'),
                ('active',  'white'),
                ('!disabled', 'black')
            ],
            background=[
                ('pressed', '#2b8ac4'),   # darker when pressed
                ('active',  '#3399ff'),   # lighter on hover
                ('!disabled', '#44a6fc')  # normal
            ]
        )
        
        style.configure("Add.TButton", background="#4CAF50", foreground="#4CAF50")
        style.map("Add.TButton",
            foreground=[('active', 'white'), ('!disabled', 'white')],
            background=[('active', '#45A049'), ('!disabled', '#4CAF50')]
        )

        style.configure(
            "Delete.TButton",
            font=("Helvetica", 10, "normal")
        )
        style.map(
            "Delete.TButton",
            foreground=[
                ('pressed', 'white'),
                ('active',  'white'),
                ('!disabled', 'black')
            ],
            background=[
                ('pressed', '#c62828'),
                ('active',  '#e57373'),
                ('!disabled', '#f44336')
            ]
        )

        style.configure(
            "Save.TButton",
            font=("Helvetica", 10, "normal")
        )
        style.map(
            "Save.TButton",
            foreground=[
                ('pressed', 'white'),
                ('active',  'white'),
                ('!disabled', 'black')
            ],
            background=[
                ('pressed', '#1565c0'),
                ('active',  '#64b5f6'),
                ('!disabled', '#44a6fc')
            ]
        )

        style.configure(
            "Generate.TButton",
            background="#FF9800",
            foreground="#FF9800")
        
        style.map(
            "Generate.TButton",
            foreground=[
                ('pressed', 'white'),
                ('active',  'white'),
                ('!disabled', 'black')
            ],
            background=[
                ('pressed', '#FF9800'),
                ('active',  '#FF9800'),
                ('!disabled', '#FF9800')
            ]
        )


        style.configure(
            "Invalid.TEntry",
            fieldbackground="#FFEBEE",
            font=("Helvetica", 10)
        )
        style.map(
            "Invalid.TEntry",
            fieldbackground=[
                ('focus',   '#FFEBEE'),
                ('!focus',  'white')
            ]
        )

        style.configure("TLabel", font=("Helvetica", 11))

        # Create a scrollable canvas
        canvas = tk.Canvas(self.root, bg="#F5F5F5")
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Set up a two-column layout
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, padx=(0, 20), sticky=(tk.N, tk.S))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Basic Parameters Frame (Left Column)
        param_frame = ttk.LabelFrame(left_frame, text="📋 Basic Parameters", padding="15", style="Custom.TLabelframe")
        param_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        param_frame.configure(borderwidth=2, relief="groove")

        ttk.Label(param_frame, text="Halls:", style="TLabel").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        halls_entry = ttk.Entry(param_frame, textvariable=self.halls, width=10, state="normal")
        halls_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.halls.trace("w", lambda *args: self.check_entry(halls_entry, self.halls))
        Tooltip(halls_entry, "Number of lecture halls available")

        ttk.Label(param_frame, text="Labs:", style="TLabel").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        labs_entry = ttk.Entry(param_frame, textvariable=self.labs, width=10, state="normal")
        labs_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.labs.trace("w", lambda *args: self.check_entry(labs_entry, self.labs))
        Tooltip(labs_entry, "Number of labs available")

        ttk.Label(param_frame, text="Days:", style="TLabel").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        days_entry = ttk.Entry(param_frame, textvariable=self.days, width=10, state="normal")
        days_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.days.trace("w", lambda *args: self.check_entry(days_entry, self.days))
        Tooltip(days_entry, "Number of days per week (1-7)")

        ttk.Label(param_frame, text="Periods:", style="TLabel").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        periods_entry = ttk.Entry(param_frame, textvariable=self.periods, width=10, state="normal")
        periods_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        self.periods.trace("w", lambda *args: self.check_entry(periods_entry, self.periods))
        Tooltip(periods_entry, "Number of periods per day (1-10)")

        # Environments Frame (Left Column)
        env_frame = ttk.LabelFrame(left_frame, text="🌍 Environments", padding="15", style="Custom.TLabelframe")
        env_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        env_frame.configure(borderwidth=2, relief="groove")

        self.env_listbox = tk.Listbox(env_frame, height=4, exportselection=False, width=30)
        self.env_listbox.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        if not self.environments:
            self.env_listbox.insert(tk.END, "Add an environment to start...")

        add_env_btn = ttk.Button(env_frame, text="➕ Add", command=self.add_environment, style="Add.TButton")
        add_env_btn.grid(row=1, column=0, padx=5, pady=5)
        Tooltip(add_env_btn, "Add a new environment (e.g., year3)")

        delete_env_btn = ttk.Button(env_frame, text="🗑 Delete", command=self.delete_environment, style="Delete.TButton")
        delete_env_btn.grid(row=1, column=1, padx=5, pady=5)
        Tooltip(delete_env_btn, "Delete the selected environment")

        add_group_btn = ttk.Button(env_frame, text="➕ Add Group", command=self.add_group, style="Add.TButton")
        add_group_btn.grid(row=1, column=2, padx=5, pady=5)
        Tooltip(add_group_btn, "Add a group to the selected environment")

        # Subjects Frame (Left Column)
        subject_frame = ttk.LabelFrame(left_frame, text="📚 Subjects", padding="15", style="Custom.TLabelframe")
        subject_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        subject_frame.configure(borderwidth=2, relief="groove")

        self.subject_listbox = tk.Listbox(subject_frame, height=4, width=30)
        self.subject_listbox.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        add_subject_btn = ttk.Button(subject_frame, text="➕ Add", command=self.add_subject, style="Add.TButton")
        add_subject_btn.grid(row=1, column=0, padx=5, pady=5)
        Tooltip(add_subject_btn, "Add a subject to the selected environment")

        delete_subject_btn = ttk.Button(subject_frame, text="🗑 Delete", command=self.delete_subject, style="Delete.TButton")
        delete_subject_btn.grid(row=1, column=1, padx=5, pady=5)
        Tooltip(delete_subject_btn, "Delete the selected subject")

        # Groups and Classes Frame (Right Column)
        group_frame = ttk.LabelFrame(right_frame, text="👥 Groups and Classes", padding="15", style="Custom.TLabelframe")
        group_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        group_frame.configure(borderwidth=2, relief="groove")

        self.group_listbox = tk.Listbox(group_frame, height=4, exportselection=False, width=30)
        self.group_listbox.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        delete_group_btn = ttk.Button(group_frame, text="🗑 Delete Group", command=self.delete_group, style="Delete.TButton")
        delete_group_btn.grid(row=1, column=0, padx=5, pady=5)
        Tooltip(delete_group_btn, "Delete the selected group")

        add_class_btn = ttk.Button(group_frame, text="➕ Add Class", command=self.add_class, style="Add.TButton")
        add_class_btn.grid(row=1, column=1, padx=5, pady=5)
        Tooltip(add_class_btn, "Add a class to the selected group")

        self.class_listbox = tk.Listbox(group_frame, height=4, width=30)
        self.class_listbox.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        delete_class_btn = ttk.Button(group_frame, text="🗑 Delete Class", command=self.delete_class, style="Delete.TButton")
        delete_class_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        Tooltip(delete_class_btn, "Delete the selected class")

        # Assistants and Doctors Frame (Right Column)
        staff_frame = ttk.LabelFrame(right_frame, text="👨‍🏫 Assistants and Doctors", padding="15", style="Custom.TLabelframe")
        staff_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        staff_frame.configure(borderwidth=2, relief="groove")

        # Assistants Section
        ttk.Label(staff_frame, text="Assistants:", style="TLabel").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.assistant_listbox = tk.Listbox(staff_frame, height=4, width=20)
        self.assistant_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Add fields for assistant workload limits (AL)
        ttk.Label(staff_frame, text="Assistant Max Periods:", style="TLabel").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        assistant_periods_entry = ttk.Entry(staff_frame, textvariable=self.assistant_max_periods, width=10, state="normal")
        assistant_periods_entry.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.assistant_max_periods.trace("w", lambda *args: self.check_entry(assistant_periods_entry, self.assistant_max_periods))
        Tooltip(assistant_periods_entry, "Max periods per assistant per week")

        ttk.Label(staff_frame, text="Assistant Max Subjects:", style="TLabel").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        assistant_subjects_entry = ttk.Entry(staff_frame, textvariable=self.assistant_max_subjects, width=10, state="normal")
        assistant_subjects_entry.grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.assistant_max_subjects.trace("w", lambda *args: self.check_entry(assistant_subjects_entry, self.assistant_max_subjects))
        Tooltip(assistant_subjects_entry, "Max subjects per assistant")

        add_assistant_btn = ttk.Button(staff_frame, text="➕ Add", command=self.add_assistant, style="Add.TButton")
        add_assistant_btn.grid(row=6, column=0, padx=5, pady=5)
        Tooltip(add_assistant_btn, "Add a new teaching assistant to the selected environment")

        set_assistant_time_prefs_btn = ttk.Button(staff_frame, text="⏰ Set Time Preferences", command=self.set_assistant_time_preferences, style="Custom.TButton")
        set_assistant_time_prefs_btn.grid(row=7, column=0, padx=5, pady=5)
        Tooltip(set_assistant_time_prefs_btn, "Set preferred days and periods for the selected assistant")

        set_assistant_subject_prefs_btn = ttk.Button(staff_frame, text="📚 Set Subject Preferences", command=self.set_assistant_subject_preferences, style="Custom.TButton")
        set_assistant_subject_prefs_btn.grid(row=8, column=0, padx=5, pady=5)
        Tooltip(set_assistant_subject_prefs_btn, "Set preferred subjects for the selected assistant")

        delete_assistant_btn = ttk.Button(staff_frame, text="🗑 Delete", command=self.delete_assistant, style="Delete.TButton")
        delete_assistant_btn.grid(row=9, column=0, padx=5, pady=5)
        Tooltip(delete_assistant_btn, "Delete the selected assistant")

        # Doctors Section
        ttk.Label(staff_frame, text="Doctors:", style="TLabel").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.doctor_listbox = tk.Listbox(staff_frame, height=4, width=20)
        self.doctor_listbox.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Add fields for doctor workload limits (TL)
        ttk.Label(staff_frame, text="Doctor Max Periods:", style="TLabel").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        doctor_periods_entry = ttk.Entry(staff_frame, textvariable=self.doctor_max_periods, width=10, state="normal")
        doctor_periods_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        self.doctor_max_periods.trace("w", lambda *args: self.check_entry(doctor_periods_entry, self.doctor_max_periods))
        Tooltip(doctor_periods_entry, "Max periods per doctor per week")

        ttk.Label(staff_frame, text="Doctor Max Subjects:", style="TLabel").grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        doctor_subjects_entry = ttk.Entry(staff_frame, textvariable=self.doctor_max_subjects, width=10, state="normal")
        doctor_subjects_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        self.doctor_max_subjects.trace("w", lambda *args: self.check_entry(doctor_subjects_entry, self.doctor_max_subjects))
        Tooltip(doctor_subjects_entry, "Max subjects per doctor")

        add_doctor_btn = ttk.Button(staff_frame, text="➕ Add", command=self.add_doctor, style="Add.TButton")
        add_doctor_btn.grid(row=6, column=1, padx=5, pady=5)
        Tooltip(add_doctor_btn, "Add a new doctor to the selected environment")

        set_doctor_time_prefs_btn = ttk.Button(staff_frame, text="⏰ Set Time Preferences", command=self.set_doctor_time_preferences, style="Custom.TButton")
        set_doctor_time_prefs_btn.grid(row=7, column=1, padx=5, pady=5)
        Tooltip(set_doctor_time_prefs_btn, "Set preferred days and periods for the selected doctor")

        set_doctor_subject_prefs_btn = ttk.Button(staff_frame, text="📚 Set Subject Preferences", command=self.set_doctor_subject_preferences, style="Custom.TButton")
        set_doctor_subject_prefs_btn.grid(row=8, column=1, padx=5, pady=5)
        Tooltip(set_doctor_subject_prefs_btn, "Set preferred subjects for the selected doctor")

        delete_doctor_btn = ttk.Button(staff_frame, text="🗑 Delete", command=self.delete_doctor, style="Delete.TButton")
        delete_doctor_btn.grid(row=9, column=1, padx=5, pady=5)
        Tooltip(delete_doctor_btn, "Delete the selected doctor")

        # Action Buttons (Right Column)
        action_frame = ttk.Frame(right_frame)
        action_frame.grid(row=2, column=0, pady=20)

        save_btn = ttk.Button(action_frame, text="💾 Save Inputs", command=self.save_inputs, style="Save.TButton")
        save_btn.grid(row=0, column=0, padx=10)
        Tooltip(save_btn, "Save all inputs to a JSON file")

        clear_btn = ttk.Button(action_frame, text="Clear All Inputs", command=self.clear_inputs, style="Custom.TButton")
        clear_btn.grid(row=0, column=1, padx=10)
        Tooltip(clear_btn, "Reset all inputs to default values")

        load_btn = ttk.Button(action_frame, text="Browse Inputs", command=self.browse_inputs, style="Custom.TButton")
        load_btn.grid(row=0, column=2, padx=10)
        Tooltip(load_btn, "Browse and load inputs from a JSON file")

        generate_btn = ttk.Button(action_frame, text="🚀 Generate Schedules", command=self.generate_schedules, style="Generate.TButton")
        generate_btn.grid(row=0, column=3, padx=10)
        Tooltip(generate_btn, "Generate schedules using the input data")

        self.env_listbox.bind('<<ListboxSelect>>', self.update_groups)

    def clear_inputs(self):
        """Reset all input fields and data structures to their default state."""
        self.halls.set("4")
        self.labs.set("9")
        self.days.set("5")
        self.periods.set("5")
        self.assistant_max_periods.set("8")
        self.assistant_max_subjects.set("3")
        self.doctor_max_periods.set("5")
        self.doctor_max_subjects.set("3")
        self.environments = []
        self.groups = {}
        self.classes = {}
        self.subjects = {}
        self.assistants = {}
        self.doctors = {}
        self.assistant_time_prefs = {}
        self.doctor_time_prefs = {}
        self.assistant_subject_prefs = {}
        self.doctor_subject_prefs = {}

        self.env_listbox.delete(0, tk.END)
        self.env_listbox.insert(tk.END, "Add an environment to start...")
        self.group_listbox.delete(0, tk.END)
        self.class_listbox.delete(0, tk.END)
        self.subject_listbox.delete(0, tk.END)
        self.assistant_listbox.delete(0, tk.END)
        self.doctor_listbox.delete(0, tk.END)

    def browse_inputs(self):
        """Open a file dialog to select a JSON file and load its contents."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select JSON File",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            if not file_path:
                return  # User canceled the dialog

            with open(file_path, "r") as f:
                data = json.load(f)

            # Populate basic parameters
            self.halls.set(str(data.get("halls", 4)))
            self.labs.set(str(data.get("labs", 9)))
            self.days.set(str(data.get("days", 5)))
            self.periods.set(str(data.get("periods", 5)))
            self.assistant_max_periods.set(str(data.get("AL", [8, 3])[0]))
            self.assistant_max_subjects.set(str(data.get("AL", [8, 3])[1]))
            self.doctor_max_periods.set(str(data.get("TL", [5, 3])[0]))
            self.doctor_max_subjects.set(str(data.get("TL", [5, 3])[1]))

            # Load environments, groups, and subjects
            self.environments = data.get("environments", [])
            self.groups = data.get("groups", {})
            self.subjects = data.get("subjects", {})

            # Reconstruct classes to match the {env: {group: [classes]}} format
            flat_classes = data.get("classes", {})
            self.classes = {env: {} for env in self.environments}
            for env in self.environments:
                for group in self.groups.get(env, []):
                    # Assign classes for the group, default to empty list if not found
                    self.classes[env][group] = flat_classes.get(group, [])

            # Initialize assistants and doctors dictionaries
            self.assistants = {env: [] for env in self.environments}
            self.doctors = {env: [] for env in self.environments}

            # Populate assistants and doctors, mapping them to environments
            loaded_assistants = data.get("A", [])
            loaded_doctors = data.get("T", [])
            # For simplicity, distribute assistants and doctors based on subject preferences
            for env in self.environments:
                env_subjects = set(self.subjects.get(env, []))
                for assistant in loaded_assistants:
                    # Check if assistant has preferences for any subjects in this environment
                    assistant_prefs = data.get("AS", {}).get(assistant, {})
                    if any(subject in env_subjects and assistant_prefs.get(subject, 0) == 1 for subject in assistant_prefs):
                        self.assistants[env].append(assistant)
                for doctor in loaded_doctors:
                    # Check if doctor has preferences for any subjects in this environment
                    doctor_prefs = data.get("TS", {}).get(doctor, {})
                    if any(subject in env_subjects and doctor_prefs.get(subject, 0) == 1 for subject in doctor_prefs):
                        self.doctors[env].append(doctor)

            # Load and convert time preferences (AT and TT)
            self.assistant_time_prefs = {}
            self.doctor_time_prefs = {}
            for assistant in loaded_assistants:
                at_prefs = data.get("AT", {}).get(assistant, {})
                self.assistant_time_prefs[assistant] = {
                    (day, period): at_prefs.get(str(day), {}).get(str(period), 0)
                    for day in range(1, int(self.days.get()) + 1)
                    for period in range(1, int(self.periods.get()) + 1)
                }
            for doctor in loaded_doctors:
                tt_prefs = data.get("TT", {}).get(doctor, {})
                self.doctor_time_prefs[doctor] = {
                    (day, period): tt_prefs.get(str(day), {}).get(str(period), 0)
                    for day in range(1, int(self.days.get()) + 1)
                    for period in range(1, int(self.periods.get()) + 1)
                }

            # Load subject preferences (AS and TS)
            self.assistant_subject_prefs = data.get("AS", {})
            self.doctor_subject_prefs = data.get("TS", {})

            # Populate the environment listbox
            self.env_listbox.delete(0, tk.END)
            for env in self.environments:
                self.env_listbox.insert(tk.END, env)
            if not self.environments:
                self.env_listbox.insert(tk.END, "Add an environment to start...")

            # Clear other listboxes
            self.group_listbox.delete(0, tk.END)
            self.class_listbox.delete(0, tk.END)
            self.subject_listbox.delete(0, tk.END)
            self.assistant_listbox.delete(0, tk.END)
            self.doctor_listbox.delete(0, tk.END)

            # Update UI if an environment is selected
            if self.environments and self.env_listbox.size() > 0:
                self.env_listbox.select_set(0)  # Select the first environment
                self.update_groups(None)  # Trigger UI update

            messagebox.showinfo("Success", "Inputs loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading inputs: {str(e)}")

    def add_environment(self):
        """Add a new environment to the list and initialize its data structures."""
        env = simpledialog.askstring("Input", "Enter new environment name:")
        if env and env not in self.environments:
            self.environments.append(env)
            self.groups[env] = []
            self.classes[env] = {}
            self.subjects[env] = []
            self.assistants[env] = []
            self.doctors[env] = []
            if self.env_listbox.get(0) == "Add an environment to start...":
                self.env_listbox.delete(0)
            self.env_listbox.insert(tk.END, env)

    def delete_environment(self):
        """Delete the selected environment and its associated data."""
        selected = self.env_listbox.curselection()
        if not selected or self.env_listbox.get(selected[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Please select an environment to delete!")
            return
        env = self.env_listbox.get(selected[0])
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete environment '{env}'?"):
            # Remove associated assistants and doctors
            for assistant in self.assistants[env]:
                if assistant in self.assistant_time_prefs:
                    del self.assistant_time_prefs[assistant]
                if assistant in self.assistant_subject_prefs:
                    del self.assistant_subject_prefs[assistant]
            for doctor in self.doctors[env]:
                if doctor in self.doctor_time_prefs:
                    del self.doctor_time_prefs[doctor]
                if doctor in self.doctor_subject_prefs:
                    del self.doctor_subject_prefs[doctor]
            self.environments.remove(env)
            del self.groups[env]
            del self.classes[env]
            del self.subjects[env]
            del self.assistants[env]
            del self.doctors[env]
            self.env_listbox.delete(selected[0])
            if not self.environments:
                self.env_listbox.insert(tk.END, "Add an environment to start...")
            self.group_listbox.delete(0, tk.END)
            self.class_listbox.delete(0, tk.END)
            self.subject_listbox.delete(0, tk.END)
            self.assistant_listbox.delete(0, tk.END)
            self.doctor_listbox.delete(0, tk.END)

    def add_group(self):
        """Add a new group to the selected environment."""
        selected = self.env_listbox.curselection()
        if not selected or self.env_listbox.get(selected[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Please add and select an environment first!")
            return
        env = self.env_listbox.get(selected[0])
        group = simpledialog.askstring("Input", f"Enter new group for {env}:")
        if group and group not in self.groups[env]:
            self.groups[env].append(group)
            self.classes[env][group] = []
            if env == self.env_listbox.get(self.env_listbox.curselection()[0]):
                self.group_listbox.insert(tk.END, group)

    def delete_group(self):
        """Delete the selected group and its classes."""
        selected = self.group_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a group to delete!")
            return
        group = self.group_listbox.get(selected[0])
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete group '{group}'?"):
            env = self.env_listbox.get(self.env_listbox.curselection()[0])
            self.groups[env].remove(group)
            del self.classes[env][group]
            self.group_listbox.delete(selected[0])
            self.class_listbox.delete(0, tk.END)

    def add_class(self):
        """Add a new class to the selected group."""
        selected = self.group_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Select a group first!")
            return
        group = self.group_listbox.get(selected[0])
        env = self.env_listbox.get(self.env_listbox.curselection()[0])
        class_name = simpledialog.askstring("Input", f"Enter new class for {group}:")
        if class_name and class_name not in self.classes[env].get(group, []):
            self.classes[env][group].append(class_name)
            if group == self.group_listbox.get(self.group_listbox.curselection()[0]):
                self.class_listbox.insert(tk.END, class_name)

    def delete_class(self):
        """Delete the selected class from the group."""
        selected = self.class_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a class to delete!")
            return
        class_name = self.class_listbox.get(selected[0])
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete class '{class_name}'?"):
            env = self.env_listbox.get(self.env_listbox.curselection()[0])
            group = self.group_listbox.get(self.group_listbox.curselection()[0])
            self.classes[env][group].remove(class_name)
            self.class_listbox.delete(selected[0])

    def add_subject(self):
        """Add a new subject to the selected environment."""
        selected = self.env_listbox.curselection()
        if not selected or self.env_listbox.get(selected[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Select an environment first!")
            return
        env = self.env_listbox.get(selected[0])
        subject = simpledialog.askstring("Input", f"Enter new subject for {env}:")
        if subject and subject not in self.subjects[env]:
            self.subjects[env].append(subject)
            if env == self.env_listbox.get(self.env_listbox.curselection()[0]):
                self.subject_listbox.insert(tk.END, subject)

    def delete_subject(self):
        """Delete the selected subject from the environment."""
        selected = self.subject_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a subject to delete!")
            return
        subject = self.subject_listbox.get(selected[0])
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete subject '{subject}'?"):
            env = self.env_listbox.get(self.env_listbox.curselection()[0])
            self.subjects[env].remove(subject)
            self.subject_listbox.delete(selected[0])

    def add_assistant(self):
        """Add a new teaching assistant to the selected environment."""
        selected = self.env_listbox.curselection()
        if not selected or self.env_listbox.get(selected[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Select an environment first!")
            return
        env = self.env_listbox.get(selected[0])
        assistant = simpledialog.askstring("Input", f"Enter new assistant name for {env}:")
        # Check if the assistant already exists in any environment
        all_assistants = [a for e in self.environments for a in self.assistants.get(e, [])]
        if assistant and assistant not in all_assistants:
            self.assistants[env].append(assistant)
            if env == self.env_listbox.get(self.env_listbox.curselection()[0]):
                self.assistant_listbox.insert(tk.END, assistant)

    def set_assistant_time_preferences(self):
        """Open a dialog to set time preferences for the selected assistant, loading existing preferences if available."""
        selected_env = self.env_listbox.curselection()
        selected_assistant = self.assistant_listbox.curselection()
        if not selected_env or self.env_listbox.get(selected_env[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Select an environment first!")
            return
        if not selected_assistant:
            messagebox.showwarning("Warning", "Select an assistant first!")
            return
        assistant = self.assistant_listbox.get(selected_assistant[0])
        
        if not self.validate_positive_integer(self.days.get()) or not self.validate_positive_integer(self.periods.get()):
            messagebox.showerror("Error", "Please enter valid Days and Periods before setting preferences.")
            return
        
        days = int(self.days.get())
        periods = int(self.periods.get())
        # Load existing preferences if they exist
        existing_prefs = self.assistant_time_prefs.get(assistant, None)
        dialog = PreferenceDialog(self.root, days, periods, f"Time Preferences for {assistant}", existing_prefs=existing_prefs)
        self.root.wait_window(dialog.top)
        if dialog.result is not None:
            self.assistant_time_prefs[assistant] = dialog.result

    def set_assistant_subject_preferences(self):
        """Open a dialog to set subject preferences for the selected assistant, loading existing preferences if available."""
        selected_env = self.env_listbox.curselection()
        selected_assistant = self.assistant_listbox.curselection()
        if not selected_env or self.env_listbox.get(selected_env[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Select an environment first!")
            return
        if not selected_assistant:
            messagebox.showwarning("Warning", "Select an assistant first!")
            return
        env = self.env_listbox.get(selected_env[0])
        assistant = self.assistant_listbox.get(selected_assistant[0])
        
        # Only show subjects for the current environment
        env_subjects = sorted(self.subjects.get(env, []))
        if not env_subjects:
            messagebox.showwarning("Warning", f"No subjects available in environment '{env}'. Add subjects first!")
            return
        
        # Load existing preferences if they exist
        existing_prefs = self.assistant_subject_prefs.get(assistant, None)
        dialog = SubjectPreferenceDialog(self.root, env_subjects, f"Subject Preferences for {assistant} ({env})", existing_prefs=existing_prefs)
        self.root.wait_window(dialog.top)
        if dialog.result is not None:
            # Expand the result to include all subjects across all environments
            all_subjects = sorted({s for e in self.environments for s in self.subjects.get(e, [])})
            expanded_result = {s: dialog.result.get(s, 0) for s in all_subjects}
            self.assistant_subject_prefs[assistant] = expanded_result

    def delete_assistant(self):
        """Delete the selected teaching assistant from the environment."""
        selected = self.assistant_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an assistant to delete!")
            return
        env = self.env_listbox.get(self.env_listbox.curselection()[0])
        assistant = self.assistant_listbox.get(selected[0])
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete assistant '{assistant}' from '{env}'?"):
            self.assistants[env].remove(assistant)
            if assistant in self.assistant_time_prefs:
                del self.assistant_time_prefs[assistant]
            if assistant in self.assistant_subject_prefs:
                del self.assistant_subject_prefs[assistant]
            self.assistant_listbox.delete(selected[0])

    def add_doctor(self):
        """Add a new doctor to the selected environment."""
        selected = self.env_listbox.curselection()
        if not selected or self.env_listbox.get(selected[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Select an environment first!")
            return
        env = self.env_listbox.get(selected[0])
        doctor = simpledialog.askstring("Input", f"Enter new doctor name for {env}:")
        # Check if the doctor already exists in any environment
        all_doctors = [d for e in self.environments for d in self.doctors.get(e, [])]
        if doctor and doctor not in all_doctors:
            self.doctors[env].append(doctor)
            if env == self.env_listbox.get(self.env_listbox.curselection()[0]):
                self.doctor_listbox.insert(tk.END, doctor)

    def set_doctor_time_preferences(self):
        """Open a dialog to set time preferences for the selected doctor, loading existing preferences if available."""
        selected_env = self.env_listbox.curselection()
        selected_doctor = self.doctor_listbox.curselection()
        if not selected_env or self.env_listbox.get(selected_env[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Select an environment first!")
            return
        if not selected_doctor:
            messagebox.showwarning("Warning", "Select a doctor first!")
            return
        doctor = self.doctor_listbox.get(selected_doctor[0])
        
        if not self.validate_positive_integer(self.days.get()) or not self.validate_positive_integer(self.periods.get()):
            messagebox.showerror("Error", "Please enter valid Days and Periods before setting preferences.")
            return
        
        days = int(self.days.get())
        periods = int(self.periods.get())
        # Load existing preferences if they exist
        existing_prefs = self.doctor_time_prefs.get(doctor, None)
        dialog = PreferenceDialog(self.root, days, periods, f"Time Preferences for {doctor}", existing_prefs=existing_prefs)
        self.root.wait_window(dialog.top)
        if dialog.result is not None:
            self.doctor_time_prefs[doctor] = dialog.result

    def set_doctor_subject_preferences(self):
        """Open a dialog to set subject preferences for the selected doctor, loading existing preferences if available."""
        selected_env = self.env_listbox.curselection()
        selected_doctor = self.doctor_listbox.curselection()
        if not selected_env or self.env_listbox.get(selected_env[0]) == "Add an environment to start...":
            messagebox.showwarning("Warning", "Select an environment first!")
            return
        if not selected_doctor:
            messagebox.showwarning("Warning", "Select a doctor first!")
            return
        env = self.env_listbox.get(selected_env[0])
        doctor = self.doctor_listbox.get(selected_doctor[0])
        
        # Only show subjects for the current environment
        env_subjects = sorted(self.subjects.get(env, []))
        if not env_subjects:
            messagebox.showwarning("Warning", f"No subjects available in environment '{env}'. Add subjects first!")
            return
        
        # Load existing preferences if they exist
        existing_prefs = self.doctor_subject_prefs.get(doctor, None)
        dialog = SubjectPreferenceDialog(self.root, env_subjects, f"Subject Preferences for {doctor} ({env})", existing_prefs=existing_prefs)
        self.root.wait_window(dialog.top)
        if dialog.result is not None:
            # Expand the result to include all subjects across all environments
            all_subjects = sorted({s for e in self.environments for s in self.subjects.get(e, [])})
            expanded_result = {s: dialog.result.get(s, 0) for s in all_subjects}
            self.doctor_subject_prefs[doctor] = expanded_result

    def delete_doctor(self):
        """Delete the selected doctor from the environment."""
        selected = self.doctor_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a doctor to delete!")
            return
        env = self.env_listbox.get(self.env_listbox.curselection()[0])
        doctor = self.doctor_listbox.get(selected[0])
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete doctor '{doctor}' from '{env}'?"):
            self.doctors[env].remove(doctor)
            if doctor in self.doctor_time_prefs:
                del self.doctor_time_prefs[doctor]
            if doctor in self.doctor_subject_prefs:
                del self.doctor_subject_prefs[doctor]
            self.doctor_listbox.delete(selected[0])

    def update_groups(self, event):
        """Update the groups, classes, subjects, assistants, and doctors listboxes when an environment is selected."""
        self.group_listbox.delete(0, tk.END)
        self.class_listbox.delete(0, tk.END)
        self.subject_listbox.delete(0, tk.END)
        self.assistant_listbox.delete(0, tk.END)
        self.doctor_listbox.delete(0, tk.END)
        selected = self.env_listbox.curselection()
        if selected and self.env_listbox.get(selected[0]) != "Add an environment to start...":
            env = self.env_listbox.get(selected[0])
            for group in self.groups.get(env, []):
                self.group_listbox.insert(tk.END, group)
            for subject in self.subjects.get(env, []):
                self.subject_listbox.insert(tk.END, subject)
            for assistant in self.assistants.get(env, []):
                self.assistant_listbox.insert(tk.END, assistant)
            for doctor in self.doctors.get(env, []):
                self.doctor_listbox.insert(tk.END, doctor)
        self.group_listbox.bind('<<ListboxSelect>>', self.update_classes)

    def update_classes(self, event):
        """Update the classes listbox when a group is selected."""
        self.class_listbox.delete(0, tk.END)
        selected = self.group_listbox.curselection()
        if selected:
            env = self.env_listbox.get(self.env_listbox.curselection()[0])
            group = self.group_listbox.get(selected[0])
            if env not in self.classes or group not in self.classes[env]:
                return
            for class_name in self.classes[env].get(group, []):
                self.class_listbox.insert(tk.END, class_name)

    def save_inputs(self):
        """Validate and save all inputs to a JSON file."""
        try:
            # Validate that all required data is provided
            if not self.environments:
                messagebox.showerror("Error", "Please add at least one environment.")
                return
            if not all(self.groups[env] for env in self.environments):
                messagebox.showerror("Error", "Each environment must have at least one group.")
                return
            if not all(self.classes[env].get(g) for env in self.environments for g in self.groups[env]):
                messagebox.showerror("Error", "Each group must have at least one class.")
                return
            if not all(self.subjects[env] for env in self.environments):
                messagebox.showerror("Error", "Each environment must have at least one subject.")
                return
            all_assistants = [a for env in self.environments for a in self.assistants.get(env, [])]
            all_doctors = [d for env in self.environments for d in self.doctors.get(env, [])]
            if not all_assistants:
                messagebox.showerror("Error", "Please add at least one assistant.")
                return
            if not all_doctors:
                messagebox.showerror("Error", "Please add at least one doctor.")
                return

            # Validate that all assistants and doctors have set their preferences
            for assistant in all_assistants:
                if assistant not in self.assistant_time_prefs:
                    messagebox.showerror("Error", f"Assistant {assistant} has not set time preferences.")
                    return
                if assistant not in self.assistant_subject_prefs:
                    messagebox.showerror("Error", f"Assistant {assistant} has not set subject preferences.")
                    return
            for doctor in all_doctors:
                if doctor not in self.doctor_time_prefs:
                    messagebox.showerror("Error", f"Doctor {doctor} has not set time preferences.")
                    return
                if doctor not in self.doctor_subject_prefs:
                    messagebox.showerror("Error", f"Doctor {doctor} has not set subject preferences.")
                    return

            # Validate numeric inputs
            for var, name in [
                (self.halls, "Halls"),
                (self.labs, "Labs"),
                (self.days, "Days"),
                (self.periods, "Periods"),
                (self.assistant_max_periods, "Assistant Max Periods"),
                (self.assistant_max_subjects, "Assistant Max Subjects"),
                (self.doctor_max_periods, "Doctor Max Periods"),
                (self.doctor_max_subjects, "Doctor Max Subjects")
            ]:
                if not self.validate_positive_integer(var.get()):
                    messagebox.showerror("Error", f"Invalid input for {name}. Please enter a positive integer.")
                    return

            # Convert inputs to appropriate types
            halls = int(self.halls.get())
            labs = int(self.labs.get())
            days = int(self.days.get())
            periods = int(self.periods.get())
            AL = [int(self.assistant_max_periods.get()), int(self.assistant_max_subjects.get())]
            TL = [int(self.doctor_max_periods.get()), int(self.doctor_max_subjects.get())]

            # Flatten the classes dictionary for consistency
            flattened_classes = {}
            for env in self.environments:
                for group in self.groups[env]:
                    flattened_classes[group] = self.classes[env].get(group, [])

            # Prepare A and T by flattening the lists
            A = sorted([a for env in self.environments for a in self.assistants.get(env, [])])
            T = sorted([d for env in self.environments for d in self.doctors.get(env, [])])

            # Prepare AT and TT in the specified format: AT[a][d][p], TT[t][d][p]
            DAYS = list(range(1, days + 1))
            PERIODS = list(range(1, periods + 1))
            AT = {}
            TT = {}
            for a in A:
                AT[a] = {d: {p: self.assistant_time_prefs[a].get((d, p), 0) for p in PERIODS} for d in DAYS}
            for t in T:
                TT[t] = {d: {p: self.doctor_time_prefs[t].get((d, p), 0) for p in PERIODS} for d in DAYS}

            # Prepare AS and TS in the specified format: AS[a][s], TS[t][s]
            all_subjects = sorted({s for e in self.environments for s in self.subjects[e]})
            AS = {}
            TS = {}
            for a in A:
                AS[a] = self.assistant_subject_prefs[a]
            for t in T:
                TS[t] = self.doctor_subject_prefs[t]

            # Prepare the data dictionary with the specified order
            data = {
                "halls": halls,
                "labs": labs,
                "days": days,
                "periods": periods,
                "environments": self.environments,
                "groups": self.groups,
                "classes": flattened_classes,
                "subjects": self.subjects,
                "A": A,
                "T": T,
                "AL": AL,
                "TL": TL,
                "AT": AT,
                "TT": TT,
                "AS": AS,
                "TS": TS
            }

            # Save to a JSON file
            os.makedirs("inputs", exist_ok=True)
            with open("inputs/scheduling_inputs.json", "w") as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Success", "Inputs saved to 'inputs/scheduling_inputs.json'.")

            return data  # Return the data for use in generate_schedules
        except Exception as e:
            messagebox.showerror("Error", f"Error saving inputs: {str(e)}")
            return None

    def generate_schedules(self):
        """Generate schedules using the logic file and display a progress bar."""
        # First, save and validate inputs
        data = self.save_inputs()
        if data is None:
            return  # Validation failed, error message already shown

        # Create a modal dialog with a progress bar
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Generating Schedules")
        progress_dialog.geometry("300x100")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()

        ttk.Label(progress_dialog, text="Generating schedules, please wait...").pack(pady=10)
        progress_bar = ttk.Progressbar(progress_dialog, length=200, mode="determinate", maximum=100)
        progress_bar.pack(pady=10)

        # Variables to control the generation process
        self.generation_complete = False
        self.generation_error = None

        def run_generation():
            """Run the generation in a separate thread."""
            try:
                # -------------------- START: Generate Schedules Modifications --------------------
                # Call the generate_schedules function from scheduler_logic.py
                # The function is expected to handle its own output saving
                scheduelModel()
                # -------------------- END: Generate Schedules Modifications --------------------
            except Exception as e:
                self.generation_error = str(e)
            finally:
                self.generation_complete = True

        def update_progress():
            """Update the progress bar while generation is running."""
            start_time = time.time()
            estimated_duration = 10  # Estimated time in seconds (adjust as needed)
            while not self.generation_complete:
                elapsed = time.time() - start_time
                progress = min(100, (elapsed / estimated_duration) * 100)
                progress_bar["value"] = progress
                progress_dialog.update()
                time.sleep(0.1)  # Update every 100ms

            # Ensure the progress bar reaches 100% when done
            progress_bar["value"] = 100
            progress_dialog.update()

            # Close the dialog and show the result
            progress_dialog.destroy()
            if self.generation_error:
                messagebox.showerror("Error", f"Error generating schedules: {self.generation_error}")
            else:
                # -------------------- START: Generate Schedules Modifications --------------------
                # Show a success message without saving the output here
                messagebox.showinfo("Success", "Schedules generated successfully. Check the output as specified by the logic file.")
                # -------------------- END: Generate Schedules Modifications --------------------

        # Start the generation in a separate thread
        threading.Thread(target=run_generation, daemon=True).start()
        # Start updating the progress bar
        update_progress()

    def update_groups(self, event):
        """Update the groups, classes, subjects, assistants, and doctors listboxes when an environment is selected."""
        self.group_listbox.delete(0, tk.END)
        self.class_listbox.delete(0, tk.END)
        self.subject_listbox.delete(0, tk.END)
        self.assistant_listbox.delete(0, tk.END)
        self.doctor_listbox.delete(0, tk.END)
        selected = self.env_listbox.curselection()
        if selected and self.env_listbox.get(selected[0]) != "Add an environment to start...":
            env = self.env_listbox.get(selected[0])
            for group in self.groups.get(env, []):
                self.group_listbox.insert(tk.END, group)
            for subject in self.subjects.get(env, []):
                self.subject_listbox.insert(tk.END, subject)
            for assistant in self.assistants.get(env, []):
                self.assistant_listbox.insert(tk.END, assistant)
            for doctor in self.doctors.get(env, []):
                self.doctor_listbox.insert(tk.END, doctor)
        self.group_listbox.bind('<<ListboxSelect>>', self.update_classes)

    def update_classes(self, event):
        """Update the classes listbox when a group is selected."""
        self.class_listbox.delete(0, tk.END)
        selected = self.group_listbox.curselection()
        if selected:
            env = self.env_listbox.get(self.env_listbox.curselection()[0])
            group = self.group_listbox.get(selected[0])
            if env not in self.classes or group not in self.classes[env]:
                return
            for class_name in self.classes[env].get(group, []):
                self.class_listbox.insert(tk.END, class_name)

if __name__ == "__main__":
    """Entry point for the application."""
    root = tk.Tk()
    app = SchedulingApp(root)
    root.mainloop()