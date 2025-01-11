#!/bin/bash
set -e

# 简单日志函数
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "开始构建"

# 删除旧dist目录
if [[ -d "dist" ]]; then
  log "删除旧dist目录"
  rm -rf ./dist/
fi

# 构建可执行文件
log "运行pyinstaller"
pyinstaller -w -F -n FTB任务翻译器 main.py

# 创建数据目录
log "创建数据目录"
mkdir -p ./dist/data

# 复制数据文件
log "复制数据文件"
cp ./data/reference.json ./dist/data/
cp config.ini ./dist/

log "构建完成"
