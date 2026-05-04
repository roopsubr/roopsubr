import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import difflib
import re

class NetworkDiffApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cisco & APIC Advanced Comparator")
        self.root.geometry("1000x700")

        self.pre_path = tk.StringVar()
        self.post_path = tk.StringVar()
        self.pre_data = {}
        self.post_data = {}

        # --- UI Layout ---
        file_frame = tk.LabelFrame(root, text="File Selection", padx=10, pady=10)
        file_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(file_frame, text="Select Pre-Check File", command=self.load_pre).grid(row=0, column=0, pady=5)
        tk.Label(file_frame, textvariable=self.pre_path, fg="blue").grid(row=0, column=1, padx=10, sticky="w")

        tk.Button(file_frame, text="Select Post-Check File", command=self.load_post).grid(row=1, column=0, pady=5)
        tk.Label(file_frame, textvariable=self.post_path, fg="blue").grid(row=1, column=1, padx=10, sticky="w")

# --- Updated Button UI ---
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        # Create a Label that acts as a button
        run_btn = tk.Label(
            btn_frame, 
            text="RUN COMPARISON", 
            bg="#005a9e", 
            fg="white", 
            font=('Arial', 10, 'bold'), 
            padx=20, 
            pady=5, 
            relief="raised", 
            cursor="hand2"
        )
        run_btn.pack(side="left", padx=5)
        
        # Bind the click event to the compare method
        run_btn.bind("<Button-1>", lambda event: self.compare())
        
        # Add a hover effect (optional, makes it feel more like a real button)
        run_btn.bind("<Enter>", lambda e: run_btn.config(bg="#007acc"))
        run_btn.bind("<Leave>", lambda e: run_btn.config(bg="#005a9e"))

        tk.Label(root, text="Double-click any row to see side-by-side differences", fg="gray").pack()

        # Results Table
        table_frame = tk.Frame(root)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("command", "match", "mismatch", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("command", text="Extracted Command")
        self.tree.heading("match", text="Matching Lines")
        self.tree.heading("mismatch", text="Mismatched Lines")
        self.tree.heading("status", text="Status")

        self.tree.column("command", width=550)
        self.tree.column("match", width=100, anchor="center")
        self.tree.column("mismatch", width=100, anchor="center")
        self.tree.column("status", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.open_detail_window)

    def load_pre(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path: self.pre_path.set(path)

    def load_post(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path: self.post_path.set(path)

    def parse_file(self, path):
        commands = {}
        current_cmd = None
        current_output = []
        
        # 1. Primary pattern: Looks for a prompt (hostname#) followed by command
        cmd_pattern = re.compile(r'^[#!]?\s*[\w\-\.@]+[#>]\s*(show|acidiag|fabric|fabricnode)\b\s+([^:].*)', re.IGNORECASE)

        # 2. Refined fallback:
        # - Matches start of line with keyword
        # - Ensures it is NOT followed by a colon (to avoid "Fabric Name : ...")
        # - Ensures it doesn't look like a simple key-value pair
        fallback_pattern = re.compile(r'^(show|acidiag|fabric|fabricnode)\b\s+([^:].*?)(?<!:)$', re.IGNORECASE)

        with open(path, 'r') as f:
            for line in f:
                # Check for command match
                match = cmd_pattern.match(line) or fallback_pattern.match(line)
                
                # Check to explicitly ignore lines that look like metadata/key-value pairs
                # (e.g., lines containing a colon that aren't actual command outputs)
                is_metadata = ":" in line and not line.strip().startswith(('show', 'acidiag', 'fabric', 'fabricnode'))
                
                if match and not is_metadata:
                    if current_cmd:
                        commands[current_cmd] = current_output
                    # Reconstruct command name
                    current_cmd = f"{match.group(1)} {match.group(2)}".strip()
                    current_output = []
                elif current_cmd:
                    # Only append to output if it's not a header-like line
                    current_output.append(line)
            
            if current_cmd:
                commands[current_cmd] = current_output
        return commands

    def compare(self):
        if not self.pre_path.get() or not self.post_path.get():
            messagebox.showwarning("Warning", "Please select both files.")
            return

        for item in self.tree.get_children(): self.tree.delete(item)
        
        self.pre_data = self.parse_file(self.pre_path.get())
        self.post_data = self.parse_file(self.post_path.get())

        all_cmds = sorted(set(self.pre_data.keys()) | set(self.post_data.keys()))

        for cmd in all_cmds:
            pre_lines = self.pre_data.get(cmd, [])
            post_lines = self.post_data.get(cmd, [])

            if not pre_lines:
                self.tree.insert("", "end", values=(cmd, "-", "-", "NEW IN POST"))
                continue
            if not post_lines:
                self.tree.insert("", "end", values=(cmd, "-", "-", "MISSING IN POST"))
                continue

            matcher = difflib.SequenceMatcher(None, pre_lines, post_lines)
            matches = sum(block.size for block in matcher.get_matching_blocks())
            mismatches = max(len(pre_lines), len(post_lines)) - matches
            status = "PASS" if mismatches == 0 else "CHANGED"

            item_id = self.tree.insert("", "end", values=(cmd, matches, mismatches, status))
            if status == "CHANGED":
                self.tree.tag_configure('diff', foreground="red")
                self.tree.item(item_id, tags=('diff',))

    def open_detail_window(self, event):
        selection = self.tree.selection()
        if not selection: return
        item = selection[0]
        cmd_name = self.tree.item(item, "values")[0]

        detail_win = tk.Toplevel(self.root)
        detail_win.title(f"Details: {cmd_name}")
        detail_win.geometry("950x700")

        notebook = ttk.Notebook(detail_win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        pre_tab = tk.Frame(notebook); post_tab = tk.Frame(notebook); diff_tab = tk.Frame(notebook)
        notebook.add(pre_tab, text="Pre-Check"); notebook.add(post_tab, text="Post-Check"); notebook.add(diff_tab, text="Diff Analysis")

        def create_text_area(parent, content, is_diff=False):
            txt = tk.Text(parent, wrap="none", font=("Courier New", 10))
            sy = tk.Scrollbar(parent, command=txt.yview); sx = tk.Scrollbar(parent, orient="horizontal", command=txt.xview)
            txt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
            sy.pack(side="right", fill="y"); sx.pack(side="bottom", fill="x"); txt.pack(side="left", fill="both", expand=True)

            if is_diff:
                txt.tag_configure("add", background="#e6ffed", foreground="#22863a")
                txt.tag_configure("rem", background="#ffeef0", foreground="#cb2431")
                for line in content:
                    if line.startswith('+'): txt.insert("end", line, "add")
                    elif line.startswith('-'): txt.insert("end", line, "rem")
                    else: txt.insert("end", line)
            else:
                txt.insert("end", "".join(content))
            txt.config(state="disabled")

        pre_content = self.pre_data.get(cmd_name, ["Not in Pre file"])
        post_content = self.post_data.get(cmd_name, ["Not in Post file"])
        diff_content = list(difflib.ndiff(pre_content, post_content))

        create_text_area(pre_tab, pre_content)
        create_text_area(post_tab, post_content)
        create_text_area(diff_tab, diff_content, is_diff=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkDiffApp(root)
    root.mainloop()