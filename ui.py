import tkinter as tk
from tkinter import filedialog, scrolledtext
import sys
from io import StringIO
import os

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FTB任务书翻译工具 by 骑狗上学@bilibili")
        self.root.geometry("800x600")
        
        # 标题：FTBQuests 任务书翻译工具 by CoronaNIMO
        self.title_label = tk.Label(self.root, text="FTBQuests 任务书翻译工具 by 骑狗上学@bilibili", font=("Arial", 16))
        self.title_label.pack(pady = (10, 0))
        # 翻译整合包任务书区域
        self.translate_frame = tk.LabelFrame(self.root, text="汉化整合包任务书", bd=2, relief=tk.GROOVE)
        self.translate_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)

        # 路径选择组件
        self.path_frame = tk.Frame(self.translate_frame, bd=0, relief=tk.GROOVE)
        self.path_frame.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.path_label = tk.Label(self.path_frame, text="整合包根目录：", width=15)
        self.path_label.pack(side=tk.LEFT)
        
        self.path_entry = tk.Entry(self.path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        
        self.path_button = tk.Button(self.path_frame, text="选择", command=self.select_path)
        self.path_button.pack(side=tk.LEFT)
        
        # 功能按钮
        self.button_frame = tk.Frame(self.translate_frame)
        self.button_frame.grid(row=0, column=1, sticky="nsew", pady=10)
        
        self.generate_button = tk.Button(self.button_frame, text="预备")
        self.generate_button.pack(side=tk.LEFT, padx=5)
        
        self.open_button = tk.Button(self.button_frame, text="打开", command=self.open_work_path)
        self.open_button.pack(side=tk.LEFT, padx=5)

        self.translate_button = tk.Button(self.button_frame, text="AI翻译")
        self.translate_button.pack(side=tk.LEFT, padx=5)



        
        self.write_button = tk.Button(self.button_frame, text="写回")
        self.write_button.pack(side=tk.LEFT, padx=5)
        
        # Configure the grid to expand properly
        self.translate_frame.grid_rowconfigure(0, weight=1)
        self.translate_frame.grid_columnconfigure(0, weight=0)
        self.translate_frame.grid_columnconfigure(1, weight=1)

        # 管理区域
        self.manage_frame = tk.LabelFrame(self.root, text="从整合包任务书提取参考文件（如果你不知道这是什么，不要操作）", bd=2, relief=tk.GROOVE)
        self.manage_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)

        # 管理区域内也有一个路径选择
        self.path_frame_2 = tk.Frame(self.manage_frame, bd=0, relief=tk.GROOVE)        
        self.path_frame_2.grid(row=0, column=0, padx=5, sticky="ew")

        self.path_label_2 = tk.Label(self.path_frame_2, text="整合包根目录：", width = 15)
        self.path_label_2.pack(side=tk.LEFT)
        self.path_entry_2 = tk.Entry(self.path_frame_2, width = 50)
        self.path_entry_2.pack(side=tk.LEFT, padx = 5)
        self.path_button_2 = tk.Button(self.path_frame_2, text="选择", command=self.select_admin_path)
        self.path_button_2.pack(side=tk.LEFT)

        self.button_frame_2 = tk.Frame(self.manage_frame)
        self.button_frame_2.grid(row=0, column=1, sticky="nsew",pady=10)
        self.extract_button = tk.Button(self.button_frame_2, text="提取参考文件")
        self.extract_button.pack(side=tk.LEFT, padx=5)

        # Configure the grid to expand properly
        self.manage_frame.grid_rowconfigure(0, weight=1)
        self.manage_frame.grid_columnconfigure(0, weight=0)
        self.manage_frame.grid_columnconfigure(1, weight=1)

        # 配置区域
        self.config_frame = tk.Frame(self.root)
        self.config_frame.pack(fill=tk.X, expand=True)

        # 配置项
        self.config_entries = {}
        
        # 创建配置项UI
        self.create_config_ui()
        
        # 加载配置
        self.load_config()



        # 控制台输出显示
        self.console_frame = tk.Frame(self.root)
        self.console_frame.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        
        self.console_text = scrolledtext.ScrolledText(self.console_frame, state='disabled')
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        # 重定向控制台输出
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self

    def open_work_path(self):
        """打开工作翻译路径文件"""
        import config
        filepath = config.getDefaultConfig('translate_work_path')
        # 把filepath 改成以当前目录为基础的windows目录形态
        filepath = os.path.abspath(filepath)
        filepath = filepath.replace('/', '\\')
        try:
            os.startfile(filepath)
        except FileNotFoundError:
            self.show_info("错误", f"文件未找到: {filepath}")
        except Exception as e:
            self.show_info("错误", f"无法打开文件: {e}")

        

        
    def create_config_ui(self):
        """创建配置项UI"""
        from configparser import ConfigParser
        import os
        
        # 读取配置文件
        self.config = ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        self.config.read(config_path)
        
        # 创建配置项容器
        config_container = tk.Frame(self.config_frame)
        config_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 左侧面板 - 基本配置
        left_panel = tk.Frame(config_container)
        left_panel.grid(row=0, column=0, sticky="nsew")
        
        # 右侧面板
        right_panel = tk.Frame(config_container)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        # 配置网格权重
        config_container.grid_columnconfigure(0, weight=1)
        config_container.grid_columnconfigure(1, weight=1)
        config_container.grid_rowconfigure(0, weight=1)
        
        # 右侧上部 - LLM配置
        llm_frame = tk.LabelFrame(right_panel, text="LLM配置")
        llm_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧下部 - 操作区域
        operation_frame = tk.LabelFrame(right_panel, text="操作")
        operation_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建配置项
        default_frame = tk.LabelFrame(left_panel, text="基本配置")
        default_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_config_entry(llm_frame, "LLM", "api_base", "API地址")
        self.create_config_entry(llm_frame, "LLM", "api_key", "API密钥")
        self.create_config_entry(llm_frame, "LLM", "model", "模型名称")
        self.create_config_entry(llm_frame, "LLM", "max_tokens", "最大token数")
                
        self.create_config_entry(default_frame, "DEFAULT", "dev_mode", "请保持为0")
        self.create_config_entry(default_frame, "DEFAULT", "reference_path", "参考文件路径")
        self.create_config_entry(default_frame, "DEFAULT", "translate_fine_path", "精细翻译路径")
        self.create_config_entry(default_frame, "DEFAULT", "translate_work_path", "工作翻译路径")
        self.create_config_entry(default_frame, "DEFAULT", "ftb_lang_source_path", "源语言文件路径")
        self.create_config_entry(default_frame, "DEFAULT", "ftb_lang_target_path", "目标语言文件路径")

        # 保存按钮
        self.save_button = tk.Button(operation_frame, text="保存配置", command=self.save_config)
        self.save_button.pack(pady=10, anchor='center')
        

        
    def create_config_entry(self, parent, section, key, label):
        """创建单个配置项"""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        label = tk.Label(frame, text=label, width=15)
        label.pack(side=tk.LEFT)
        
        entry = tk.Entry(frame, width=50)
        entry.pack(side=tk.LEFT, padx=5)
        
        # 保存到字典中
        if section not in self.config_entries:
            self.config_entries[section] = {}
        self.config_entries[section][key] = entry
        
    def load_config(self):
        """加载配置到UI"""
        for section in self.config_entries:
            for key in self.config_entries[section]:
                entry = self.config_entries[section][key]
                value = self.config.get(section, key)
                entry.delete(0, tk.END)
                entry.insert(0, value)
                
    def save_config(self):
        """保存配置到文件"""
        from configparser import ConfigParser
        import os
        
        # 更新配置
        for section in self.config_entries:
            for key in self.config_entries[section]:
                entry = self.config_entries[section][key]
                self.config[section][key] = entry.get()
        
        # 写入文件
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        with open(config_path, 'w') as f:
            self.config.write(f)
        
        # 重新加载配置
        self.load_config()
        self.show_info("提示", "配置保存成功")
        
        # 通知配置更新
        import config
        config.reload_config()
        
        
    def select_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
    
    def select_admin_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry_2.delete(0, tk.END)
            self.path_entry_2.insert(0, path)

    def get_selected_path(self):
        return self.path_entry.get()
    
    def get_selected_admin_path(self):
        return self.path_entry_2.get()
    
    def write(self, text):
        self.console_text.configure(state='normal')
        self.console_text.insert(tk.END, text)
        self.console_text.configure(state='disabled')
        self.console_text.see(tk.END)
        self.old_stdout.write(text)
    
    def flush(self):
        pass
        
    def show_info(self, title, message):
        from tkinter import messagebox
        messagebox.showinfo(title, message)
    
    def run(self):
        self.root.mainloop()
        
    def __del__(self):
        # 恢复标准输出
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
