#!/bin/bash

# 获取当前目录下所有子文件夹的名字（不包括普通文件）
find . -maxdepth 1 -type d | while read -r dir;
do
    # 使用 basename 去掉路径，只保留文件夹名
    dirname=$(basename "$dir")

    # 排除当前目录 "." 自身
    if [ "$dirname" != "." ]; then
        echo "$dirname"
    fi
done > folder_list.txt

echo "文件夹列表已保存到 folder_list.txt"