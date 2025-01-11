from file_processor import FileProcessor
import traceback

def main():
    try:
        # 初始化处理器并生成资源包
        processor = FileProcessor(".")
        print("正在生成汉化资源包...")
        processor.generate_language_pack("dist/minecraft-language-pack.zip")
        
        # 输出结果
        print("资源包生成成功！")
            
    except Exception as e:
        print(f"生成资源包时发生错误: {str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
    finally:
        if 'processor' in locals():
            processor.close()

if __name__ == "__main__":
    main() 