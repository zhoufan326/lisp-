#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from lisp_loader import LispParser, load_single_lisp_file
from acad_doc_manager import find_autocad, apply_template, configure_print_settings
from lisp_executor import run_lisp
from dwg_saver import save_dwg
from acad_plot_manager import plot_paper_space
from filename import generate_filename

# UI Modules Import
HAS_UI = {}
for name in ["DWA_短尾凹", "DWT_短尾凸", "JZM_短尾M24_基准模", "JZM_锥度_基准模", "XBA_下摆凹", "XBT_下摆凸", "MJA_迈均凹", "MJT_迈均凸", "XZA_小锥度凹", "XZT_小锥度凸"]:
    try:
        mod = __import__(name, fromlist=[f"{name}_UI"])
        HAS_UI[name] = getattr(mod, f"{name}_UI")
    except: pass

class ExecutionDialog(tk.Toplevel):
    def __init__(self, parent, func, on_exec, fs):
        super().__init__(parent)
        self.title(f"参数: {func.name}"); self.func = func; self.on_exec = on_exec; self.fs = fs; self.inputs = {}
        self.cfg_dir = os.path.join(os.path.expanduser("~"), ".autolisp_mgr")
        os.makedirs(self.cfg_dir, exist_ok=True)
        self.p_file = os.path.join(self.cfg_dir, f"generic_{func.name}_params.json")
        self._setup(); self.load_p(); self.transient(parent); self.grab_set()

    def load_p(self):
        if os.path.exists(self.p_file):
            try:
                with open(self.p_file, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    for k, v in d.items(): 
                        if k in self.inputs: self.inputs[k].set(v)
            except: pass

    def save_p(self):
        try:
            with open(self.p_file, 'w', encoding='utf-8') as f:
                json.dump({k: v.get() for k, v in self.inputs.items()}, f, ensure_ascii=False, indent=2)
        except: pass

    def _setup(self):
        f = ttk.Frame(self, padding=30); f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text=f"命令: {self.func.name}", font=("Segoe UI", self.fs, "bold")).pack(pady=(0, 20))
        for p in self.func.params:
            row = ttk.Frame(f); row.pack(fill=tk.X, pady=5)
            ttk.Label(row, text=f"{p}:", width=12).pack(side=tk.LEFT)
            var = tk.BooleanVar() if 'flag' in p.lower() or 'is-' in p.lower() else tk.StringVar()
            if isinstance(var, tk.BooleanVar): ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
            else: ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.inputs[p] = var
        b_f = ttk.Frame(f); b_f.pack(side=tk.BOTTOM, fill=tk.X, pady=20)
        ttk.Button(b_f, text="执行", command=self._run).pack(side=tk.RIGHT, padx=5)
        ttk.Button(b_f, text="取消", command=self.destroy).pack(side=tk.RIGHT)

    def _run(self):
        self.save_p(); self.on_exec(self.func, {k: v.get() for k, v in self.inputs.items()}); self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("AutoCAD LISP 智能管理 (v3.0)"); self.geometry("1600x1000"); self.fs = 20
        self.acad = None; self.model = Model(); self.last_save_meta = None; self._setup(); self._load(self.model.last_dir)

    def _setup(self):
        t = ttk.Frame(self, padding=10); t.pack(side=tk.TOP, fill=tk.X)
        for text, cmd in [("📂 目录", self._on_dir), ("🔌 连接", self._on_conn), ("� 新建", self._on_new), ("📂 加载", self._on_lisp), ("💾 保存", self._on_save_dwg), ("🖨️ 打印", self._on_print), ("🔄 刷新", self._on_ref)]:
            ttk.Button(t, text=text, command=cmd).pack(side=tk.LEFT, padx=5)
        self.status = ttk.Label(self, text="就绪", relief=tk.SUNKEN, padding=5); self.status.pack(side=tk.BOTTOM, fill=tk.X)
        p = ttk.PanedWindow(self, orient=tk.HORIZONTAL); p.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(p, show="tree", selectmode="browse"); p.add(self.tree, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)
        df = ttk.Frame(p, padding=20); p.add(df, weight=4)
        self.title_lbl = ttk.Label(df, text="选择文件", font=("Segoe UI", self.fs+5, "bold")); self.title_lbl.pack(anchor=tk.W)
        self.docs = tk.Text(df, height=5, font=("Segoe UI", self.fs)); self.docs.pack(fill=tk.X, pady=10)
        ttk.Button(df, text="💾 保存文档", command=self._on_save_doc).pack(anchor=tk.E)
        self.f_list = ttk.Frame(df); self.f_list.pack(fill=tk.BOTH, expand=True, pady=10)

    def _on_dir(self):
        d = filedialog.askdirectory(initialdir=self.model.last_dir)
        if d: self._load(d)

    def _load(self, d):
        self.model.last_dir = d; self.model.save_cfg("last_dir", d); self.model.scan(d)
        self.tree.delete(*self.tree.get_children())
        for path in self.model.data: self.tree.insert("", tk.END, text=os.path.basename(path), values=(path,))
        self.status.config(text=f"已加载: {d}")

    def _on_conn(self):
        try:
            self.acad = find_autocad(); self.acad.Visible = True
            self.status.config(text="AutoCAD 已连接")
        except Exception as e: messagebox.showerror("错误", str(e))

    def _ensure_acad(self):
        """确保执行前有可用 CAD 连接。"""
        if self.acad:
            try:
                self.acad.Visible = True
                return True
            except Exception:
                self.acad = None
        try:
            self.acad = find_autocad()
            self.acad.Visible = True
            self.status.config(text="AutoCAD 已自动连接")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"无法连接 AutoCAD: {e}")
            return False

    def _on_new(self):
        try:
            tmpl = filedialog.askopenfilename(filetypes=[("DWT", "*.dwt")])
            if not tmpl: return
            self.acad = find_autocad(); doc = apply_template(self.acad, tmpl, None)
            doc.Activate(); configure_print_settings(doc)
            self.status.config(text="新图形已创建")
        except Exception as e: messagebox.showerror("错误", str(e))

    def _on_lisp(self):
        if not self.acad: return
        try:
            doc = self.acad.ActiveDocument; count = 0
            for path, obj in self.model.data.items():
                if load_single_lisp_file(doc, path, obj.functions): count += 1
            self.status.config(text=f"已加载 {count} 个 LISP")
        except Exception as e: messagebox.showerror("错误", str(e))

    def _on_ref(self): self._load(self.model.last_dir)

    def _on_sel(self, e):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0], "values")[0]; obj = self.model.data.get(path)
        if not obj: return
        self.model.curr = obj; self.title_lbl.config(text=obj.name)
        self.docs.delete("1.0", tk.END); self.docs.insert(tk.END, self.model.get_doc(path))
        for w in self.f_list.winfo_children(): w.destroy()
        for f in (obj.functions or []):
            if f.name.lower().startswith("c:"):
                row = ttk.Frame(self.f_list); row.pack(fill=tk.X, pady=2)
                ttk.Label(row, text=f.name).pack(side=tk.LEFT)
                ttk.Button(row, text="🚀 执行", command=lambda f_obj=f: self._on_exec_click(f_obj)).pack(side=tk.RIGHT)

    def _on_save_doc(self):
        if self.model.curr: self.model.save_doc(self.model.curr.path, self.docs.get("1.0", tk.END).strip())

    def _on_exec_click(self, f):
        # 这里仅负责打开参数 UI，不执行 CAD 相关动作。
        name = os.path.splitext(self.model.curr.name)[0]
        if name in HAS_UI:
            dialog = tk.Toplevel(self); dialog.title(f"参数: {name}")
            frame = ttk.Frame(dialog, padding=30); frame.pack(fill=tk.BOTH, expand=True)
            HAS_UI[name](dialog, self._exec_custom, self.fs).create_ui(frame)
        else: ExecutionDialog(self, f, self._exec_generic, self.fs)

    def _exec_generic(self, f, p):
        try:
            if not self._ensure_acad():
                return
            doc = getattr(self.acad, "ActiveDocument", None)
            if not doc:
                messagebox.showwarning("提醒", "请先在 CAD 中新建或打开图形，再执行。")
                return
            args = []
            for k in f.params:
                v = p.get(k)
                if isinstance(v, bool): args.append("T" if v else "nil")
                elif str(v).replace('.','',1).isdigit(): args.append(str(v))
                else: args.append(f'"{v}"')
            fname = self._get_fname(f.name.replace("c:",""), p)
            self._remember_save_meta(f.name.replace("c:", "").lower(), p, fname)
            run_lisp(self.acad, f.name, args, len(f.params)>0)
        except Exception as e: messagebox.showerror("错误", str(e))

    def _exec_custom(self, f_name, p):
        try:
            if not self._ensure_acad():
                return
            doc = getattr(self.acad, "ActiveDocument", None)
            if not doc:
                messagebox.showwarning("提醒", "请先在 CAD 中新建或打开图形，再执行。")
                return
            clean = f_name.lower().replace("c:", "")
            args = self._build_args(clean, p)
            fname = self._get_fname(clean, p)
            self._remember_save_meta(clean, p, fname)
            # 自定义参数模式下，优先调用核心函数（如 xbt），避免对 c: 命令传参导致异常
            exec_name = clean if f_name.lower().startswith("c:") else f_name
            run_lisp(self.acad, exec_name, args, True)
        except Exception as e: messagebox.showerror("错误", str(e))

    def _build_args(self, name, p):
        def abs_v(k): return str(abs(float(p.get(k, 0))))
        if name in ["dwa", "dwt", "xza", "xzt"]: return [abs_v("r0"), abs_v("a0"), abs_v("t0"), f'"{p.get("tool_type", "1")}"']
        if name in ["jzm1", "jzm2"]:
            res = [abs_v("r0"), abs_v("a0")]
            if name == "jzm1": res.append(abs_v("t0"))
            res.append(f'"{p.get("scale_str", "1:1")}"')
            if name == "jzm2": res.append(abs_v("t0"))
            res.extend([p.get("tech_choice", "1"), f'"{p.get("custom_tech_text", "")}"', p.get("slot_choice", "0")])
            return res
        if name in ["xba", "xbt"]: return [abs_v("r0"), abs_v("a0"), abs_v("t0"), abs_v("b0"), f'"{p.get("tool_type", "1")}"', p.get("tech_choice", "1"), f'"{p.get("custom_tech_text", "")}"']
        if name in ["mja", "mjt"]: return [abs_v("r0"), abs_v("a0"), abs_v("t0")]
        return []

    def _get_fname(self, name, p):
        pref = self._get_drawing_type(name, p)
        try: return generate_filename(float(p.get("r0", 0)), float(p.get("a0", 0)), pref or "DRAWING")
        except: return None

    def _get_drawing_type(self, name, p):
        pref = {"mja": "XPMJM", "mjt": "XPMJM", "jzm1": "JZM", "jzm2": "JZM"}.get(name)
        if pref:
            return pref
        tt = p.get("tool_type", "1")
        if name in ["dwa", "dwt", "xza", "xzt"]:
            return {"1": "GPMJX", "2": "GPMXJ", "3": "QX", "4": "QZ", "5": "QP"}.get(tt, "DRAWING")
        if name in ["xba", "xbt"]:
            return {"1": "XPMJM", "2": "XJMJM"}.get(tt, "DRAWING")
        return "DRAWING"

    def _remember_save_meta(self, func_name, params, fallback_name=None):
        try:
            self.last_save_meta = {
                "name": fallback_name,
                "radius": float(params.get("r0", 0)),
                "chord_length": float(params.get("a0", 0)),
                "drawing_type": self._get_drawing_type(func_name, params),
            }
        except Exception:
            self.last_save_meta = {"name": fallback_name}

    def _on_print(self):
        if self.acad: plot_paper_space(self.acad.ActiveDocument)

    def _on_save_dwg(self):
        try:
            if not self._ensure_acad():
                return
            doc = self.acad.ActiveDocument
            if not doc:
                messagebox.showwarning("提醒", "请先在 CAD 中新建或打开图形。")
                return

            meta = self.last_save_meta or {}
            path = save_dwg(
                doc,
                out_dir="P:\\工装绘图文件",
                name=None,
                radius=meta.get("radius"),
                chord_length=meta.get("chord_length"),
                drawing_type=meta.get("drawing_type"),
            )
            self.status.config(text=f"已保存: {os.path.basename(path)}")
            messagebox.showinfo("保存成功", f"DWG 已保存:\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

class Model:
    def __init__(self):
        self.cfg_dir = os.path.join(os.path.expanduser("~"), ".autolisp_mgr"); os.makedirs(self.cfg_dir, exist_ok=True)
        self.cfg_p = os.path.join(self.cfg_dir, "config.json"); self.docs_p = os.path.join(self.cfg_dir, "docs.json")
        try: self.cfg = json.load(open(self.cfg_p))
        except: self.cfg = {}
        try: self.docs_d = json.load(open(self.docs_p))
        except: self.docs_d = {}
        self.last_dir = self.cfg.get("last_dir", "."); self.data = {}; self.curr = None

    def save_cfg(self, k, v): self.cfg[k] = v; json.dump(self.cfg, open(self.cfg_p, 'w'))
    def scan(self, d):
        self.data = {}
        for r, _, fs in os.walk(d):
            for f in fs:
                if f.lower().endswith(('.lisp', '.lsp')):
                    p = os.path.join(r, f); self.data[p] = type('obj', (), {'path':p, 'name':f, 'functions':LispParser.parse_file(p)})

    def get_doc(self, p): return self.docs_d.get(p, self.data[p].functions[0].docstring if self.data[p].functions else "暂无说明")
    def save_doc(self, p, d): self.docs_d[p] = d; json.dump(self.docs_d, open(self.docs_p, 'w'))

if __name__ == "__main__": App().mainloop()
