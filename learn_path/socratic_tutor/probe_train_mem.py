"""
probe_train_mem.py — 訓練步顯存診斷：判定雪崩是「洩漏」還是「碎片化/系統記憶體回退」，
並對照「分頁 vs 非分頁優化器」。

做法：用與訓練相同的設定（4-bit + LoRA + grad checkpoint），對固定長度 512 的 dummy
batch 連跑 14 個訓練步（forward + chunked CE + backward + optimizer step），每步印出
allocated / max_allocated / reserved 與耗時。

判讀：
  * allocated 每步上升 → 記憶體洩漏（要找持有 reference 的地方）。
  * allocated 穩定但 reserved 上升、時間暴增 → 碎片化 / Windows 系統記憶體回退。
  * 換非分頁優化器後若穩定 → 元兇是 paged optimizer 的 CPU↔GPU 分頁。

用環境變數 OPT 切換：OPT=paged（預設）/ OPT=adamw8bit / OPT=adamw_torch
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pyarrow, datasets  # noqa: F401  預載 DLL
import torch
import torch.nn.functional as F
import bitsandbytes as bnb
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

from common import MODEL_NAME

SEQ = int(os.environ.get("SEQ", "512"))
STEPS = int(os.environ.get("STEPS", "14"))
OPT = os.environ.get("OPT", "paged")
GB = 1024 ** 3


def main():
    bnbcfg = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnbcfg, device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.train()

    params = [p for p in model.parameters() if p.requires_grad]
    if OPT == "adamw8bit":
        opt = bnb.optim.AdamW8bit(params, lr=2e-4)
    elif OPT == "adamw_torch":
        opt = torch.optim.AdamW(params, lr=2e-4)
    else:
        opt = bnb.optim.PagedAdamW8bit(params, lr=2e-4)
    print(f"模型載入後：allocated={torch.cuda.memory_allocated()/GB:.2f}GB "
          f"reserved={torch.cuda.memory_reserved()/GB:.2f}GB  OPT={OPT} SEQ={SEQ}", flush=True)

    ids = torch.randint(0, 150000, (1, SEQ), device="cuda")
    attn = torch.ones_like(ids)
    labels = ids.clone()

    for step in range(STEPS):
        torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        out = model(input_ids=ids, attention_mask=attn)
        logits = out.logits
        shift_logits = logits[:, :-1, :]
        shift_labels = labels[:, 1:]
        V = shift_logits.size(-1)
        fl = shift_logits.reshape(-1, V)
        fb = shift_labels.reshape(-1)
        total = fl.new_zeros(())
        for i in range(0, fl.size(0), 256):
            total = total + F.cross_entropy(fl[i:i+256].float(), fb[i:i+256], reduction="sum")
        loss = total / fb.numel()
        loss.backward()
        opt.step(); opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        dt = time.time() - t0
        print(f"step {step:2d}: loss={loss.item():.3f}  "
              f"alloc={torch.cuda.memory_allocated()/GB:.2f}GB  "
              f"peak={torch.cuda.max_memory_allocated()/GB:.2f}GB  "
              f"reserved={torch.cuda.memory_reserved()/GB:.2f}GB  {dt:.1f}s", flush=True)


if __name__ == "__main__":
    main()
