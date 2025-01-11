import configparser
import os
import sys
from typing import Callable, List


if getattr(sys, 'frozen', False):    
    application_path = os.path.dirname(os.path.abspath(sys.executable))
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)

# 创建配置对象
configParser = configparser.ConfigParser()
# 读取配置文件
configParser.read('config.ini')

# 配置变更回调函数列表
_config_change_callbacks: List[Callable[[], None]] = []

def reload_config():
    """重新加载配置文件"""
    configParser.read('config.ini')
    # 通知所有注册的回调
    for callback in _config_change_callbacks:
        callback()

def register_config_change_callback(callback: Callable[[], None]):
    """注册配置变更回调"""
    _config_change_callbacks.append(callback)

def getConfig(section, key):
    return configParser.get(section, key)

def getDefaultConfig(key):
    return getConfig('DEFAULT', key)

def setConfig(section, key, value):
    configParser.set(section, key, value)

def flushConfig():
    with open('config.ini', 'w') as configfile:
        configParser.write(configfile)
    reload_config()
