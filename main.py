import json
import os
import ftb_snbt_lib as slib
import ui
from collections import deque
import config as conf

# 全局变量存储主窗口实例
window = None

if conf.getDefaultConfig('dev_mode') == '1':
    DEVELOPMENT_MODE = True
else:
    DEVELOPMENT_MODE = False


def extractLangMapFromLangTree(langTree):
    queue = deque()
    queue.append(([], langTree))
    langMap = {}

    while queue:
        path, node = queue.popleft()

        if isinstance(node, (list, dict)):
            if isinstance(node, list):
                for i, item in enumerate(node):
                    queue.append((path + [i], item))
            elif isinstance(node, dict):
                for key, value in node.items():
                    queue.append((path + [key], value))
        elif isinstance(node, str):
            key = "[" + "][".join(
                map(lambda x: f"'{x}'" if isinstance(x, str) else str(x), path)) + "]"
            langMap[key] = node
    return langMap


def generateReferenceJson():
    if DEVELOPMENT_MODE:
        folder_path = r"D:\Games\Prism Launcher\instances\All the Mods 10 - ATM10\minecraft"
    else:
        if window:
            folder_path = window.get_selected_admin_path()
        if not folder_path:
            window.show_info("提示", "请先选择整合包根目录")
            return

    sourcePathConf = conf.getDefaultConfig('ftb_lang_source_path')
    targetPathConf = conf.getDefaultConfig('ftb_lang_target_path')
    sourcePath = f"{folder_path}/{sourcePathConf}"
    targetPath = f"{folder_path}/{targetPathConf}"

    enusTree = slib.load(open(sourcePath, "r", encoding="utf-8"))
    zhcnTree = slib.load(open(targetPath, "r", encoding="utf-8"))

    zhcnMap = extractLangMapFromLangTree(zhcnTree)
    enusMap = extractLangMapFromLangTree(enusTree)

    referenceMap = {}

    for key, value in enusMap.items():
        if key not in zhcnMap:
            print(f"{key}: {value}")
        else:
            if len(enusMap[key]) < 1:
                continue
            elif enusMap[key].startswith("{") and enusMap[key].endswith("}"):
                continue
            else:
                if enusMap[key] not in referenceMap:
                    referenceMap[enusMap[key]] = {
                        'value': zhcnMap[key], 'source': [key]}
                else:
                    referenceMap[enusMap[key]]['source'].append(key)

    referencePath = conf.getDefaultConfig('reference_path')
    with open(referencePath, "w", encoding="utf-8") as f:
        json.dump(referenceMap, f, ensure_ascii=False, indent=4)
    window.show_info("提示", f"参考翻译已保存到 {referencePath}")


def generateTemporaryJson():
    if DEVELOPMENT_MODE:
        folder_path = r"D:\Games\Prism Launcher\instances\All the Mods 10 - ATM10 - Updated\minecraft"
    else:
        folder_path = window.get_selected_path()
        if not folder_path:
            window.show_info("提示", "请先选择整合包根目录")
            return

    referencePath = conf.getDefaultConfig('reference_path')
    with open(referencePath, "r", encoding="utf-8") as f:
        referenceMap = json.load(f)

    sourcePathConf = conf.getDefaultConfig('ftb_lang_source_path')
    targetPathConf = conf.getDefaultConfig('ftb_lang_target_path')
    sourcePath = f"{folder_path}/{sourcePathConf}"
    targetPath = f"{folder_path}/{targetPathConf}"

    try:
        zhcnTree = slib.load(open(targetPath, "r", encoding="utf-8"))
    except FileNotFoundError:
        zhcnTree = slib.Compound()

    enusTree = slib.load(open(sourcePath, "r", encoding="utf-8"))

    zhcnMap = extractLangMapFromLangTree(zhcnTree)
    enusMap = extractLangMapFromLangTree(enusTree)

    translateMap = {}
    translatedMap = {}

    for key, value in enusMap.items():
        if len(value) < 1 or enusMap[key].startswith(
                "{") and enusMap[key].endswith("}"):
            continue
        if key not in zhcnMap:
            if value in referenceMap:
                if key in referenceMap[value]['source']:
                    translatedMap[key] = referenceMap[value]['value']
                else:
                    translateMap[key] = {
                        'origin': value,
                        'ref': referenceMap[value]['value'],
                        'target': ''}
            else:
                translateMap[key] = {'origin': value, 'ref': '', 'target': ''}
        else:
            translatedMap[key] = zhcnMap[key]

    with open(conf.getDefaultConfig('translate_fine_path'), "w", encoding="utf-8") as f:
        json.dump(translatedMap, f, ensure_ascii=False, indent=4)
    with open(conf.getDefaultConfig('translate_work_path'), "w", encoding="utf-8") as f:
        json.dump(translateMap, f, ensure_ascii=False, indent=4)
    window.show_info("提示", "文件写入成功")


