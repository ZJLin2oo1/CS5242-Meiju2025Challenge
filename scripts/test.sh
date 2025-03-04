#!/bin/bash

# SBATCH - 资源分配（1个GPU）
#SBATCH --output=/home/l/linzijie/MEIJU/codebase/log/output_%j.log  # 输出日志文件，%j表示任务ID
#SBATCH --error=/home/l/linzijie/MEIJU/codebase/log/error_%j.log  # 错误日志文件

source ~/.bashrc
conda activate meiju

# 打印当前时间和工作目录
echo "当前时间: $(date)"
echo "当前工作目录: $(pwd)"

# 运行简单的 Python 脚本（可以替换为实际需要运行的脚本）
echo "开始运行测试脚本..."
python -c "print('Hello, sbatch!')"

# 结束作业
echo "测试脚本运行完毕."

echo "作业开始运行于: $(date)"
echo "主机名: $(hostname)"

echo "CPU 信息:"
lscpu

echo "内存信息:"
free -h

echo "GPU 信息:"
nvidia-smi

echo "CUDA 版本:"
nvcc --version

echo "测试 CUDA 功能..."
cat <<EOF > cuda_test.cu
#include <stdio.h>

__global__ void cuda_hello(){
    printf("Hello World from GPU!\n");
}

int main() {
    cuda_hello<<<1,1>>>();
    cudaDeviceSynchronize();
    return 0;
}
EOF

nvcc cuda_test.cu -o cuda_test
./cuda_test

echo "作业结束运行于: $(date)"
