import importlib.metadata as m
for p in ['torch','transformers','accelerate','bitsandbytes','peft','trl','datasets','flash_attn','huggingface_hub','sentencepiece']:
    try:
        print(p, m.version(p))
    except Exception:
        print(p, 'NOT_INSTALLED')
import torch
print('cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')
if torch.cuda.is_available():
    free, total = torch.cuda.mem_get_info()
    print('vram_free_GiB', round(free/1024**3,2), 'total_GiB', round(total/1024**3,2))
    print('bf16_supported', torch.cuda.is_bf16_supported())
