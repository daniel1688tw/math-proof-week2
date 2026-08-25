"""
train_qlora.py — 用 QLoRA（4-bit nf4 + LoRA）把 Qwen3-4B 微調成蘇格拉底引導式數學助教。

設計重點：
  * 4-bit nf4 量化載入 4B 基底，只訓練 LoRA adapter；6 GiB VRAM 可行。
  * 對話用 Qwen3 chat template 渲染；**只對 assistant（老師）回合算 loss**，
    user/system token 標為 -100（masking），讓模型學「引導語氣」而非複誦學生輸入。
  * gradient_checkpointing + paged_adamw_8bit + bf16，盡量壓低顯存。
  * 序列長度上限 MAX_LEN=512（6 GiB 安全值；improve.md 問題⑨：先前文件誤植 1024，
    程式實際預設與安全值皆為 512）。太長的對話會被截斷；截斷後若整段沒有 assistant
    token 就丟棄，避免 loss 為 NaN。
  * improve.md 問題⑥：load_best_model_at_end + EarlyStopping，存「eval_loss 最佳」的
    checkpoint（而非最後一步），並在 eval_loss 停滯時提早停，省時又少過擬合。

執行：
  conda run -n lora_project --live-stream python train_qlora.py
可調整的環境變數：EPOCHS / MAX_LEN / BATCH / GRAD_ACCUM / LR / LORA_R
"""

from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Windows DLL 衝突修正（重要）──────────────────────────────────────────────
# transformers.Trainer 會在匯入時連帶 import datasets→pandas→pyarrow。若 torch 先載入、
# pyarrow 的 Arrow DLL 後載入，會發生 access violation（segfault，exit 255）。
# 解法：在 torch 之前先「預載」pyarrow 與 datasets，讓 Arrow DLL 先就位。
import pyarrow  # noqa: F401  (僅為預載 DLL)
import datasets  # noqa: F401

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

from common import ADAPTER_DIR, MODEL_NAME, TRAIN_JSONL, VAL_JSONL

# ── 超參數（可用環境變數覆寫）─────────────────────────────────────────────
EPOCHS = float(os.environ.get("EPOCHS", "2"))
# MAX_LEN=512：乾淨 GPU 上實測 reserved 5.57GB（穩在專用 6GB 內）、每 micro-step 1.7s。
# 更長會讓 PyTorch 保留池碎片化破 6GB → 溢出系統記憶體 → 步速 4 倍慢且不可恢復。
# 多數對話 <512 token，被截斷者仍保留最重要的前期引導回合。
MAX_LEN = int(os.environ.get("MAX_LEN", "512"))
BATCH = int(os.environ.get("BATCH", "1"))
GRAD_ACCUM = int(os.environ.get("GRAD_ACCUM", "16"))
LR = float(os.environ.get("LR", "2e-4"))
LORA_R = int(os.environ.get("LORA_R", "16"))
LORA_ALPHA = int(os.environ.get("LORA_ALPHA", "32"))

TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


# ─────────────────────────────────────────────────────────────────────────────
# 資料集：讀 jsonl → 用 chat template tokenize → 只對 assistant 算 loss
# ─────────────────────────────────────────────────────────────────────────────

def _load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class SocraticDataset(Dataset):
    def __init__(self, path: str, tokenizer, max_len: int):
        self.tok = tokenizer
        self.max_len = max_len
        raw = _load_jsonl(path)
        self.examples = []
        skipped = 0
        for ex in raw:
            built = self._build(ex["messages"])
            if built is None:
                skipped += 1
                continue
            self.examples.append(built)
        print(f"  {os.path.basename(path)}: 可用 {len(self.examples)} / 跳過 {skipped}")

    def _encode(self, messages: list[dict]) -> list[int]:
        """把訊息渲染成字串再 tokenize，確保回傳乾淨的 list[int]。

        注意：transformers 5.x 的 apply_chat_template(tokenize=True) 會回傳
        tokenizers.Encoding 物件而非 list[int]，故這裡用 tokenize=False 取字串，
        再以 add_special_tokens=False 自行 tokenize（模板已含 <|im_start|> 等特殊標記）。
        """
        text = self.tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        return self.tok(text, add_special_tokens=False)["input_ids"]

    def _fit_window(self, messages: list[dict]):
        """超長對話：捨棄最舊回合、保留「含 assistant 的最新窗口」（左截斷而非砍後段）。

        原作法保留前 max_len token，導致長 MathDial 多輪對話只剩開頭、甚至首個老師回合
        在 512 之後而整筆被丟（實測 803 筆）。改成保留結尾的多輪片段，救回這些樣本、
        也讓模型學到「後段回合」的引導。窗口必以 user 開頭、且含 assistant。
        """
        sys_msg, rest = messages[0], messages[1:]
        for start in range(len(rest)):
            if rest[start]["role"] != "user":
                continue
            window = [sys_msg] + rest[start:]
            if not any(m["role"] == "assistant" for m in window):
                break
            if len(self._encode(window)) <= self.max_len:
                return window
        return None

    def _build(self, messages: list[dict]):
        """逐訊息累積 token，只把 assistant 回合的 token 設為訓練目標。"""
        # 超長 → 改用「含 assistant 的最新窗口」（左截斷），而非保留前 512 致後段被砍光
        if len(self._encode(messages)) > self.max_len:
            window = self._fit_window(messages)
            if window is not None:
                messages = window

        input_ids: list[int] = []
        labels: list[int] = []
        for i, msg in enumerate(messages):
            prefix = self._encode(messages[: i + 1])
            # 前綴一致性檢查；Qwen template tokenize 後通常前綴穩定
            if prefix[: len(input_ids)] != input_ids:
                # 萬一不一致，退回「整段都算 loss」避免錯位（極罕見）
                input_ids = prefix
                labels = list(prefix)
                continue
            new = prefix[len(input_ids):]
            if msg["role"] == "assistant":
                labels.extend(new)
            else:
                labels.extend([-100] * len(new))
            input_ids = prefix

        input_ids = input_ids[: self.max_len]
        labels = labels[: self.max_len]
        # 截斷後整段都沒有 assistant token → 無法學習，丟棄
        if all(t == -100 for t in labels):
            return None
        return {"input_ids": input_ids, "labels": labels}

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return self.examples[idx]


