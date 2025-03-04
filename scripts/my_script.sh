#!/bin/bash
#SBATCH --output=/home/l/linzijie/MEIJU/codebase/log/output_%j.log  # 输出日志文件，%j表示任务ID
#SBATCH --error=/home/l/linzijie/MEIJU/codebase/log/error_%j.log  # 错误日志文件
source ~/.bashrc
conda activate meiju

# 定义目标目录
target_dir="/home/l/linzijie/MEIJU/track2_data/English_preproc/features/roberta-base-4-FRA"

# 使用 for 循环遍历目录中符合条件的文件
for file in "$target_dir"/*.mkv.npy; do
    # 获取不带 .mkv 的新文件名
    new_file="${file/.mkv.npy/.npy}"

    # 重命名文件
    mv "$file" "$new_file"
done
#python feature_extraction_main.py extract_data_to_txt --csv_file='/home/l/linzijie/MEIJU/track2_data/English_preproc/transcription.csv' --txt_file='/home/l/linzijie/MEIJU/track2_data/English_preproc/Training.txt'


