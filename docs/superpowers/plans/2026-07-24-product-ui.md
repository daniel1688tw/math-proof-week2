# 商品化介面（Gradio 本機 Demo）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 QLoRA 蘇格拉底助教包成本機單人 Gradio 介面，讓使用者貼自己的題目（可含證明嘗試），系統自我驗證備課後 grounded 引導，備課失敗走同學模式。

**Architecture:** 新增 `dataset/app.py` Gradio 單體 App，啟動時常駐載入模型一次；`auto_reference.build_reference` 加選填 `progress_cb` 回呼供 UI 顯示備課進度；備課在背景執行緒跑、以佇列把階段串流到進度區；`TutorDriver` 與所有既有防護不改動。

**Tech Stack:** Python 3.11（lora_project env）、Gradio ≥4.44、既有 transformers/peft/bitsandbytes 推理堆疊、Ollama（備課思考型，離線自動降級）。

## Global Constraints

- 環境：Anaconda `lora_project`，執行前 `PYTHONNOUSERSITE=1`；跑法 `conda run -n lora_project --live-stream python <script>`。
- 語言慣例：介面文案、註解、回覆一律**繁體中文**。
- **不修改** `tutor_driver.py`、`regression_suite.py`、守門基準、部署 adapter。
- `build_reference` 的既有行為（含 `verbose` print、回傳 dict 結構）必須向後相容：不傳 `progress_cb` 時逐字不變。
- 部署 adapter 預設 `qlora_adapter_v9`（沿用 `interactive_turn.load_model`，`ADAPTER` env 可覆寫）。
- 單 GPU：Gradio 佇列 `concurrency_limit=1`，生成序列化。
- 模型載入必須只在 `python app.py` 直接執行時發生（`main()` 內），**不可**在 module import 時載入，否則單元測試需要 GPU。

---

### Task 1: `build_reference` 加選填 `progress_cb` 回呼

**Files:**
- Modify: `dataset/auto_reference.py`（`build_reference`，約 144-184 行）
- Test: `dataset/test_app.py`（新建，本任務先放 Task 1 測試）

**Interfaces:**
- Produces: `build_reference(statement: str, k: int = K_CANDIDATES, verbose: bool = True, progress_cb: Callable[[str, str], None] | None = None) -> dict`。`progress_cb(stage, detail)` 在每個既有 print 點被呼叫（`stage` ∈ {`"PROVER"`,`"VERIFIER"`,`"REPAIR"`,`"SEGMENTER"`}，`detail` 為如 `"1/3"` 的補充字串）。回傳 dict 結構不變。

- [ ] **Step 1: Write the failing test**

在新檔 `dataset/test_app.py`：

```python
# -*- coding: utf-8 -*-
"""app / auto_reference 備課回呼與組裝邏輯單元測試（不載模型、不連 Ollama）。"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import auto_reference


def _fake_chat_pass(system, user, temperature, timeout=600):
    if "標準參考解" in system:            # PROVER_SYSTEM
        return "證明：由假設可得結論。$\\blacksquare$"
    if "驗證員" in system:                # VERIFIER_SYSTEM
        return '{"verdict": "pass", "issues": []}'
    if "教學設計者" in system:            # SEGMENTER_SYSTEM
        return '[{"explain": "步驟一：套用定義", "check": "定義是什麼？"}]'
    return None


def test_progress_cb_fires_with_stages(monkeypatch):
    monkeypatch.setattr(auto_reference, "_chat", _fake_chat_pass)
    events = []
    result = auto_reference.build_reference(
        "證明 1+1=2", k=1, verbose=False,
        progress_cb=lambda stage, detail="": events.append((stage, detail)),
    )
    stages = [s for s, _ in events]
    assert result["status"] == "verified"
    assert "PROVER" in stages
    assert "VERIFIER" in stages
    assert "SEGMENTER" in stages


def test_no_progress_cb_is_backward_compatible(monkeypatch):
    monkeypatch.setattr(auto_reference, "_chat", _fake_chat_pass)
    result = auto_reference.build_reference("證明 1+1=2", k=1, verbose=False)
    assert result["status"] == "verified"
    assert result["reference_proof"].endswith("$\\blacksquare$")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n lora_project python -m pytest dataset/test_app.py::test_progress_cb_fires_with_stages -v`
