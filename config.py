import configparser
from typing import Callable, List

# 创建配置对象
config = configparser.ConfigParser()

# 读取配置文件
config.read('config.ini')

# 配置变更回调函数列表
_config_change_callbacks: List[Callable[[], None]] = []

def reload_config():
    """重新加载配置文件"""
    config.read('config.ini')
    # 通知所有注册的回调
    for callback in _config_change_callbacks:
        callback()

def register_config_change_callback(callback: Callable[[], None]):
    """注册配置变更回调"""
    _config_change_callbacks.append(callback)

def getConfig(section, key):
    return config.get(section, key)

def getDefaultConfig(key):
    return getConfig('DEFAULT', key)
