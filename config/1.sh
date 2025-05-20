#!/bin/bash

# 定义目标文件
LIST_FILE="folder_list.txt"

# 检查 folder_list.txt 是否存在
if [ ! -f "$LIST_FILE" ]; then
  echo "错误：找不到文件 $LIST_FILE"
  exit 1
fi

# 逐行读取文件并创建文件夹
while IFS= read -r line
do
  # 去除行首行尾空白字符
  folder_name=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

  # 忽略空行
  if [ -n "$folder_name" ]; then
    mkdir -p "$folder_name"
    echo "已创建文件夹：$folder_name"
  fi
done < "$LIST_FILE"

echo "所有文件夹创建完成。"