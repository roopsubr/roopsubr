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
        
        # Pattern to identify a command header
        cmd_pattern = re.compile(r'^[#!]?\s*[\w\-\.@]+[#>]\s*(show|acidiag|fabric|fabricnode|moquery)\b(.*)', re.IGNORECASE)
        
        # Pattern to identify a prompt line (e.g., "E1-APIC-01#")
        # Matches: start of line, hostname, prompt char (# or >), optional whitespace, end of line
        prompt_pattern = re.compile(r'^[\w\-\.@]+[#>]\s*$')

        with open(path, 'r') as f:
            for line in f:
                match = cmd_pattern.match(line)
                
                if match:
                    if current_cmd:
                        commands[current_cmd] = current_output
                    
                    keyword = match.group(1)
                    args = match.group(2).strip()
                    current_cmd = f"{keyword} {args}".strip()
                    current_output = []
                
                # Only append if it's not a prompt line and we are inside a command block
                elif current_cmd:
                    if not prompt_pattern.match(line.strip()):
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
        detail_win.title(f"Comparison Analysis")
        detail_win.geometry("1200x800")

        comp_frame = tk.Frame(detail_win)
        comp_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- ADDED: Command Header Display ---
        header_label = tk.Label(
            comp_frame, 
            text=f"Command: {cmd_name}", 
            font=('Courier New', 12, 'bold'), 
            bg="#f0f0f0", 
            anchor="w", 
            pady=5
        )
        header_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Labels for Pre/Post
        tk.Label(comp_frame, text="Pre-Check", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky="ew")
        tk.Label(comp_frame, text="Post-Check", font=('Arial', 10, 'bold')).grid(row=1, column=1, sticky="ew")

        # Text Areas
        txt_pre = tk.Text(comp_frame, wrap="none", font=("Courier New", 9))
        txt_post = tk.Text(comp_frame, wrap="none", font=("Courier New", 9))
        
        # Shared Scrollbar
        sb = tk.Scrollbar(comp_frame, orient="vertical", command=lambda *args: (txt_pre.yview(*args), txt_post.yview(*args)))
        txt_pre.configure(yscrollcommand=sb.set); txt_post.configure(yscrollcommand=sb.set)

        # Updated Grid placement (row indices shifted down by 1 to make room for header)
        txt_pre.grid(row=2, column=0, sticky="nsew")
        txt_post.grid(row=2, column=1, sticky="nsew")
        sb.grid(row=2, column=2, sticky="ns")

        # Configure weights
        comp_frame.grid_columnconfigure(0, weight=1)
        comp_frame.grid_columnconfigure(1, weight=1)
        comp_frame.grid_rowconfigure(2, weight=1) # Row 2 is now the text area row


        # Tag configuration
        for txt in [txt_pre, txt_post]:
            txt.tag_configure("diff", background="#ffeef0", foreground="#cb2431")

        # Logic to populate
        pre_lines = self.pre_data.get(cmd_name, [])
        post_lines = self.post_data.get(cmd_name, [])
        diff = list(difflib.ndiff(pre_lines, post_lines))

        for line in diff:
            code = line[:2]
            content = line[2:]
            if code == '  ':
                txt_pre.insert("end", content); txt_post.insert("end", content)
            elif code == '- ':
                txt_pre.insert("end", content, "diff"); txt_post.insert("end", "\n")
            elif code == '+ ':
                txt_pre.insert("end", "\n"); txt_post.insert("end", content, "diff")

        txt_pre.config(state="disabled"); txt_post.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkDiffApp(root)
    root.mainloop()