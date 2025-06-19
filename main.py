import os 
import json 
import importlib 
import subprocess 
import threading 
import sys 
import re 
from datetime import datetime 
import openai 
import tkinter as tk 
from tkinter import ttk, messagebox, filedialog, scrolledtext 
 
# 准备系统提示 
def get_system_prompt():
    current_time = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    return f"""你是一个专业的Python开发助手，专注于为Windows环境编写实用工具脚本。请根据用户需求编写完整的Python工具脚本，遵循以下规范：
 
1. 提供完整的、可直接运行的Python代码 
2. 必须包含main()函数作为程序入口点 
3. 包含清晰的功能描述和使用方法注释 
4. 包含元数据注释，格式为：# metadata = {{"name": "工具名称", "description": "工具描述", "created": "创建时间"}}
5. 必须处理潜在错误并提供用户友好的反馈 
6. 优先使用Python标准库，第三方库需在脚本内自动安装 
7. 代码需有良好的注释，结构清晰易读 
8. 聚焦于解决用户描述的具体问题，不引入无关功能 
9. 使用标准输入输出方式，避免使用sys.argv 和非必要的图形界面 
10. 创建临时或配置文件时，在脚本所在目录创建同名子目录 
11. 除非用户明确要求，否则不要将输出文件保存到脚本子目录 
12. 脚本末尾需包含阻塞语句，防止控制台窗口自动关闭 
 
请仅返回完整的Python代码，不要包含任何解释或额外的文本。
当前时间：{current_time}"""
 