Expected: FAIL（`build_reference() got an unexpected keyword argument 'progress_cb'`）

- [ ] **Step 3: Implement minimal change**

在 `dataset/auto_reference.py` 修改 `build_reference` 簽名與內部，加入 `_emit` 並在每個 print 點旁呼叫。改成：

```python
def build_reference(statement: str, k: int = K_CANDIDATES,
                    verbose: bool = True, progress_cb=None) -> dict:
    """回傳 {status, reference_proof?, teach_steps?, log}。"""
    def _emit(stage: str, detail: str = ""):
        if progress_cb:
            progress_cb(stage, detail)
    log = []
    for i in range(k):
        if verbose:
            print(f"  [PROVER {i+1}/{k}] 生成候選證明…")
        _emit("PROVER", f"{i+1}/{k}")
        proof = _chat(PROVER_SYSTEM, f"題目：{statement}", temperature=0.7)
        if not proof:
            log.append({"candidate": i, "event": "prover_failed"})
            continue
        if verbose:
            print(f"  [VERIFIER] 驗證候選 {i+1}（{len(proof)} 字）…")
        _emit("VERIFIER", f"候選 {i+1}")
        v = parse_verdict(_chat(
            VERIFIER_SYSTEM, f"題目：{statement}\n\n待驗證的證明：\n{proof}",
            temperature=0.2))
        log.append({"candidate": i, "verdict": v})
        if v is None:
            continue
        if v["verdict"] == "pass":
            if v["issues"]:
                if verbose:
                    print(f"  [REPAIR] pass 但有 {len(v['issues'])} 項小瑕疵，修補後複驗…")
                _emit("REPAIR", f"{len(v['issues'])} 項小瑕疵")
                fixed = _chat(REPAIR_SYSTEM,
                              f"題目：{statement}\n\n證明：\n{proof}\n\n"
                              f"審閱意見：{json.dumps(v['issues'], ensure_ascii=False)}",
                              temperature=0.2)
                if fixed:
                    v2 = parse_verdict(_chat(
                        VERIFIER_SYSTEM,
                        f"題目：{statement}\n\n待驗證的證明：\n{fixed}",
                        temperature=0.2))
                    log.append({"candidate": i, "repaired_verdict": v2})
                    if v2 and v2["verdict"] == "pass":
                        proof = fixed
            if verbose:
                print("  [SEGMENTER] 切分教學步驟…")
            _emit("SEGMENTER", "")
            steps = segment_proof(statement, proof) or fallback_steps(proof)
            return {"status": "verified", "reference_proof": proof,
                    "teach_steps": steps, "log": log}
    return {"status": "unverified", "log": log}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n lora_project python -m pytest dataset/test_app.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add dataset/auto_reference.py dataset/test_app.py
git commit -m "feat: build_reference 加選填 progress_cb 回呼（向後相容）"
```

---

### Task 2: `app.py` 純邏輯（組裝 / opener / Ollama 偵測）

**Files:**
- Create: `dataset/app.py`（僅本任務的純函式段；module import 不得載入模型）
- Test: `dataset/test_app.py`（追加）

**Interfaces:**
- Produces:
  - `check_ollama(url: str | None = None, timeout: int = 3) -> bool`
  - `assemble_problem(statement: str, result: dict, pid: str = "USER") -> dict` — verified 時含 `reference_proof`/`teach_steps`，`grounding` 為 `"auto_verified"`/`"unverified"`。
  - `opener_for(proof: str | None) -> str | None` — 空白/None → `None`（driver 用預設請求提示），否則回 strip 後字串（driver 當學生開場、路由審閱）。
- Consumes: 無（純函式）。