class Collator:
    """把一個 batch 內的序列右側 padding 到等長。"""

    def __init__(self, pad_id: int):
        self.pad_id = pad_id

    def __call__(self, batch: list[dict]) -> dict:
        maxlen = max(len(b["input_ids"]) for b in batch)
        input_ids, labels, attn = [], [], []
        for b in batch:
            n = len(b["input_ids"])
            pad = maxlen - n
            input_ids.append(b["input_ids"] + [self.pad_id] * pad)
            labels.append(b["labels"] + [-100] * pad)
            attn.append([1] * n + [0] * pad)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
            "attention_mask": torch.tensor(attn, dtype=torch.long),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # 啟動前檢查可用 VRAM；殘留的孤兒 python 進程會偷顯存導致訓練雪崩。
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        print(f"[0/5] GPU 可用 {free/1024**3:.2f}/{total/1024**3:.2f} GiB")
        if free < 5.0 * 1024 ** 3:
            print("[警告] 可用 VRAM < 5GiB，可能有殘留 python 進程佔用顯存！"
                  "請先在外部執行：Get-Process python | Stop-Process -Force，再重跑。")

    print(f"[1/5] 載入 tokenizer：{MODEL_NAME}")
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    print("[2/5] 準備資料集（chat template + assistant-only masking）")
    train_ds = SocraticDataset(TRAIN_JSONL, tok, MAX_LEN)
    val_ds = SocraticDataset(VAL_JSONL, tok, MAX_LEN)
    collator = Collator(tok.pad_token_id)

    print(f"[3/5] 4-bit nf4 載入基底模型：{MODEL_NAME}")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb,
        device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )

    print(f"[4/5] 套用 LoRA (r={LORA_R}, alpha={LORA_ALPHA})")
    lora = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=TARGET_MODULES,
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    max_steps = int(os.environ.get("MAX_STEPS", "0"))  # >0 時用於快速煙霧測試
    args = TrainingArguments(
        output_dir=os.path.join(ADAPTER_DIR, "_checkpoints"),
        num_train_epochs=EPOCHS,
        max_steps=max_steps if max_steps > 0 else -1,
        per_device_train_batch_size=BATCH,
        per_device_eval_batch_size=BATCH,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=int(os.environ.get("EVAL_STEPS", "50")),
        save_strategy="steps",
        # 與 eval_steps 對齊，load_best_model_at_end 要求一致
        save_steps=int(os.environ.get("EVAL_STEPS", "50")),
        save_total_limit=2,
        load_best_model_at_end=True,      # improve.md 問題⑥：存「eval_loss 最佳」而非最後一步
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=True,
        # gradient checkpointing 已由 prepare_model_for_kbit_training 啟用，
        # 這裡不重複開啟，避免 Trainer 二次 enable 造成衝突。
        gradient_checkpointing=False,
        # 優化器可用 OPTIM 覆寫。paged_adamw_8bit 用 CUDA managed memory，在 WDDM 上
        # 被 abrupt kill 後 managed-memory 子系統可能壞掉（bnb pythonInterface 初始化錯誤）；
        # 此時改用非分頁 adamw_8bit（LoRA 僅 33M 參數、優化器狀態極小，不需分頁）。
        optim=os.environ.get("OPTIM", "paged_adamw_8bit"),
        # NEFTune：對 embedding 加均勻噪音，小資料 SFT 常見 +1~3% 品質增益、抑制過擬合。
        # 設 NEFTUNE_ALPHA=5 啟用；0（預設）停用。
        neftune_noise_alpha=(float(os.environ["NEFTUNE_ALPHA"])
                             if float(os.environ.get("NEFTUNE_ALPHA", "0")) > 0 else None),
        max_grad_norm=0.3,
        report_to="none",
        dataloader_num_workers=0,   # Windows 下避免多進程問題
    )

    # 用標準 Trainer：由模型內建 loss（ForCausalLMLoss）計算，正確處理 grad accum
    # 的 num_items_in_batch 縮放。乾淨 GPU 上 512 序列峰值 ~5.2GB < 6GB，記憶體夠用，
    # 不需要自訂 chunked CE（其未處理 num_items_in_batch 會讓 loss/梯度被 16× 放大）。
    # improve.md 問題⑥：eval_loss 約 0.8 epoch 後即停滯，加 EarlyStopping 提早收手。
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    print("[5/5] 開始訓練…")
    trainer.train()

    os.makedirs(ADAPTER_DIR, exist_ok=True)
    model.save_pretrained(ADAPTER_DIR)
    tok.save_pretrained(ADAPTER_DIR)
    print(f"\n[完成] LoRA adapter 已存到：{ADAPTER_DIR}")


if __name__ == "__main__":
    main()