class ToolBoxApp:
    def __init__(self, root):
        self.root  = root 
        self.root.title(" 智能工具箱")
        self.root.geometry("900x750")   # 增加高度以适应新按钮 
        
        # 配置 
        self.config_file  = "toolbox_config.json"  
        self.tools_dir  = "tools"
        self.api_key  = ""
        self.base_url  = "https://api.deepseek.com"  
        self.max_tokens  = 2000  # 默认值 
        
        # 创建工具目录 
        if not os.path.exists(self.tools_dir):  
            os.makedirs(self.tools_dir)  
        
        # 加载配置 
        self.load_config()  
        
        # 初始化工具列表 
        self.tools  = {}
        self.load_tools()  
        
        # 创建UI 
        self.create_ui()  
        
        # 初始化OpenAI客户端 
        self.init_openai_client()  
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):  
            with open(self.config_file,  "r") as f:
                config = json.load(f)  
                self.api_key  = config.get("api_key",  "")
                self.base_url  = config.get("base_url",  self.base_url)  
                self.max_tokens  = config.get("max_tokens",  2000)  # 加载max_tokens 
    
    def save_config(self):
        """保存配置文件"""
        config = {
            "api_key": self.api_key,  
            "base_url": self.base_url, 
            "max_tokens": self.max_tokens   # 保存max_tokens 
        }
        with open(self.config_file,  "w") as f:
            json.dump(config,  f, indent=4)
    
    def init_openai_client(self):
        """初始化OpenAI客户端"""
        if self.api_key: 
            return True 
        return False 
    
    def create_ui(self):
        """创建用户界面"""
        # 创建主框架 
        self.main_frame  = ttk.Frame(self.root,  padding="10")
        self.main_frame.pack(fill=tk.BOTH,  expand=True)
        
        # 顶部配置栏 
        config_frame = ttk.LabelFrame(self.main_frame,  text="API配置", padding="10")
        config_frame.pack(fill=tk.X,  pady=5)
        
        ttk.Label(config_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W)
        self.api_key_entry  = ttk.Entry(config_frame, width=50)
        self.api_key_entry.grid(row=0,  column=1, sticky=tk.W)
        self.api_key_entry.insert(0,  self.api_key)  
        
        ttk.Label(config_frame, text="Base URL:").grid(row=1, column=0, sticky=tk.W)
        self.base_url_entry  = ttk.Entry(config_frame, width=50)
        self.base_url_entry.grid(row=1,  column=1, sticky=tk.W)
        self.base_url_entry.insert(0,  self.base_url) 
 
        ttk.Label(config_frame, text="Max Tokens:").grid(row=2, column=0, sticky=tk.W)
        self.max_tokens_entry  = ttk.Entry(config_frame, width=10)
        self.max_tokens_entry.grid(row=2,  column=1, sticky=tk.W)
        self.max_tokens_entry.insert(0,  str(self.max_tokens))   # 使用配置中的值 
        
        ttk.Button(config_frame, text="保存配置", command=self.save_api_config).grid(row=1,  column=2, padx=5)
        
        # 工具创建器 
        creator_frame = ttk.LabelFrame(self.main_frame,  text="工具创建器", padding="10")
        creator_frame.pack(fill=tk.X,  pady=5)
        
        ttk.Label(creator_frame, text="工具需求描述:").pack(anchor=tk.W)
        self.tool_request_entry  = scrolledtext.ScrolledText(creator_frame, height=5, width=80)
        self.tool_request_entry.pack(fill=tk.X,  pady=5)
        
        self.generate_button  = ttk.Button(creator_frame, text="生成工具", command=self.generate_tool) 
        self.generate_button.pack(pady=5)  
        
        # 工具管理 
        management_frame = ttk.LabelFrame(self.main_frame,  text="工具管理", padding="10")
        management_frame.pack(fill=tk.BOTH,  expand=True, pady=5)
        
        # 工具列表 
        self.tool_tree  = ttk.Treeview(management_frame, columns=("name", "description", "created"), show="headings")
        self.tool_tree.heading("#0",  text="工具ID")
        self.tool_tree.heading("name",  text="工具名称")
        self.tool_tree.heading("description",  text="描述")
        self.tool_tree.heading("created",  text="创建时间")
        self.tool_tree.column("#0",  width=100)
        self.tool_tree.column("name",  width=200)
        self.tool_tree.column("description",  width=400)
        self.tool_tree.column("created",  width=150)
        self.tool_tree.pack(side=tk.LEFT,  fill=tk.BOTH, expand=True)
        
        # 工具操作按钮 
        button_frame = ttk.Frame(management_frame)
        button_frame.pack(side=tk.RIGHT,  fill=tk.Y, padx=5)
        
        ttk.Button(button_frame, text="运行工具", command=self.run_tool).pack(fill=tk.X,  pady=5)
        ttk.Button(button_frame, text="编辑工具", command=self.edit_tool).pack(fill=tk.X,  pady=5)
        ttk.Button(button_frame, text="删除工具", command=self.delete_tool).pack(fill=tk.X,  pady=5)
        ttk.Button(button_frame, text="导出工具", command=self.export_tool).pack(fill=tk.X,  pady=5)
        ttk.Button(button_frame, text="导入工具", command=self.import_tool).pack(fill=tk.X,  pady=5)
        ttk.Button(button_frame, text="更改信息", command=self.edit_tool_info).pack(fill=tk.X,  pady=5)
        ttk.Button(button_frame, text="修改工具", command=self.modify_tool).pack(fill=tk.X,  pady=5)
        
        # 刷新工具列表 
        self.refresh_tool_list()  
    
    def save_api_config(self):
        """保存API配置"""
        self.api_key  = self.api_key_entry.get().strip()  
        self.base_url  = self.base_url_entry.get().strip()  
        
        try:
            self.max_tokens  = int(self.max_tokens_entry.get().strip()) 
            if self.max_tokens  <= 0:
                messagebox.showerror(" 错误", "max_tokens 必须是正整数")
                return 
        except ValueError:
            messagebox.showerror(" 错误", "max_tokens 必须是数字")
            return 
        
        self.save_config()  
        
        # 重新初始化客户端 
        if self.init_openai_client():  
            messagebox.showinfo(" 成功", "API配置已保存并验证通过")
        else:
            messagebox.showwarning(" 警告", "API配置已保存但验证失败")
    
    def load_tools(self):
        """加载所有工具"""
        self.tools  = {}
        if os.path.exists(self.tools_dir):  
            for filename in os.listdir(self.tools_dir):  
                if filename.endswith(".py"):  
                    tool_name = filename[:-3]
                    tool_path = os.path.join(self.tools_dir,  filename)
                    
                    # 读取工具元数据 
                    metadata = self.get_tool_metadata(tool_path)  
                    if metadata:
                        self.tools[tool_name]  = {
                            "path": tool_path,
                            "name": metadata.get("name",  tool_name), 
                            "description": metadata.get("description",  "无描述"),
                            "created": metadata.get("created",  "未知")
                        }
    
    def get_tool_metadata(self, tool_path):
        """从工具文件中提取元数据"""
        try:
            with open(tool_path, "r", encoding="utf-8") as f:
                content = f.read() 
                
                # 查找元数据注释 
                metadata_start = content.find('#  metadata = {')
                if metadata_start != -1:
                    metadata_end = content.find('}',  metadata_start)
                    if metadata_end != -1:
                        metadata_str = content[metadata_start:metadata_end + 1]
                        try:
                            # 将字符串格式的元数据转换为字典 
                            metadata = eval(metadata_str.replace('=  ', ': ', 1))
                            if isinstance(metadata, dict):
                                return metadata 
                        except:
                            pass 
                
                # 如果标准元数据格式不存在，尝试兼容旧版格式 
                metadata = {}

                # 提取name
                name_match = re.search(r'"name":\s*"([^"]+)"',  content)
                if name_match:
                    metadata["description"] = name_match.group(1)
                
                # 提取description 
                desc_match = re.search(r'"description":\s*"([^"]+)"',  content)
                if desc_match:
                    metadata["description"] = desc_match.group(1) 
                
                # 提取created 
                created_match = re.search(r'"created":\s*"([^"]+)"',  content)
                if created_match:
                    metadata["created"] = created_match.group(1) 
                
                return metadata 
        except Exception as e:
            print(f"读取工具元数据失败: {str(e)}")
            return None 
    
    def refresh_tool_list(self):
        """刷新工具列表"""
        self.load_tools()  
        self.tool_tree.delete(*self.tool_tree.get_children())  
        
        # 确保工具名称正确显示 
        for tool_name, tool_info in self.tools.items():  
            # 确保tool_name是字符串 
            display_name = str(tool_name) if tool_name else "未命名工具"
            self.tool_tree.insert("",  tk.END, text=tool_name,  # 使用tool_name作为ID 
                                values=(display_name, tool_info["description"], tool_info["created"]))
        
    def generate_tool(self):
        """生成新工具"""
        if not self.api_key:  
            messagebox.showerror(" 错误", "请先配置API Key")
            return 
        
        request_text = self.tool_request_entry.get("1.0",  tk.END).strip()
        if not request_text:
            messagebox.showerror(" 错误", "请输入工具需求描述")
            return 
 
        try:
            max_tokens = int(self.max_tokens_entry.get().strip()) 
            if max_tokens <= 0:
                messagebox.showerror(" 错误", "max_tokens 必须是正整数")
                return 
        except ValueError:
            messagebox.showerror(" 错误", "max_tokens 必须是数字")
            return 
        
        # 禁用生成按钮 
        self.generate_button.config(state=tk.DISABLED) 
        
        messagebox.showinfo(" 正在生成工具", "工具已开始生成")
 
        # 在新线程中生成工具，避免阻塞UI 
        threading.Thread(target=self._generate_tool_in_thread, args=(request_text, max_tokens)).start()
 
    def _generate_tool_in_thread(self, request_text, _max_tokens):
        """在新线程中生成工具"""
        try:
            openai.api_key  = self.api_key   
            openai.api_base  = "https://api.deepseek.com/v1"  
            
            response = openai.ChatCompletion.create(  
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": request_text},
                ],
                max_tokens=_max_tokens 
            )
            
            tool_code = response.choices[0].message.content   
 
            # 去除代码块标记 
            if tool_code.startswith("```python"):  
                tool_code = tool_code[9:]
            if tool_code.endswith("```"):  
                tool_code = tool_code[:-3]
            tool_code = tool_code.strip()  
            
            # 提取工具名称 
            tool_name = self.extract_tool_name(tool_code)  
            if not tool_name:
                tool_name = f"tool_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  
            
            # 保存工具文件 
            tool_path = os.path.join(self.tools_dir,  f"{tool_name}.py")
            with open(tool_path, "w", encoding="utf-8") as f:
                f.write(tool_code)  
            
            # 使用主线程更新UI，因为tkinter的UI更新必须在主线程中进行 
            self.root.after(0,  lambda: messagebox.showinfo(" 成功", f"工具 '{tool_name}' 已生成并保存"))
            self.root.after(0,  self.refresh_tool_list)  
            
        except Exception as e:
            # 使用主线程更新UI 
            self.root.after(0,  lambda: messagebox.showerror(" 错误", f"生成工具失败: {str(e)}"))
        finally:
            # 无论成功或失败，都重新启用生成按钮 
            self.root.after(0,  lambda: self.generate_button.config(state=tk.NORMAL)) 
    
    def extract_tool_name(self, code):
        """从代码中提取工具名称"""
        try:
            # 优先尝试从main函数的docstring中提取 
            main_func_match = re.search(r'def\s+main\s*\(\s*\):\s*\"\"\"\s*(.*?)\s*\"\"\"',  code, re.DOTALL)
            if main_func_match:
                docstring = main_func_match.group(1).strip() 
                first_line = docstring.split('\n')[0].strip() 
                if first_line:
                    return re.sub(r'[^a-zA-Z0-9_]',  '', first_line.replace('  ', '_')).lower() or f"tool_{datetime.now().strftime('%Y%m%d_%H%M%S')}" 
 
            # 尝试从描述中提取 
            desc_match = re.search(r'"description":\s*"([^"]+)"',  code)
            if desc_match:
                desc = desc_match.group(1).strip() 
                if desc:
                    return re.sub(r'[^a-zA-Z0-9_]',  '', desc.split()[0].replace('  ', '_')).lower()
 
            # 如果以上方法都失败，使用随机名称 
            return f"tool_{datetime.now().strftime('%Y%m%d_%H%M%S')}" 
        except:
            return f"tool_{datetime.now().strftime('%Y%m%d_%H%M%S')}" 
    
    def run_tool(self):
        """运行选中的工具"""
        selected_item = self.tool_tree.focus()  
        if not selected_item:
            messagebox.showerror(" 错误", "请先选择一个工具")
            return 
        
        tool_name = self.tool_tree.item(selected_item,  "text")
        tool_path = os.path.join(self.tools_dir,  f"{tool_name}.py")
        
        try:
            if sys.platform  == "win32":
                os.startfile(tool_path)  
            else:
                subprocess.run(["python",  tool_path])
        except Exception as e:
            messagebox.showerror(" 错误", f"启动工具失败: {str(e)}")
    
    def edit_tool(self):
        """编辑选中的工具"""
        selected_item = self.tool_tree.focus()  
        if not selected_item:
            messagebox.showerror(" 错误", "请先选择一个工具")
            return 
        
        tool_name = self.tool_tree.item(selected_item,  "text")
        tool_path = os.path.join(self.tools_dir,  f"{tool_name}.py")
        
        try:
            # 使用 subprocess 启动记事本而不显示 CMD 窗口 
            if sys.platform  == "win32":
                # 启动记事本并隐藏 CMD 窗口 
                subprocess.Popen(
                    ['notepad.exe',  tool_path],
                    shell=True,
                    creationflags=subprocess.SW_HIDE  # 隐藏窗口 
                )
            else:
                subprocess.run(["xdg-open",  tool_path])
        except Exception as e:
            messagebox.showerror(" 错误", f"打开工具失败: {str(e)}")
    
    def delete_tool(self):
        """删除选中的工具"""
        selected_item = self.tool_tree.focus()  
        if not selected_item:
            messagebox.showerror(" 错误", "请先选择一个工具")
            return 
        
        tool_name = self.tool_tree.item(selected_item,  "text")
        
        if messagebox.askyesno(" 确认", f"确定要删除工具 '{tool_name}' 吗?"):
            tool_path = os.path.join(self.tools_dir,  f"{tool_name}.py")
            try:
                os.remove(tool_path)  
                self.refresh_tool_list()  
                messagebox.showinfo(" 成功", f"工具 '{tool_name}' 已删除")
            except Exception as e:
                messagebox.showerror(" 错误", f"删除工具失败: {str(e)}")
    
    def export_tool(self):
        """导出选中的工具"""
        selected_item = self.tool_tree.focus()  
        if not selected_item:
            messagebox.showerror(" 错误", "请先选择一个工具")
            return 
        
        tool_name = self.tool_tree.item(selected_item,  "text")
        tool_path = os.path.join(self.tools_dir,  f"{tool_name}.py")
        
        export_path = filedialog.asksaveasfilename(  
            title="导出工具",
            initialfile=f"{tool_name}.py",
            defaultextension=".py",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        
        if export_path:
            try:
                with open(tool_path, "r", encoding="utf-8") as src, \
                     open(export_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())  
                messagebox.showinfo(" 成功", f"工具 '{tool_name}' 已导出到 {export_path}")
            except Exception as e:
                messagebox.showerror(" 错误", f"导出工具失败: {str(e)}")
    
    def import_tool(self):
        """导入工具"""
        import_path = filedialog.askopenfilename(  
            title="导入工具",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        
        if import_path:
            try:
                # 获取工具名称 
                tool_name = os.path.basename(import_path)[:-3]  
                if not tool_name:
                    raise ValueError("无效的文件名")
                
                # 检查是否已存在 
                tool_path = os.path.join(self.tools_dir,  f"{tool_name}.py")
                if os.path.exists(tool_path):  
                    if not messagebox.askyesno(" 确认", f"工具 '{tool_name}' 已存在，是否覆盖?"):
                        return 
                
                # 复制文件 
                with open(import_path, "r", encoding="utf-8") as src, \
                     open(tool_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())  
                
                self.refresh_tool_list()  
                messagebox.showinfo(" 成功", f"工具 '{tool_name}' 已导入")
                
            except Exception as e:
                messagebox.showerror(" 错误", f"导入工具失败: {str(e)}")
    
    def edit_tool_info(self):
        """编辑工具信息"""
        selected_item = self.tool_tree.focus() 
        if not selected_item:
            messagebox.showerror(" 错误", "请先选择一个工具")
            return 
        
        tool_name = self.tool_tree.item(selected_item,  "text")
        tool_info = self.tools.get(tool_name) 
        if not tool_info:
            messagebox.showerror(" 错误", "无法获取工具信息")
            return 
        
        # 创建编辑对话框 
        edit_window = tk.Toplevel(self.root) 
        edit_window.title(" 编辑工具信息")
        edit_window.geometry("400x200") 
        
        # 工具名称 
        ttk.Label(edit_window, text="工具名称:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        name_entry = ttk.Entry(edit_window, width=30)
        name_entry.grid(row=0,  column=1, padx=5, pady=5, sticky=tk.W)
        name_entry.insert(0,  tool_name)
        
        # 工具描述 
        ttk.Label(edit_window, text="工具描述:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        desc_entry = ttk.Entry(edit_window, width=30)
        desc_entry.grid(row=1,  column=1, padx=5, pady=5, sticky=tk.W)
        desc_entry.insert(0,  tool_info["description"])
        
        # 保存按钮 
        def save_changes():
            new_name = name_entry.get().strip() 
            new_desc = desc_entry.get().strip() 
            
            if not new_name:
                messagebox.showerror(" 错误", "工具名称不能为空")
                return 
            
            try:
                # 如果名称改变了，需要重命名文件 
                if new_name != tool_name:
                    old_path = os.path.join(self.tools_dir,  f"{tool_name}.py")
                    new_path = os.path.join(self.tools_dir,  f"{new_name}.py")
                    
                    if os.path.exists(new_path): 
                        messagebox.showerror(" 错误", f"工具 '{new_name}' 已存在")
                        return 
                    
                    os.rename(old_path,  new_path)
                
                # 更新元数据 
                tool_path = os.path.join(self.tools_dir,  f"{new_name}.py")
                with open(tool_path, "r+", encoding="utf-8") as f:
                    content = f.read() 
                    
                    # 查找并更新元数据 
                    metadata_start = content.find('#  metadata = {')
                    if metadata_start != -1:
                        metadata_end = content.find('}',  metadata_start)
                        if metadata_end != -1:
                            # 构造新的元数据字符串 
                            new_metadata = f'# metadata = {{"description": "{new_desc}", "created": "{tool_info["created"]}"}}'
                            new_content = content[:metadata_start] + new_metadata + content[metadata_end+1:]
                            
                            # 写回文件 
                            f.seek(0) 
                            f.write(new_content) 
                            f.truncate() 
                
                # 刷新工具列表 
                self.refresh_tool_list() 
                messagebox.showinfo(" 成功", "工具信息已更新")
                edit_window.destroy() 
                
            except Exception as e:
                messagebox.showerror(" 错误", f"更新工具信息失败: {str(e)}")
        
        ttk.Button(edit_window, text="保存", command=save_changes).grid(row=2, column=1, padx=5, pady=5, sticky=tk.E)
    
    def modify_tool(self):
        """修改工具代码"""
        selected_item = self.tool_tree.focus() 
        if not selected_item:
            messagebox.showerror(" 错误", "请先选择一个工具")
            return 
        
        tool_name = self.tool_tree.item(selected_item,  "text")
        tool_info = self.tools.get(tool_name) 
        if not tool_info:
            messagebox.showerror(" 错误", "无法获取工具信息")
            return 
        
        # 创建修改对话框 
        modify_window = tk.Toplevel(self.root) 
        modify_window.title(" 修改工具")
        modify_window.geometry("600x400") 
        
        # 显示当前工具信息 
        ttk.Label(modify_window, text=f"工具: {tool_name}").pack(pady=5)
        ttk.Label(modify_window, text=f"描述: {tool_info['description']}").pack(pady=5)
        
        # 修改提示 
        ttk.Label(modify_window, text="修改提示:").pack(pady=5)
        modify_prompt_entry = scrolledtext.ScrolledText(modify_window, height=5, width=70)
        modify_prompt_entry.pack(pady=5) 
        
        # 修改按钮 
        def submit_modification():
            modify_prompt = modify_prompt_entry.get("1.0",  tk.END).strip()
            if not modify_prompt:
                messagebox.showerror(" 错误", "请输入修改提示")
                return 
            
            # 读取当前工具代码 
            try:
                with open(tool_info["path"], "r", encoding="utf-8") as f:
                    current_code = f.read() 
            except Exception as e:
                messagebox.showerror(" 错误", f"读取工具代码失败: {str(e)}")
                return 
            
            # 在新线程中修改工具 
            def _modify_tool_in_thread():
                try:
                    openai.api_key  = self.api_key   
                    openai.api_base  = "https://api.deepseek.com/v1"  
                    
                    # 构造修改请求 
                    modify_request = f"请根据以下提示修改以下Python工具代码:\n\n修改提示: {modify_prompt}\n\n当前代码:\n```python\n{current_code}\n```"
                    
                    response = openai.ChatCompletion.create(  
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": get_system_prompt()},
                            {"role": "user", "content": modify_request},
                        ],
                        max_tokens=self.max_tokens  
                    )
                    
                    modified_code = response.choices[0].message.content   
 
                    # 去除代码块标记 
                    if modified_code.startswith("```python"):  
                        modified_code = modified_code[9:]
                    if modified_code.endswith("```"):  
                        modified_code = modified_code[:-3]
                    modified_code = modified_code.strip() 
                    
                    # 保存修改后的代码 
                    with open(tool_info["path"], "w", encoding="utf-8") as f:
                        f.write(modified_code) 
                    
                    # 使用主线程更新UI 
                    self.root.after(0,  lambda: messagebox.showinfo(" 成功", "工具已成功修改"))
                    self.root.after(0,  self.refresh_tool_list) 
                    self.root.after(0,  modify_window.destroy) 
                    
                except Exception as e:
                    # 使用主线程更新UI 
                    self.root.after(0,  lambda: messagebox.showerror(" 错误", f"修改工具失败: {str(e)}"))
            
            # 显示进度信息 
            messagebox.showinfo(" 正在修改工具", "工具修改中，请稍候...")
            
            # 启动新线程 
            threading.Thread(target=_modify_tool_in_thread).start()
        
        ttk.Button(modify_window, text="提交修改", command=submit_modification).pack(pady=10)
 
if __name__ == "__main__":
    root = tk.Tk()
    app = ToolBoxApp(root)
    root.mainloop() 
