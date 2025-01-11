import os
from pathlib import Path
from file_processor import FileProcessor
import time

def main():
    # 指定整合包的mods目录
    mods_dir = Path(r"D:\Games\Prism Launcher\instances\All the Mods 10 - ATM10 218\minecraft\mods")
    
    # 验证目录是否存在
    if not mods_dir.exists():
        print(f"错误: 指定的mods目录不存在: {mods_dir}")
        return
    
    start_time = time.time()
    success_count = 0
    error_count = 0
    
    try:
        # 初始化FileProcessor
        processor = FileProcessor(str(mods_dir))
        
        # 检查mods目录中的.jar文件
        jar_files = list(mods_dir.glob('*.jar'))
        if not jar_files:
            print("mods目录中没有找到.jar文件")
            return
            
        total_files = len(jar_files)
        print(f"找到 {total_files} 个jar文件")
        
        # 处理所有mod文件
        print("开始处理mod文件...")
        for i, jar_file in enumerate(jar_files, 1):
            print(f"正在处理 [{i}/{total_files}] {jar_file.name}")
            try:
                processor._process_jar(jar_file)
                success_count += 1
            except Exception as e:
                print(f"处理 {jar_file.name} 时出错: {str(e)}")
                error_count += 1
                continue
        
        elapsed_time = time.time() - start_time
        print("\n处理完成!")
        print(f"总计处理: {total_files} 个文件")
        print(f"成功: {success_count} 个")
        print(f"失败: {error_count} 个")
        print(f"耗时: {elapsed_time:.2f} 秒")

        # 处理资源包
        resource_pack_file = "data/resourcepack.zip"
        processor.process_resource_pack(Path(resource_pack_file))

        # 处理补充参考文件
        reference_dat_file = "data/modreference.json"
        processor.process_reference_dat(Path(reference_dat_file))
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
    finally:
        # 确保关闭数据库连接
        processor.close()

if __name__ == "__main__":
    main() 