- [ ] **Step 1: Write the failing test**

在 `dataset/test_app.py` 追加：

```python
import app  # noqa: E402  （module import 不得載入模型——見 Task 3 的 main() 守則）


def test_assemble_problem_verified():
    result = {"status": "verified", "reference_proof": "P $\\blacksquare$",
              "teach_steps": [{"explain": "a", "check": "b"}], "log": []}
    prob = app.assemble_problem("  證明 X  ", result)
    assert prob["statement"] == "證明 X"
    assert prob["grounding"] == "auto_verified"
    assert prob["reference_proof"] == "P $\\blacksquare$"
    assert prob["teach_steps"]


def test_assemble_problem_unverified_triggers_peer():
    from tutor_driver import TutorDriver
    result = {"status": "unverified", "log": []}
    prob = app.assemble_problem("證明 Y", result)
    assert prob["grounding"] == "unverified"
    assert "reference_proof" not in prob
    # is_peer 只看 problem，不需模型
    d = TutorDriver.__new__(TutorDriver)
    d.problem = prob
    assert d.is_peer() is True


def test_opener_for():
    assert app.opener_for(None) is None
    assert app.opener_for("   ") is None
    assert app.opener_for("  我試著用歸納法  ") == "我試著用歸納法"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n lora_project python -m pytest dataset/test_app.py::test_opener_for -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app'`）

- [ ] **Step 3: Create `dataset/app.py` 純函式段**

```python
# -*- coding: utf-8 -*-
"""app.py — 蘇格拉底助教商品化介面（Gradio 本機單人 Demo）。

使用者貼上自己的題目（可含目前的證明嘗試），系統先自我驗證備課（auto_reference），
再由 TutorDriver 進行 grounded 引導；備課驗證失敗則走同學模式（誠實降級）。

啟動：
  conda run -n lora_project --live-stream python dataset/app.py
瀏覽器開 http://localhost:7860
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from auto_reference import build_reference  # noqa: E402
from tutor_driver import TutorDriver        # noqa: E402


# ── 純邏輯（可單元測試，不載模型、不連 Ollama）─────────────────────────────
def check_ollama(url: str | None = None, timeout: int = 3) -> bool:
    """偵測 Ollama 是否在線（備課功能依賴；離線時備課會降級為同學模式）。"""
    url = url or os.environ.get("OLLAMA_TAGS_URL", "http://localhost:11434/api/tags")
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except (urllib.error.URLError, OSError):
        return False


def assemble_problem(statement: str, result: dict, pid: str = "USER") -> dict:
    """把 build_reference 的結果組成 TutorDriver 需要的 problem dict。"""
    prob = {
        "id": pid,
        "statement": statement.strip(),
        "grounding": "auto_verified" if result["status"] == "verified" else "unverified",
    }
    if result["status"] == "verified":
        prob["reference_proof"] = result["reference_proof"]
        prob["teach_steps"] = result["teach_steps"]
    return prob


def opener_for(proof: str | None) -> str | None:
    """使用者貼的證明 → driver 的學生開場白；空則 None（driver 預設請求提示）。"""
    return (proof or "").strip() or None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n lora_project python -m pytest dataset/test_app.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add dataset/app.py dataset/test_app.py
git commit -m "feat: app.py 純邏輯（assemble_problem / opener_for / check_ollama）"
```

---

### Task 3: Gradio UI、模型常駐、備課串流與對話串接

**Files:**
- Modify: `dataset/app.py`（追加 `build_ui` / `main` 與 `if __name__` 區塊）
- Modify: `week3/README.md`（新增「商品化介面 / 啟動」段落）

**Interfaces:**
- Consumes: Task 1 的 `build_reference(..., progress_cb=…)`；Task 2 的 `check_ollama` / `assemble_problem` / `opener_for`；`interactive_turn.load_model()`（回 `(tok, model)`，預設 adapter v9）；`TutorDriver(tok, model, problem).start(opener)` / `.step(text)`。
- Produces: `build_ui(tok, model) -> gr.Blocks`；`main()`（載模型→建 UI→`launch`）。模型載入只在 `main()` 內發生。

