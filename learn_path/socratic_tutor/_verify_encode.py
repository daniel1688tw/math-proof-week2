"""快速驗證 SocraticDataset 的編碼/ masking 正確（只載 tokenizer，不載模型）。"""
import os, sys
os.environ.setdefault("PYTHONNOUSERSITE", "1")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pyarrow, datasets  # noqa  預載 DLL
from transformers import AutoTokenizer
from common import MODEL_NAME, TRAIN_JSONL
from train_qlora import SocraticDataset

tok = AutoTokenizer.from_pretrained(MODEL_NAME)
if tok.pad_token_id is None:
    tok.pad_token = tok.eos_token

ds = SocraticDataset(TRAIN_JSONL, tok, max_len=1024)
ex = ds[0]
ii, lb = ex["input_ids"], ex["labels"]
print("input_ids 型別:", type(ii).__name__, "首5:", ii[:5])
print("全為 int:", all(isinstance(x, int) for x in ii))
print("長度 input/labels:", len(ii), len(lb))
n_train = sum(1 for x in lb if x != -100)
print(f"可訓練(非-100) token 數: {n_train} / {len(lb)}")
# 解碼 assistant 片段（labels != -100 的部分）看是否確實是老師回覆
asst = [ii[k] for k in range(len(lb)) if lb[k] != -100]
print("assistant 片段解碼預覽:", tok.decode(asst)[:200].replace("\n", " "))
print("OK")
