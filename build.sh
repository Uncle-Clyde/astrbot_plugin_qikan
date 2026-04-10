#!/bin/bash
# astrbot_plugin_qikan 前端构建脚本
# 用于自动构建 qikan-ui 和 skill-tree-ui 并复制到 static 目录

set -e  # 遇到错误立即退出

echo "开始构建 astrbot_plugin_qikan 前端..."

# 构建 qikan-ui
echo "构建 qikan-ui..."
cd qikan-ui
npm install
npm run build
cd ..

# 构建 skill-tree-ui
echo "构建 skill-tree-ui..."
cd skill-tree-ui
npm install
npm run build
cd ..

# 清理旧的静态文件
echo "清理旧的静态文件..."
rm -rf static/assets/*
rm -rf static/index.html

# 复制新的构建产物
echo "复制构建产物到 static/..."
cp -r qikan-ui/dist/* static/
cp -r skill-tree-ui/dist/* static/

echo "前端构建完成！"
echo "构建产物已复制到 static/ 目录"