- [ ] **Step 1: 追加 UI/串流/主程式到 `dataset/app.py`**

接在 Task 2 的純函式之後追加：

```python
# ── 備課背景執行緒 + 佇列串流（供 UI 逐步顯示階段）─────────────────────────
def _run_prepare(statement: str):
    """generator：先 yield 進度字串，最後 yield ('__result__', result_dict)。"""
    q: "queue.Queue" = queue.Queue()
    holder: dict = {}

    def worker():
        def cb(stage: str, detail: str = ""):
            q.put(f"{stage} {detail}".strip())
        holder["result"] = build_reference(statement, progress_cb=cb)
        q.put(None)

    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = q.get()
        if item is None:
            break
        yield item
    yield ("__result__", holder["result"])


# ── Gradio UI ──────────────────────────────────────────────────────────────
def build_ui(tok, model):
    import gradio as gr

    ollama_warn = "" if check_ollama() else \
        "⚠️ 未偵測到 Ollama 服務：備課需要 Ollama，目前所有題目會走同學模式。\n"

    with gr.Blocks(title="蘇格拉底數學證明助教") as demo:
        gr.Markdown("# 蘇格拉底數學證明助教\n貼上你的證明題，助教會先自己備課再一步步引導你（不直接給答案）。")
        if ollama_warn:
            gr.Markdown(ollama_warn)

        driver_state = gr.State(None)

        with gr.Group() as input_group:
            statement_tb = gr.Textbox(label="題目敘述（必填）", lines=4,
                                      placeholder="例：證明連續函數在閉區間上有界。")
            proof_tb = gr.Textbox(label="你目前的證明／嘗試（可留空）", lines=6,
                                  placeholder="沒有頭緒可留空，助教會從第一個提示開始引導。")
            prepare_btn = gr.Button("開始備課", variant="primary")

        progress_md = gr.Markdown("")

        with gr.Group(visible=False) as chat_group:
            chatbot = gr.Chatbot(label="對話", type="messages", height=460)
            with gr.Row():
                msg_tb = gr.Textbox(label="你的回覆", scale=5, lines=2)
                send_btn = gr.Button("送出", scale=1, variant="primary")
            reset_btn = gr.Button("重新開始（換一題）")

        def on_prepare(statement, proof):
            if not (statement or "").strip():
                yield (gr.update(value="請先輸入題目。"),
                       gr.update(visible=True), gr.update(visible=False), [], None)
                return
            lines = []
            result = None
            for item in _run_prepare(statement):
                if isinstance(item, tuple) and item[0] == "__result__":
                    result = item[1]
                    break
                lines.append("• " + item)
                yield ("\n".join(lines), gr.update(visible=True),
                       gr.update(visible=False), [], None)
            problem = assemble_problem(statement, result)
            driver = TutorDriver(tok, model, problem)
            reply = driver.start(opener=opener_for(proof))
            if result["status"] == "verified":
                lines.append("✅ 備課完成（grounded），開始引導。")
            else:
                lines.append("⚠️ 這題我沒能自己驗證出可靠解，將以同儕身分陪你探索（同學模式）。")
            first_user = opener_for(proof) or "（請助教給第一個提示）"
            chat = [{"role": "user", "content": first_user},
                    {"role": "assistant", "content": reply}]
            yield ("\n".join(lines), gr.update(visible=False),
                   gr.update(visible=True), chat, driver)

        def on_send(message, chat, driver):
            if driver is None or not (message or "").strip():
                return "", chat
            reply = driver.step(message)
            chat = chat + [{"role": "user", "content": message},
                           {"role": "assistant", "content": reply}]
            return "", chat

        def on_reset():
            return (gr.update(value="", visible=True), gr.update(visible=False),
                    "", [], None, "", "")

        prepare_btn.click(
            on_prepare, [statement_tb, proof_tb],
            [progress_md, input_group, chat_group, chatbot, driver_state])
        send_btn.click(on_send, [msg_tb, chatbot, driver_state], [msg_tb, chatbot])
        msg_tb.submit(on_send, [msg_tb, chatbot, driver_state], [msg_tb, chatbot])
        reset_btn.click(
            on_reset, None,
            [input_group, chat_group, progress_md, chatbot, driver_state,
             statement_tb, proof_tb])

    demo.queue(default_concurrency_limit=1)
    return demo


def main():
    from interactive_turn import load_model
    print("[app] 載入模型中（首次約需 30–60 秒）…", flush=True)
    tok, model = load_model()
    print("[app] 模型就緒，啟動介面 http://localhost:7860", flush=True)
    build_ui(tok, model).launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 確認純邏輯測試仍過（未回歸）**

Run: `conda run -n lora_project python -m pytest dataset/test_app.py -v`
Expected: 5 passed（UI 函式不在測試範圍，但 import app 不得載模型 → 全過即證明 module 未在 import 時載入）

- [ ] **Step 3: 安裝 gradio 並啟動 app 做手動驗收**

```bash
conda run -n lora_project pip install "gradio>=4.44"
conda run -n lora_project --live-stream python dataset/app.py
```

手動驗收（瀏覽器 http://localhost:7860）：
1. 只貼題目、證明留空 → 進度區出現 `PROVER/VERIFIER/SEGMENTER` → 對話展開，助教給第一個提示而非答案。
2. 貼含明顯錯誤的證明 → 助教審閱、指出問題並引導改正（不奉送正解）。
3. 停掉 Ollama 再貼題 → 頂端顯示 Ollama 警告、走同學模式並誠實聲明沒把握。
4. 「重新開始」→ 回到輸入區可換題。

- [ ] **Step 4: README 增補啟動段落**

在 `week3/README.md` 適當位置新增：

```markdown
## 商品化介面（本機單人 Demo）

