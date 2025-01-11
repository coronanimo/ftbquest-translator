import zipfile
import json
import time
from pathlib import Path
from database import Database
import shutil
import os
import tempfile

class FileProcessor:
    def __init__(self, mods_dir: str):
        self.mods_dir = mods_dir
        self.db = Database()

    def process_mods(self):
        """处理mods目录下的所有jar文件"""
        for jar_file in Path(self.mods_dir).glob('*.jar'):
            self._process_jar(jar_file)

    def _process_jar(self, jar_path: Path):
        """处理单个jar文件"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 获取assets目录下的所有modid
                assets_dir = 'assets/'
                modids = set()
                
                # 遍历assets目录下的所有子目录
                for file_info in jar.infolist():
                    if file_info.filename.startswith(assets_dir):
                        parts = file_info.filename.split('/')
                        if len(parts) > 2:  # assets/<modid>/...
                            modids.add(parts[1])
                
                if not modids:
                    print(f"警告: {jar_path.name} 中没有找到有效的modid")
                    return
                    
                # 为每个modid处理lang文件
                for modid in modids:
                    try:
                        # 处理英文lang文件
                        en_lang_path = f'assets/{modid}/lang/en_us.json'
                        if en_lang_path in jar.namelist():
                            self._process_lang_file(jar, modid, en_lang_path, is_chinese=False)
                        else:
                            #print(f"提示: {jar_path.name} 的 {modid} 没有英文语言文件")
                            pass
                        
                        # 处理中文lang文件
                        zh_lang_path = f'assets/{modid}/lang/zh_cn.json'
                        if zh_lang_path in jar.namelist():
                            self._process_lang_file(jar, modid, zh_lang_path, is_chinese=True)
                        else:
                            #print(f"提示: {jar_path.name} 的 {modid} 没有中文语言文件")
                            pass
                            
                    except Exception as e:
                        print(f"处理 {jar_path.name} 的 {modid} 时出错: {str(e)}")
                        continue
                        
        except zipfile.BadZipFile:
            print(f"错误: {jar_path.name} 不是有效的zip文件")
        except Exception as e:
            print(f"处理 {jar_path.name} 时发生未知错误: {str(e)}")

    def _process_lang_file(self, jar: zipfile.ZipFile, modid: str, file_path: str, is_chinese: bool):
        """处理单个lang文件"""
        try:
            with jar.open(file_path) as f:
                try:
                    content = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"错误: {file_path} 不是有效的JSON文件: {str(e)}")
                    return
                    
                try:
                    if is_chinese:
                        self._process_chinese_lang(modid, content)
                    else:
                        self._process_english_lang(modid, content)
                except Exception as e:
                    print(f"处理语言文件 {file_path} 时出错: {str(e)}")
                    
        except Exception as e:
            print(f"打开语言文件 {file_path} 时出错: {str(e)}")

    def _process_english_lang(self, modid: str, content: dict):
        """处理英文lang文件内容"""
        
        for key, value in content.items():
            self.db.insert_translation(modid, key, value)
        

    def _process_chinese_lang(self, modid: str, content: dict):
        """处理中文lang文件内容"""
        
        for key, value in content.items():
            self.db.update_zhcn1(modid, key, value)
        

    def close(self):
        """关闭数据库连接"""
        self.db.close()

    def process_resource_pack(self, pack_path: Path):
        """处理汉化资源包文件"""
        try:
            with zipfile.ZipFile(pack_path, 'r') as zip_file:
                # 遍历所有文件找到中文语言文件
                for file_info in zip_file.infolist():
                    if file_info.filename.startswith('assets/') and file_info.filename.endswith('/lang/zh_cn.json'):
                        parts = file_info.filename.split('/')
                        if len(parts) >= 4:  # assets/<modid>/lang/zh_cn.json
                            modid = parts[1]
                            try:
                                with zip_file.open(file_info.filename) as f:
                                    content = json.load(f)
                                    for key, value in content.items():
                                        self.db.update_zhcn2(modid, key, value)
                            except json.JSONDecodeError as e:
                                print(f"错误: {file_info.filename} 不是有效的JSON文件: {str(e)}")
                            except Exception as e:
                                print(f"处理资源包语言文件 {file_info.filename} 时出错: {str(e)}")
                            
        except zipfile.BadZipFile:
            print(f"错误: {pack_path.name} 不是有效的zip文件")
        except Exception as e:
            print(f"处理资源包 {pack_path.name} 时发生未知错误: {str(e)}")

    def process_reference_dat(self, dat_path: Path):
        """处理补充参考文件"""
        try:
            with open(dat_path, 'r', encoding='utf-8') as f:
                try:
                    reference_data = json.load(f)
                    
                    # 获取数据库中所有条目
                    cursor = self.db.conn.cursor()
                    cursor.execute('SELECT modid, key, zhcn2 FROM translations')
                    
                    # 对每个数据库条目，检查是否有对应的参考翻译
                    for row in cursor.fetchall():
                        modid, key, existing_zhcn2 = row
                        if existing_zhcn2 is None and key in reference_data:
                            self.db.update_zhcn2(modid, key, reference_data[key])
                            
                except json.JSONDecodeError as e:
                    print(f"错误: {dat_path.name} 不是有效的JSON文件: {str(e)}")
                    
        except Exception as e:
            print(f"处理参考文件 {dat_path.name} 时发生错误: {str(e)}")

    def generate_language_pack(self, output_path: str = "dist/minecraft-language-pack.zip"):
        """生成整合包汉化资源包"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 确保assets目录存在
            assets_dir = Path(temp_dir) / "assets"
            assets_dir.mkdir(exist_ok=True)
            
            # 从数据库获取所有翻译内容
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT DISTINCT modid 
                FROM translations 
                WHERE zhcn1 IS NOT NULL OR zhcn2 IS NOT NULL OR zhcn3 IS NOT NULL
            ''')
            modids = cursor.fetchall()
            
            # 为每个mod创建翻译文件
            for (modid,) in modids:
                # 获取这个mod的所有翻译，按照优先级：zhcn1 > zhcn3 > zhcn2
                cursor.execute('''
                    SELECT key, 
                           COALESCE(zhcn1, zhcn3, zhcn2) as translation 
                    FROM translations 
                    WHERE modid = ? 
                    AND (zhcn1 IS NOT NULL OR zhcn2 IS NOT NULL OR zhcn3 IS NOT NULL)
                ''', (modid,))
                translations = cursor.fetchall()
                
                if translations:
                    # 创建mod的语言文件目录
                    mod_lang_dir = assets_dir / modid / "lang"
                    mod_lang_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 将翻译写入json文件
                    translations_dict = {key: trans for key, trans in translations}
                    lang_file_path = mod_lang_dir / "zh_cn.json"
                    with open(lang_file_path, 'w', encoding='utf-8') as f:
                        json.dump(translations_dict, f, ensure_ascii=False, indent=4)
            
            # 创建pack.mcmeta文件
            pack_mcmeta = {
                "pack": {
                    "pack_format": 15,
                    "description": "Generated Language Pack"
                }
            }
            with open(Path(temp_dir) / "pack.mcmeta", 'w', encoding='utf-8') as f:
                json.dump(pack_mcmeta, f, ensure_ascii=False, indent=4)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 创建zip文件
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arc_name = str(file_path.relative_to(temp_dir))
                        zipf.write(file_path, arc_name)

    