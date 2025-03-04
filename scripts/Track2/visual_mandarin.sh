# bash scripts/Track2/Mandarin_pretrain.sh
set -e
run_idx=$1
gpu=$0

for i in `seq 1 1 1`;
do

cmd="python train_baseline.py --dataset_mode=multimodal --model=visual
--log_dir=./logs --checkpoints_dir=./checkpoints --gpu_ids=$gpu
--input_dim_a=512 --embd_size_a=128 --embd_method_a=maxpool
--input_dim_v=512 --embd_size_v=128  --embd_method_v=maxpool
--input_dim_l=768 --embd_size_l=128  --hidden_size=128
--A_type=wav2vec-large_frame-c-FRA --V_type=resnet50face_FRA --L_type=chinese-roberta-wwm-ext-4-FRA
--num_thread=2 --corpus=MEIJU_Mandarin
--emo_output_dim=7 --int_output_dim=8 --track=2
--ce_weight=1.0 --cls_layers=128,64 --dropout_rate=0.2
--niter=20 --niter_decay=40 --print_freq=10
--batch_size=32 --lr=2e-4 --run_idx=$run_idx --weight_decay=1e-5
--name=visual_mandarin --suffix=run_{gpu_ids}_{run_idx}
--cvNo=$i"


echo "\n-------------------------------------------------------------------------------------"
echo "Execute command: $cmd"
echo "-------------------------------------------------------------------------------------\n"
echo $cmd | sh

done