貼上自己的證明題（可含目前的證明嘗試），助教先自我驗證備課再蘇格拉底式引導。

    conda run -n lora_project pip install "gradio>=4.44"   # 首次
    conda run -n lora_project --live-stream python dataset/app.py

瀏覽器開 http://localhost:7860。備課需要 Ollama 在線（`qwen3-4b-thinking-2507`）；
離線時所有題目改走同學模式（誠實降級）。RTX 4050 6GB：模型常駐約 3.5GB，備課時
Ollama 會被擠到 CPU 而變慢，屬 Demo 可接受的固有限制。
```

- [ ] **Step 5: Commit**

```bash
git add dataset/app.py README.md
git commit -m "feat: Gradio 商品化介面（備課串流 + grounded/同學模式對話）"
```

---

## Self-Review

**Spec coverage：**
- 貼題（含/不含證明）→ Task 3 `on_prepare` + `opener_for`。✅
- 只有題目、無方向逐級引導 → `opener=None` 走 driver 預設提示。✅
- 錯誤證明引導改正 → `opener=proof` 路由 review（driver 既有）。✅
- 備課進度畫面 → Task 1 `progress_cb` + Task 3 `_run_prepare` 佇列串流。✅
- unverified → 同學模式 → `assemble_problem` grounding + driver `is_peer()`。✅
- 模型常駐一次 → Task 3 `main()`。✅
- Ollama 離線降級 + 預警 → `check_ollama` + `_chat` 回 None 落 unverified。✅
- 不改 driver/守門 → 僅動 auto_reference 一處回呼、新增 app.py/test_app.py/README。✅
- 不做 token 串流 → `on_send` 單次回完整文本。✅

**Placeholder scan：** 無 TBD/TODO；每段皆含完整程式碼與指令。✅

**Type consistency：** `build_reference(..., progress_cb)`、`assemble_problem`/`opener_for`/`check_ollama` 簽名、`load_model()->(tok,model)`、`TutorDriver.start/step` 於各任務一致。✅
