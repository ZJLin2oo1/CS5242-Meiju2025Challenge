#!/bin/bash

#SBATCH --ntasks=1                    # 任务数量，默认1
# SBATCH --cpus-per-task=4             # 每个任务分配4个CPU
#SBATCH --time=10:00:00               # 运行时间10小时 (格式: HH:MM:SS)
#SBATCH --output=/home/l/linzijie/MEIJU/codebase/log/output_%j.log  # 输出日志文件，%j表示任务ID
#SBATCH --error=/home/l/linzijie/MEIJU/codebase/log/error_%j.log  # 错误日志文件

source ~/.bashrc
conda activate meiju

cd feature_extraction/audio
#python feature_extraction_main.py split_audio_from_video_16k '/home/l/linzijie/MEIJU/track2_data/English_preproc/Videos' '/home/l/linzijie/MEIJU/track2_data/English_preproc/Audios'
python -u extract_wav2vec_embedding.py       --dataset=Track2_English --feature_level=FRAME --gpu=0
# 打印当前时间和工作目录
echo "当前时间: $(date)"
echo "当前工作目录: $(pwd)"


#
#cd feature_extraction/visual
#python extract_openface.py --dataset=Track2_Mandarin
#
##python -u extract_manet_embedding.py \
##    --dataset=Track2_Mandarin \
##    --feature_level=FRAME \
##    --gpu=0
