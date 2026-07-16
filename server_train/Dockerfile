# QLoRA 訓練容器（192.168.1.102，RTX 4090）
# 基底鏡像自帶 torch 2.5.1 + CUDA 12.4，與本機 lora_project 環境同版，行為可對照。
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/workspace/hf_cache \
    TOKENIZERS_PARALLELISM=false

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /workspace