def translateWithDeepseek():
    translateMap = {}
    translateWorkPath = conf.getDefaultConfig('translate_work_path')

    try:
        with open(translateWorkPath, "r", encoding="utf-8") as f:
            translateMap = json.load(f)
    except Exception as e:
        window.show_info("错误", f"打开文件出现错误{e}")
        return

    maxTokens = int(conf.getConfig('LLM', 'max_tokens'))

    toTranslateString = ""
    toTranslateQueue = []
    toTranslateLength = 0

    bytesUpbound = maxTokens * 3 - 256
    locator = []
    for key, value in translateMap.items():
        if len(value['target']) > 0:
            continue
        if len(toTranslateString.encode('utf-8')) + \
                len(value['origin'].encode('utf-8')) > bytesUpbound:
            toTranslateQueue.append(toTranslateString.rstrip("\n"))
            toTranslateString = ""
        toTranslateString = toTranslateString + value['origin'] + "\n"
        locator.append(key)

    toTranslateString = toTranslateString.rstrip("\n")
    if len(toTranslateString) > 0:
        toTranslateQueue.append(toTranslateString)

    for i in range(len(toTranslateQueue)):
        toTranslateLength = toTranslateLength + \
            len(toTranslateQueue[i].encode('utf-8'))

    translatedList = []

    from openai import OpenAI

    client = OpenAI(
        base_url=conf.getConfig('LLM', 'api_base'),
        api_key=conf.getConfig('LLM', 'api_key')
    )

    try:
        remainLength = toTranslateLength
        for toTranslateString in toTranslateQueue:
            submitLength = len(toTranslateString.encode('utf-8'))
            remainLength -= submitLength
            print(f"正在提交{submitLength}长度的文本，还剩下{remainLength}请等待...")
            completion = client.chat.completions.create(
                model=conf.getConfig('LLM', 'model'),
                max_tokens=maxTokens,
                messages=[
                    {
                        "role": "system",
                        "content": '你是一个Minecraft我的世界游戏任务文本翻译专家，将用户输入的中文翻译成英文，或将用户输入的英文翻译成中文。对于非中文内容，它将提供中文翻译结果。用户可以向助手发送需要翻译的内容，助手会回答相应的翻译结果，并确保符合中文语言习惯以及我的世界游戏的风格。输入内容每行是一个任务文本，如果内容在花括号{}内，不要翻译，原样输出，内容中有类似与&开头的以及\\开头的转义字符，也要保持对应字符的格式不变'
                    },
                    {
                        "role": "user",
                        "content": toTranslateString
                    }
                ]
            )
            print(completion.choices[0].message.content.strip("\n"))
            translatedList.extend(
                completion.choices[0].message.content.split("\n"))
    except Exception as e:
        window.show_info("错误", f"翻译出现错误，请检查API配置和错误信息\n{e}")
        return

    if len(translatedList) != len(locator):
        window.show_info("错误", "翻译失败，翻译结果和原文长度不一致")
        return

    for i in range(len(locator)):
        translateMap[locator[i]]['target'] = translatedList[i]

    with open(translateWorkPath, "w", encoding="utf-8") as f:
        json.dump(translateMap, f, ensure_ascii=False, indent=4)
    window.show_info("提示", f"翻译成功，翻译结果已经写入{translateWorkPath}文件，你可以手动检查修正")


def writeBackToModpack():
    if DEVELOPMENT_MODE:
        folder_path = r"D:\Games\Prism Launcher\instances\All the Mods 10 - ATM10 - Updated\minecraft"
    else:
        if window:
            folder_path = window.get_selected_path()
            if not folder_path:
                window.show_info("提示", "请先选择整合包根目录")
                return
        else:
            folder_path = ui.getDirLocation(title="请选择要写回的整合包根目录")

    if not folder_path:
        window.show_info("提示", "未选择文件夹")
        return

    sourcePathConf = conf.getDefaultConfig('ftb_lang_source_path')
    sourcePath = f"{folder_path}/{sourcePathConf}"
    sourceTree = slib.load(open(sourcePath, "r", encoding="utf-8"))

    translateWorkPath = conf.getDefaultConfig('translate_work_path')
    translateFinePath = conf.getDefaultConfig('translate_fine_path')

    with open(translateWorkPath, "r", encoding="utf-8") as f:
        translateMap = json.load(f)

    for key, value in translateMap.items():
        dValue = slib.String(value['target'])
        exec('sourceTree' + key + ' = dValue')

    with open(translateFinePath, "r", encoding="utf-8") as f:
        translateMap = json.load(f)

    for key, value in translateMap.items():
        dValue = slib.String(value)
        exec('sourceTree' + key + ' = dValue')

    targetPathConf = conf.getDefaultConfig('ftb_lang_target_path')
    targetPath = f"{folder_path}/{targetPathConf}"
    slib.dump(sourceTree, open(targetPath, "w", encoding="utf-8"))
    window.show_info("提示", f"文件已经写回{targetPath}")


if __name__ == "__main__":
    from ui import MainWindow
    window = MainWindow()

    # 绑定按钮功能
    window.generate_button.config(command=generateTemporaryJson)
    window.translate_button.config(command=translateWithDeepseek)
    window.write_button.config(command=writeBackToModpack)
    window.extract_button.config(command=generateReferenceJson)

    # 运行主窗口
    window.run()
