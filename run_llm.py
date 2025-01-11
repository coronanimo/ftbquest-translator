from database import Database
from llm_client import LLMClient

def test_llm_translation():
    # 初始化数据库连接
    db = Database()
    # 将数据库实例传给LLMClient
    llm = LLMClient(db)

    try:
        # 1. 获取所有未翻译的条目
        untranslated = db.get_untranslated()
        print(f"找到 {len(untranslated)} 个未翻译的条目:")
        translation_results = llm.translate_batch(untranslated)

        for result in translation_results:
            db.update_zhcn3(
                modid=result.modid,
                key=result.key,
                zhcn3=result.translation
            )
        print(f"已将 {len(translation_results)} 个翻译结果写入数据库")

        # 2. 获取并翻译低信心条目
        low_confidence = db.get_low_confidence()
        print(f"\n找到 {len(low_confidence)} 个低信心条目:")
        low_conf_results = llm.translate_batch(low_confidence)
        for result in low_conf_results:
            db.update_zhcn3(
                modid=result.modid,
                key=result.key,
                zhcn3=result.translation
            )
        print(f"已将 {len(low_conf_results)} 个低信心条目的翻译结果写入数据库")
        
    finally:
        db.close()        

if __name__ == "__main__":
    test_llm_translation() 