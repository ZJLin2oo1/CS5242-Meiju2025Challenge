import os
import numpy as np

# 指定目标目录
dir_path = '/home/l/linzijie/MEIJU/track2_data/Mandarin_preproc/features/resnet50face_UTT'

# 获取目录下所有的 .npy 文件
npy_files = [f for f in os.listdir(dir_path) if f.endswith('.npy')]

if npy_files:
    # 读取第一个 .npy 文件
    first_file = npy_files[0]
    file_path = os.path.join(dir_path, first_file)

    # 加载 .npy 文件
    data = np.load(file_path)

    # 输出数据的形状
    print(f"First file: {first_file}")
    print(f"Shape of the file: {data.shape}")
else:
    print("No .npy files found in the directory.")