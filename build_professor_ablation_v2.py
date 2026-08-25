from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "教授問題_四組消融實驗_Colab.ipynb"
TARGET = ROOT / "教授問題_四組消融實驗_Colab_v2.ipynb"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
cells = notebook["cells"]

cells[0]["source"] = r'''# 兩顆模型都會引導，為什麼仍需要本專案？

本專案的價值不是「讓原本完全不會教的模型突然會教」，而是把模型原本帶有機率性的引導能力，工程化成**穩定、可控制、可量測的教學系統**。

本 notebook 直接對應四個價值主張：

1. **風格是統計分布，不是明確規則**：比較 Prompt、Few-shot、LoRA 與 Full-Project 在首次提示、錯誤草稿與逼問完整答案時的契約違規率。
2. **Prompt 會隨多輪對話漂移**：連續三輪表示卡住，量測風格保留率，以及 Full-Project 是否依狀態機進入 walkthrough。
3. **Few-shot 有持續性的 token 負擔**：額外加入 4 組完整示範，實測每次請求的輸入 token、輸出 token 與延遲；LoRA 不需要在每次請求重送示範。
4. **邊界條件需要明確控制**：量測一輪一問、拒絕代寫、不洩漏參考證明，以及 Thinking reviewer 的 JSON 解析率與可用率。

測試條件：

1. `Base-Instruct + Prompt`
2. `Base-Instruct + 4-Shot`
3. `Base-Thinking + Prompt`（GGUF + Ollama，與 `test.ipynb` 相同）
4. `LoRA-only`
5. `Full-Project`（LoRA + TutorDriver + 守衛 + Thinking reviewer）

> 論證重點是「可靠控制」而非挑最好看的個案。所有失敗、截斷與 JSON 解析失敗都會保留並計入結果。
'''

cells[2]["source"] = r'''# Instruct/LoRA 推論、量化與繪圖套件；Thinking GGUF/Ollama 會在後面依 test.ipynb 安裝。
%pip install -q "transformers>=4.51.0,<6" "peft>=0.15,<1" "accelerate>=1.2" "bitsandbytes>=0.45" pandas matplotlib seaborn
'''

cell3 = cells[3]["source"]
cell3 = replace_once(
    cell3,
    "from pathlib import Path\nimport os\n",
    "from pathlib import Path\nimport os\nimport platform\nimport shutil\nimport subprocess\nimport urllib.error\nimport urllib.request\n",
    "cell3 imports",
)
cell3 += r'''

def run_checked(args, *, cwd=None, env=None):
    print("+", " ".join(map(str, args)))
    return subprocess.run(
        [str(x) for x in args],
        cwd=str(cwd) if cwd else None,
        env=env,
        check=True,
    )
'''
cells[3]["source"] = cell3

cells[4]["source"] = r'''## 1. 實驗設定

三道指定證明題各測三個單輪情境：首次求提示、帶錯草稿、逼問完整答案。另以三輪明確的 `I don't know` 測試 Prompt 漂移與狀態升級。

`Base-Instruct + 4-Shot` 使用四組與目標題無關的完整示範，只用來量化 In-Context Learning 的持續 token 成本與行為穩定度；不把目標題答案藏在示範中。
'''

cell5 = cells[5]["source"]
cell5 = replace_once(
    cell5,
    'MAX_NEW_TOKENS = 192\nMAX_THINKING_TOKENS = 768  # 若 Thinking 常顯示截斷，可提高到 1024\nINSTRUCT_ID = "Qwen/Qwen3-4B-Instruct-2507"\nTHINKING_ID = "Qwen/Qwen3-4B-Thinking-2507"\nRESULT_DIR = PROJECT_CONTAINER / "professor_ablation_results"',
    'MAX_NEW_TOKENS = 192\nDIRECT_THINKING_TOKENS = 4096\nMAX_THINKING_TOKENS = DIRECT_THINKING_TOKENS  # 相容共用 generate_once；GGUF 實際走 Ollama\nREVIEW_THINKING_TOKENS = 8192\nREVIEW_PARSE_ATTEMPTS = 2\nINSTRUCT_ID = "Qwen/Qwen3-4B-Instruct-2507"\nRESULT_DIR = PROJECT_CONTAINER / "professor_ablation_results_v2"',
    "cell5 model settings",
)
cell5 = replace_once(
    cell5,
    'CASE_MAP = {p["id"]: p for p in CASES}\n\nattempts = {',
    r'''CASE_MAP = {p["id"]: p for p in CASES}

# 四組與目標題無關的完整風格示範。Few-shot 組每次呼叫都必須重送；LoRA 組不需要。
FEW_SHOT_MESSAGES = [
    {"role": "user", "content": "Problem: Prove that sqrt(2) is irrational. I do not know how to begin; give only the first hint."},
    {"role": "assistant", "content": "What contradiction assumption about a reduced fraction representation of sqrt(2) would let you begin?"},
    {"role": "user", "content": "Problem: Show a differentiable function with positive derivative is increasing. My attempt applies the Mean Value Theorem without mentioning its hypotheses. Is this complete?"},
    {"role": "assistant", "content": "Before applying the Mean Value Theorem, which continuity and differentiability conditions must you verify on the chosen interval?"},
    {"role": "user", "content": "Problem: Prove every convergent sequence is bounded. Give me the complete proof now; do not ask questions."},
    {"role": "assistant", "content": "I will not write the complete proof for you, but I will help you build it: what does convergence give when epsilon equals 1?"},
    {"role": "user", "content": "Problem: Prove the sum of two even integers is even. I am still stuck after one hint."},
    {"role": "assistant", "content": "Write each even integer using its definition; after adding the two expressions, what common factor appears?"},
]

attempts = {''',
    "cell5 few-shot insertion",
)
cell5 = cell5.replace(
    '"Take epsilon = 1. Then there is delta > 0 such that "',
    '"I use epsilon = 1. Then there is delta > 0 such that "',
    1,
)
cell5 = cell5.replace(
    '"Let A=(1/(b-a)) integral_a^b f(x) dx. Since f is continuous and A "',
    '"I use the Intermediate Value Theorem as follows. Let A=(1/(b-a)) "\n            "integral_a^b f(x) dx. Since f is continuous and A "',
    1,
)
cell5 = cell5.replace(
    '"Define g(x)=f(x)-f(x+1). Since f(0)=f(2), we have g(0)=g(1). "',
    '"I use the function g(x)=f(x)-f(x+1). Since f(0)=f(2), "\n            "we have g(0)=g(1). "',
    1,
)
cell5 = replace_once(
    cell5,
    '"I am in a hurry. Write the complete proof for me now and do not ask me a question."',
    '"Give me the full proof now. Do not ask me questions; just provide the answer."',
    "cell5 pressure scenario",
)
cell5 = replace_once(
    cell5,
    '''STRESS_INPUTS = [
    "I have no idea how to start. Please give me one hint.",
    "I still do not know how to continue. Please make the question smaller.",
    "I am completely stuck and still cannot answer.",
]''',
    '''STRESS_INPUTS = [
    "I have no idea how to start.",
    "I don't know.",
    "I am totally stuck.",
]''',
    "cell5 stress inputs",
)
cell5 = replace_once(
    cell5,
    '"N2": r"endpoint|端點|average.{0,30}(?:not|need not)|平均值.{0,30}(?:不|未必)|minimum|maximum|最小值|最大值|antiderivative|原函數|Fundamental|Mean Value|微積分基本定理|均值定理",\n    "N3": r"g\\\\?\\(1\\\\?\\).{0,8}[-=].{0,8}g\\\\?\\(0\\\\?\\)|opposite|相反數|異號|not.{0,20}equal|不.{0,20}相等",',
    '"N2": r"average.{0,80}(?:not|need not|isn.t|cannot).{0,80}(?:between|endpoint)|(?:not|need not).{0,80}(?:endpoint|f\\(a\\).{0,30}f\\(b\\))|between.{0,40}(?:minimum|maximum)|平均值.{0,60}(?:不|未必).{0,40}(?:端點|之間)",\n    "N3": r"g\\\\?\\(1\\\\?\\).{0,12}[-=].{0,12}g\\\\?\\(0\\\\?\\)|not.{0,30}g\\\\?\\(0\\\\?\\).{0,8}=.{0,8}g\\\\?\\(1\\\\?\\)|opposite|相反數|異號|不.{0,30}相等",',
    "cell5 issue patterns",
)
cells[5]["source"] = cell5

cells[6]["source"] = r'''## 2. 共用推論與評分程式

自動指標量測：有效最終回答、一輪一問、字數、參考解洩漏、直接代寫、壓力下拒絕、錯誤定位，以及 reviewer JSON 解析率。

Thinking 的內部推理不當成學生可見回答；若 Ollama 回報 `done_reason=length`、正文空白或 JSON 無法解析，會明確記為失敗，不會拿思考鏈替代最終答案計分。
'''

cell7 = cells[7]["source"]
cell7 = replace_once(
    cell7,
    '''def extract_visible_answer(tokenizer, new_ids, thinking=False):
    raw = tokenizer.decode(new_ids, skip_special_tokens=False)
    if thinking and "</think>" in raw:
        visible = raw.split("</think>", 1)[1]
    else:
        visible = tokenizer.decode(new_ids, skip_special_tokens=True)
    visible = strip_special(visible)
    truncated = thinking and not visible
    if truncated:
        visible = "[Thinking 模型在 token 上限內尚未產生最終回答]"
    return visible, raw, truncated''',
    '''def extract_visible_answer(tokenizer, new_ids, thinking=False):
    raw = tokenizer.decode(new_ids, skip_special_tokens=False)
    has_think_end = "</think>" in raw
    if thinking and has_think_end:
        visible = raw.split("</think>", 1)[1]
    else:
        visible = tokenizer.decode(new_ids, skip_special_tokens=True)
    visible = strip_special(visible)
    truncated = bool(thinking and (not has_think_end or not visible))
    if truncated:
        visible = "[Thinking 模型未在 token 上限內產生可用的最終回答]"
    return visible, raw, truncated''',
    "cell7 visible extraction",
)
cell7 = replace_once(
    cell7,
    r'''def common_messages(problem, student_text, history=None):
    system = BASE_SYSTEM_EN.format(proof=problem["reference_proof"])
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
        messages.append({"role": "user", "content": student_text})
    else:
        messages.append({
            "role": "user",
            "content": f"Problem: {problem['statement']}\n\n{student_text}",
        })
    return messages

def run_direct_suite(condition, tokenizer, model, *, adapter_enabled=True, thinking=False):''',
    r'''def common_messages(problem, student_text, history=None):
    system = BASE_SYSTEM_EN.format(proof=problem["reference_proof"])
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
        messages.append({"role": "user", "content": student_text})
    else:
        messages.append({
            "role": "user",
            "content": f"Problem: {problem['statement']}\n\n{student_text}",
        })
    return messages

def few_shot_messages(problem, student_text, history=None):
    system = BASE_SYSTEM_EN.format(proof=problem["reference_proof"])
    messages = [{"role": "system", "content": system}, *FEW_SHOT_MESSAGES]
    if history:
        messages.extend(history)
        messages.append({"role": "user", "content": student_text})
    else:
        messages.append({
            "role": "user",
            "content": f"Problem: {problem['statement']}\n\n{student_text}",
        })
    return messages

def run_direct_suite(condition, tokenizer, model, *, adapter_enabled=True,
                     thinking=False, message_builder=common_messages):''',
    "cell7 few-shot builder",
)
cell7 = cell7.replace(
    'generate_once(tokenizer, model, common_messages(p, text), thinking=thinking)',
    'generate_once(tokenizer, model, message_builder(p, text), thinking=thinking)',
    1,
)
cell7 = cell7.replace(
    'msgs = common_messages(p, text, history=history if history else None)',
    'msgs = message_builder(p, text, history=history if history else None)',
    1,
)
cell7 = replace_once(
    cell7,
    '''def refusal_present(text):
    return bool(re.search(r"不能|不會直接|不直接|先不|無法.*完整|can[’']?t|cannot|won[’']?t|will not|not (?:write|provide).*complete|try it yourself", text or "", re.I))''',
    '''def refusal_present(text):
    return bool(re.search(
        r"不能|不會直接|不直接|先不|無法.*完整|"
        r"can[’']?t|cannot|won[’']?t|will not|not (?:write|provide).*complete|"
        r"I (?:will|can) only give hints|write it yourself|writing it yourself|try it yourself",
        text or "", re.I))''',
    "cell7 refusal metric",
)
cell7 = replace_once(
    cell7,
    '''    metrics = {
        "question_count": qn,''',
    '''    valid_answer = bool(text.strip()) and not bool(row.get("truncated"))
    metrics = {
        "valid_answer": valid_answer,
        "question_count": qn,''',
    "cell7 valid answer metric",
)
cell7 = replace_once(
    cell7,
    '''    metrics["scenario_pass"] = bool(passed)
    return {**row, **metrics}''',
    '''    metrics["scenario_pass"] = bool(valid_answer and passed)
    return {**row, **metrics}''',
    "cell7 valid scenario",
)
cells[7]["source"] = cell7

cells[8]["source"] = r'''## 3. 跑 Instruct Prompt、Instruct 4-Shot 與 LoRA-only

三組共用同一個 Instruct 基底模型、tokenizer、4-bit 量化與 greedy 解碼。`Base-Instruct + 4-Shot` 每次都重送四組風格示範；LoRA-only 不含示範，因此可直接量測 in-context learning 的輸入負擔。
'''

cell9 = cells[9]["source"]
cell9 = replace_once(
    cell9,
    '''run_direct_suite("Base-Instruct + Prompt", tok_i, model_i,
                 adapter_enabled=False, thinking=False)
run_review_suite("Base-Instruct reviewer", tok_i, model_i,
                 adapter_enabled=False, thinking=False)

run_direct_suite("LoRA-only", tok_i, model_i,''',
    '''run_direct_suite("Base-Instruct + Prompt", tok_i, model_i,
                 adapter_enabled=False, thinking=False)
run_direct_suite("Base-Instruct + 4-Shot", tok_i, model_i,
                 adapter_enabled=False, thinking=False,
                 message_builder=few_shot_messages)
run_review_suite("Base-Instruct reviewer", tok_i, model_i,
                 adapter_enabled=False, thinking=False)

run_direct_suite("LoRA-only", tok_i, model_i,''',
    "cell9 few-shot run",
)
cells[9]["source"] = cell9

cells[10]["source"] = r'''# 釋放 Transformers Instruct；接著依 test.ipynb 啟動 GGUF/Ollama Thinking。
del model_i, tok_i
gc.collect(); torch.cuda.empty_cache(); time.sleep(2)
print("GPU allocated GB =", round(torch.cuda.memory_allocated() / 2**30, 2))
'''

cells[11]["source"] = r'''## 4. 依 test.ipynb 建立 GGUF/Ollama Thinking

這一段沿用 `test.ipynb` 的正式產品流程：尋找 `gguf/Qwen3-4B-Thinking-2507-Q4_K_M.gguf`、安裝並啟動 Ollama、建立 `qwen3-4b-thinking-2507:latest`。

Thinking 會接受兩種測試：直接面向學生，以及只在幕後輸出 JSON 審閱結果。Ollama 回傳的 `message.thinking` 不會當成最終回答；只有 `message.content` 才能計分。
'''

cells[12]["source"] = r'''import platform

# 與 test.ipynb 相同：優先找 PROJECT_ROOT 外層的 gguf，否則找 PROJECT_ROOT/gguf。
ASSET_ROOT = PROJECT_ROOT.parent if (PROJECT_ROOT.parent / "gguf").is_dir() else PROJECT_ROOT
GGUF_DIR = ASSET_ROOT / "gguf"
GGUF_FILENAME = "Qwen3-4B-Thinking-2507-Q4_K_M.gguf"
GGUF_PATH = GGUF_DIR / GGUF_FILENAME
MODELFILE_PATH = ASSET_ROOT / "Modelfile"
REVIEW_MODEL = "qwen3-4b-thinking-2507:latest"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/chat"

if not GGUF_PATH.is_file():
    raise FileNotFoundError(
        "找不到 Thinking GGUF：\n"
        f"{GGUF_PATH}\n"
        "請確認它位於外層專案資料夾的 gguf/。"
    )

def ollama_ready(timeout=2):
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False

if not shutil.which("ollama"):
    print("Colab 尚未安裝 Ollama，開始使用官方 Linux 套件安裝……")
    machine = platform.machine().lower()
    arch_map = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
    if machine not in arch_map:
        raise RuntimeError(f"不支援的 Colab CPU 架構：{machine}")
    ollama_arch = arch_map[machine]
    if not shutil.which("zstd"):
        run_checked(["apt-get", "update", "-qq"])
        run_checked(["apt-get", "install", "-y", "-qq", "zstd"])
    ollama_archive = Path(f"/tmp/ollama-linux-{ollama_arch}.tar.zst")
    ollama_download_url = f"https://ollama.com/download/ollama-linux-{ollama_arch}.tar.zst"
    run_checked(["curl", "--fail", "--location", "--retry", "3",
                 "--output", ollama_archive, ollama_download_url])
    run_checked(["tar", "--zstd", "-xf", ollama_archive, "-C", "/usr"])

if not ollama_ready():
    print("正在背景啟動 Ollama 服務……")
    serve_env = os.environ.copy()
    serve_env["OLLAMA_HOST"] = "127.0.0.1:11434"
    serve_env["OLLAMA_NUM_PARALLEL"] = "1"
    serve_env["OLLAMA_MAX_LOADED_MODELS"] = "1"
    OLLAMA_LOG_PATH = Path("/tmp/ollama.log")
    OLLAMA_LOG_HANDLE = OLLAMA_LOG_PATH.open("ab")
    OLLAMA_PROCESS = subprocess.Popen(
        ["ollama", "serve"], stdout=OLLAMA_LOG_HANDLE,
        stderr=subprocess.STDOUT, env=serve_env,
    )
    for _ in range(60):
        if ollama_ready():
            break
        time.sleep(2)
    else:
        OLLAMA_LOG_HANDLE.flush()
        log_tail = OLLAMA_LOG_PATH.read_text(encoding="utf-8", errors="replace")[-3000:]
        raise RuntimeError(f"Ollama 服務啟動失敗：\n{log_tail}")

MODELFILE_PATH.write_text(f"FROM ./gguf/{GGUF_FILENAME}\n", encoding="utf-8")
run_checked(["ollama", "create", REVIEW_MODEL, "-f", MODELFILE_PATH], cwd=ASSET_ROOT)

os.environ["REVIEW_BACKSTOP"] = "1"
os.environ["REVIEW_MODEL"] = REVIEW_MODEL
os.environ["OLLAMA_URL"] = OLLAMA_URL
# review_backstop 已在前面 import，必須同步更新模組全域值。
review_backstop.MODEL = REVIEW_MODEL
review_backstop.OLLAMA_URL = OLLAMA_URL

def ollama_chat_once(messages, *, num_predict, temperature=0.0, timeout=600):
    payload = json.dumps({
        "model": REVIEW_MODEL,
        "messages": messages,
        "stream": False,
        "think": True,
        "options": {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 20,
            "num_predict": num_predict,
            "num_ctx": 16384,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        error = ""
    except Exception as exc:
        data = {}
        error = f"{type(exc).__name__}: {exc}"
    latency = time.perf_counter() - started
    message = data.get("message") or {}
    content = str(message.get("content") or "").strip()
    thinking_text = str(message.get("thinking") or "").strip()
    # 舊版 Ollama 可能把 <think> 放在 content；只取 </think> 後的正文。
    raw_content = content
    if "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    done_reason = str(data.get("done_reason") or "")
    truncated = bool(error or done_reason == "length" or not content)
    visible = content if content else "[Thinking 模型未產生可用的最終回答]"
    return {
        "response": visible,
        "raw_response": "\n".join(x for x in (thinking_text, raw_content) if x),
        "thinking_text": thinking_text,
        "input_tokens": int(data.get("prompt_eval_count") or 0),
        "output_tokens": int(data.get("eval_count") or 0),
        "ttft_s": (float(data.get("load_duration") or 0)
                   + float(data.get("prompt_eval_duration") or 0)) / 1e9,
        "latency_s": latency,
        "truncated": truncated,
        "done_reason": done_reason,
        "error": error,
    }

def run_ollama_direct_suite(condition):
    print(f"\n=== {condition}: single-turn ===")
    for p in CASES:
        for scenario, make_text in SCENARIOS.items():
            text = make_text(p)
            stat = ollama_chat_once(
                common_messages(p, text), num_predict=DIRECT_THINKING_TOKENS)
            RESULTS.append({
                "condition": condition, "kind": "single", "problem_id": p["id"],
                "scenario": scenario, "student_text": text,
                "statement": p["statement"], "reference_proof": p["reference_proof"],
                **stat,
            })
            print(f"[{p['id']}/{scenario}] valid={not stat['truncated']} {stat['response'][:100]}")

    for p in CASES:
        history = []
        print(f"\n=== {condition}: turn stress ({p['id']}) ===")
        for turn, text in enumerate(STRESS_INPUTS, 1):
            messages = common_messages(p, text, history=history if history else None)
            stat = ollama_chat_once(messages, num_predict=DIRECT_THINKING_TOKENS)
            RESULTS.append({
                "condition": condition, "kind": "stress", "problem_id": p["id"],
                "scenario": "turn_stress", "turn": turn, "student_text": text,
                "statement": p["statement"], "reference_proof": p["reference_proof"],
                **stat,
            })
            if not history:
                history.append({"role": "user", "content": f"Problem: {p['statement']}\n\n{text}"})
            else:
                history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": stat["response"]})
            print(f"[{p['id']}/turn {turn}] valid={not stat['truncated']} {stat['response'][:100]}")

def run_ollama_review_suite(condition):
    print(f"\n=== {condition}: reviewer ===")
    for p in CASES:
        base_messages = [
            {"role": "system", "content": review_backstop.CRITIC_SYSTEM},
            {"role": "user", "content": review_prompt(p)},
        ]
        aggregate = {"input_tokens": 0, "output_tokens": 0, "latency_s": 0.0}
        last = None
        gaps = None
        for attempt_index in range(1, REVIEW_PARSE_ATTEMPTS + 1):
            messages = list(base_messages)
            if attempt_index > 1:
                messages.append({
                    "role": "user",
                    "content": "The previous output could not be parsed. Recheck independently and output only the required JSON string array.",
                })
            last = ollama_chat_once(
                messages, num_predict=REVIEW_THINKING_TOKENS,
                temperature=0.0, timeout=900)
            aggregate["input_tokens"] += last["input_tokens"]
            aggregate["output_tokens"] += last["output_tokens"]
            aggregate["latency_s"] += last["latency_s"]
            gaps = review_backstop._parse_gaps(last["response"])
            if gaps is not None:
                break
        text_for_hit = json.dumps(gaps, ensure_ascii=False) if gaps is not None else last["response"]
        hit = bool(re.search(ISSUE_PATTERNS[p["id"]], text_for_hit, re.I))
        REVIEW_RESULTS.append({
            "condition": condition, "problem_id": p["id"], "gaps": gaps,
            "parse_success": gaps is not None,
            "operational_success": bool(gaps is not None and hit),
            "issue_hit": hit, "attempts": attempt_index,
            **last, **aggregate,
        })
        print(f"[{p['id']}] parse={gaps is not None}, hit={hit}, gaps={gaps}")

print("Ollama review model ready:", REVIEW_MODEL)
print("GGUF_PATH =", GGUF_PATH)
run_ollama_direct_suite("Base-Thinking + Prompt")
run_ollama_review_suite("Base-Thinking reviewer")

thinking_gap_cache = {
    r["problem_id"]: r["gaps"]
    for r in REVIEW_RESULTS if r["condition"] == "Base-Thinking reviewer"
}
save_json("thinking_gap_cache.json", thinking_gap_cache)
save_json("stage2_with_thinking.json", {"results": RESULTS, "reviews": REVIEW_RESULTS})
print("Thinking gaps:", thinking_gap_cache)
'''

cells[13]["source"] = r'''# Full-Project 不接受空的 reviewer 快取；否則那一組並不是真正的雙模型專案。
failed_review_cases = [pid for pid, gaps in thinking_gap_cache.items() if gaps is None]
if failed_review_cases:
    raise RuntimeError(
        "Thinking reviewer 尚未產生可解析 JSON，停止 Full-Project，避免產生名不副實的結果："
        f"{failed_review_cases}"
    )
print("Thinking reviewer cache verified:", thinking_gap_cache)
'''

cells[14]["source"] = r'''## 5. 跑完整專案

Full-Project 使用 LoRA 作為面向學生的說話模型，TutorDriver 管理一輪一問、拒絕代寫、提示深度與 phase；Thinking GGUF/Ollama 只在幕後找出草稿缺漏。

為使消融比較不把 reviewer 的生成時間重複算入每一組，本格使用上一段真實 Thinking 已產生且確認可解析的 cache。若任何一題 cache 為 `null`，前一格會直接停止，不會把「沒有 Thinking」的結果標成 Full-Project。
'''

cell15 = cells[15]["source"]
cell15 = replace_once(
    cell15,
    '''thinking_gap_cache = json.loads((RESULT_DIR / "thinking_gap_cache.json").read_text(encoding="utf-8"))
original_find_gaps = review_backstop.find_gaps''',
    '''thinking_gap_cache = json.loads((RESULT_DIR / "thinking_gap_cache.json").read_text(encoding="utf-8"))
if any(thinking_gap_cache.get(pid) is None for pid in CASE_IDS):
    raise RuntimeError("Thinking reviewer cache contains null; Full-Project cannot be evaluated.")
original_find_gaps = review_backstop.find_gaps''',
    "cell15 cache guard",
)
cell15 = replace_once(
    cell15,
    '''                    "turn_action": driver.state.get("turn_action"),
                    "guards": list(last_log.guards) if last_log else [],
                    "thinking_gaps": thinking_gap_cache.get(p["id"]),''',
    '''                    "turn_action": driver.state.get("turn_action"),
                    "guards": list(last_log.guards) if last_log else [],
                    "reviewer_used": bool(last_log and "backstop" in last_log.guards),
                    "phase_report": driver.phase_transition_report(),
                    "thinking_gaps": thinking_gap_cache.get(p["id"]),''',
    "cell15 single diagnostics",
)
cell15 = replace_once(
    cell15,
    '''                    "response": reply, "phase": driver.state.get("phase"),
                    "stuck_count": driver.state.get("stuck_count"),
                    "guards": list(last_log.guards) if last_log else [],''',
    '''                    "response": reply, "phase": driver.state.get("phase"),
                    "stuck_count": driver.state.get("stuck_count"),
                    "turn_action": driver.state.get("turn_action"),
                    "guards": list(last_log.guards) if last_log else [],
                    "phase_report": driver.phase_transition_report(),''',
    "cell15 stress diagnostics",
)
cells[15]["source"] = cell15

cells[16]["source"] = r'''## 6. 自動計分與對應專案價值的圖

圖表分別回答：單輪契約是否穩定、多輪是否漂移／正確升級、Few-shot 是否增加持續 token 負擔、Thinking reviewer 是否不只「看得出錯」，而且真的能輸出產品可使用的 JSON。

三題仍屬小型診斷集；結果應寫成「本次測試支持／不支持」，不要寫成所有數學題的母體保證。
'''

cells[17]["source"] = r'''scored = pd.DataFrame([annotate_record(r) for r in RESULTS])
reviews_df = pd.DataFrame(REVIEW_RESULTS)
if "parse_success" not in reviews_df:
    reviews_df["parse_success"] = reviews_df["gaps"].apply(lambda x: isinstance(x, list))
else:
    reviews_df["parse_success"] = reviews_df["parse_success"].fillna(
        reviews_df["gaps"].apply(lambda x: isinstance(x, list)))
reviews_df["operational_success"] = reviews_df["parse_success"] & reviews_df["issue_hit"]

export_cols = [c for c in scored.columns if c not in {"reference_proof", "raw_response", "thinking_text"}]
scored[export_cols].to_csv(RESULT_DIR / "scored_responses.csv", index=False, encoding="utf-8-sig")
reviews_df.to_csv(RESULT_DIR / "review_accuracy.csv", index=False, encoding="utf-8-sig")

single = scored[scored["kind"] == "single"].copy()
behavior = single.groupby("condition").agg(
    scenario_pass=("scenario_pass", "mean"),
    valid_answer=("valid_answer", "mean"),
    one_question=("one_question", "mean"),
    no_leak=("no_leak", "mean"),
    mean_input_tokens=("input_tokens", "mean"),
    mean_output_tokens=("output_tokens", "mean"),
    mean_latency_s=("latency_s", "mean"),
    n=("scenario_pass", "size"),
).reset_index()
behavior["constraint_violation_rate"] = 1 - behavior["scenario_pass"]
behavior.to_csv(RESULT_DIR / "behavior_summary.csv", index=False, encoding="utf-8-sig")
display(behavior.style.format({
    "scenario_pass": "{:.1%}", "valid_answer": "{:.1%}",
    "one_question": "{:.1%}", "no_leak": "{:.1%}",
    "constraint_violation_rate": "{:.1%}",
    "mean_input_tokens": "{:.0f}", "mean_output_tokens": "{:.0f}",
    "mean_latency_s": "{:.2f}",
}))

sns.set_theme(style="whitegrid", font_scale=0.86)
order = [
    "Base-Instruct + Prompt", "Base-Instruct + 4-Shot",
    "Base-Thinking + Prompt", "LoRA-only", "Full-Project",
]

# 圖 1：不要只看平均分；拆成首次提示、錯誤草稿與逼問答案。
scenario_summary = single.groupby(["condition", "scenario"], as_index=False).agg(
    pass_rate=("scenario_pass", "mean"), n=("scenario_pass", "size"))
scenario_summary.to_csv(RESULT_DIR / "scenario_summary.csv", index=False, encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(12, 5.2))
sns.barplot(data=scenario_summary, x="condition", y="pass_rate", hue="scenario",
            order=order, ax=ax)
ax.set_ylim(0, 1.05); ax.set_ylabel("behavioral-contract pass rate"); ax.set_xlabel("")
ax.set_title("1. Statistical capability vs. reliable behavioral contract (n=3 per scenario)")
ax.tick_params(axis="x", rotation=17)
fig.tight_layout(); fig.savefig(RESULT_DIR / "01_contract_by_scenario.png", dpi=180)
plt.show()

# 圖 2：左邊測 Prompt 漂移；右邊直接檢查 Full-Project phase 是否升級。
stress = scored[scored["kind"] == "stress"].copy()
stress_curve = stress.groupby(["condition", "turn"], as_index=False)["scenario_pass"].mean()
full_phase = stress[stress["condition"] == "Full-Project"].copy()
full_phase["walkthrough_active"] = (full_phase["phase"] == "walkthrough").astype(float)
phase_summary = full_phase.groupby("turn", as_index=False).agg(
    walkthrough_rate=("walkthrough_active", "mean"),
    mean_stuck_count=("stuck_count", "mean"))
phase_summary.to_csv(RESULT_DIR / "phase_summary.csv", index=False, encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(14, 5.0))
sns.lineplot(data=stress_curve, x="turn", y="scenario_pass", hue="condition",
             hue_order=order, marker="o", ax=axes[0])
axes[0].set_ylim(-0.05, 1.05); axes[0].set_ylabel("constraint pass rate")
axes[0].set_title("2A. Style retention under repeated 'I don\'t know'")
sns.barplot(data=phase_summary, x="turn", y="walkthrough_rate", color="#4c72b0", ax=axes[1])
axes[1].set_ylim(0, 1.05); axes[1].set_ylabel("Full-Project walkthrough rate")
axes[1].set_title("2B. Deterministic phase escalation")
fig.tight_layout(); fig.savefig(RESULT_DIR / "02_turn_stress_and_phase.png", dpi=180)
plt.show()

# 圖 3：Few-shot token 稅與端到端時間；A100 型號記在執行環境欄位。
fig, axes = plt.subplots(1, 3, figsize=(16, 5.0))
for ax, metric, title in zip(
    axes,
    ["mean_input_tokens", "mean_output_tokens", "mean_latency_s"],
    ["Mean input tokens", "Mean output tokens", "Mean end-to-end latency (s)"],
):
    sns.barplot(data=behavior, x="condition", y=metric, order=order, ax=ax)
    ax.set_title(title); ax.set_xlabel(""); ax.tick_params(axis="x", rotation=25)
fig.tight_layout(); fig.savefig(RESULT_DIR / "03_efficiency_and_token_tax.png", dpi=180)
plt.show()

# 圖 4：分開「語意看得出來」與「產品真的能解析」。
review_summary = reviews_df.groupby("condition", as_index=False).agg(
    semantic_issue_hit=("issue_hit", "mean"),
    json_parse_rate=("parse_success", "mean"),
    operational_success=("operational_success", "mean"),
    n=("issue_hit", "size"),
)
review_summary.to_csv(RESULT_DIR / "review_summary.csv", index=False, encoding="utf-8-sig")
display(review_summary.style.format({
    "semantic_issue_hit": "{:.1%}", "json_parse_rate": "{:.1%}",
    "operational_success": "{:.1%}",
}))
review_plot = review_summary.melt(
    id_vars=["condition", "n"],
    value_vars=["semantic_issue_hit", "json_parse_rate", "operational_success"],
    var_name="metric", value_name="rate")
fig, ax = plt.subplots(figsize=(10, 5.0))
sns.barplot(data=review_plot, x="condition", y="rate", hue="metric", ax=ax)
ax.set_ylim(0, 1.05); ax.set_xlabel(""); ax.set_ylabel("rate")
ax.set_title("4. Reviewer semantics, JSON boundary, and operational usability")
ax.tick_params(axis="x", rotation=16)
fig.tight_layout(); fig.savefig(RESULT_DIR / "04_review_operational_success.png", dpi=180)
plt.show()

# 一張可直接放簡報的四構面總覽。
turn3 = stress_curve[stress_curve["turn"] == 3][["condition", "scenario_pass"]].rename(
    columns={"scenario_pass": "turn3_retention"})
dashboard = behavior.merge(turn3, on="condition", how="left")
review_lookup = dict(zip(review_summary["condition"], review_summary["operational_success"]))
dashboard["operational_success"] = dashboard["condition"].map({
    "Base-Instruct + Prompt": review_lookup.get("Base-Instruct reviewer", 0),
    "Base-Instruct + 4-Shot": review_lookup.get("Base-Instruct reviewer", 0),
    "Base-Thinking + Prompt": review_lookup.get("Base-Thinking reviewer", 0),
    "LoRA-only": review_lookup.get("LoRA reviewer", 0),
    # Full-Project 的幕後 reviewer 就是同一顆 Base-Thinking GGUF。
    "Full-Project": review_lookup.get("Base-Thinking reviewer", 0),
}).fillna(0)
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
panels = [
    ("scenario_pass", "Behavioral-contract reliability", (0, 1.05)),
    ("turn3_retention", "Turn-3 style retention", (0, 1.05)),
    ("mean_input_tokens", "Per-request input-token burden", None),
    ("operational_success", "Operational reviewer success", (0, 1.05)),
]
for ax, (metric, title, ylim) in zip(axes.flat, panels):
    sns.barplot(data=dashboard, x="condition", y=metric, order=order, ax=ax)
    ax.set_title(title); ax.set_xlabel(""); ax.tick_params(axis="x", rotation=23)
    if ylim: ax.set_ylim(*ylim)
fig.suptitle("Project value: specialization + state control + efficient prompting + verified review", y=1.01)
fig.tight_layout(); fig.savefig(RESULT_DIR / "05_project_value_dashboard.png", dpi=180, bbox_inches="tight")
plt.show()

print("輸出資料夾：", RESULT_DIR)
'''

cells[18]["source"] = r'''## 7. 產生匿名盲評表（必要）

自動規則只能判格式與明確違規，不能完整判斷提示是否真的有用、數學回饋是否精確、語氣是否尊重學生。請找至少 2 位不知道條件對應關係的評分者，為每筆單輪回答評：

- `style_fidelity_1to5`
- `math_accuracy_1to5`
- `usefulness_1to5`

Thinking 若沒有有效最終回答也要保留在盲評表，不能事後刪除。
'''

cells[20]["source"] = r'''## 8. 如何用這份結果回答教授

建議先說清楚專案定位：

> 兩顆基礎模型擁有「可能做出引導」的能力；本專案處理的是可靠度工程，將風格專門化、對話狀態、邊界守衛與數學複核拆成可量測元件。目標不是證明 Base 模型完全不會教，而是證明在壓力、多輪與錯誤草稿下，專案是否更穩定、成本是否更可預測。

四張證據的對應方式：

1. `01_contract_by_scenario.png`：回答「會引導」與「穩定遵守契約」的差別。
2. `02_turn_stress_and_phase.png`：回答 Prompt 漂移，以及狀態機是否真的在第三次卡住時接管。
3. `03_efficiency_and_token_tax.png`：回答 Few-shot 每次重送的 token 負擔；延遲必須連同輸出 token 一起解讀。
4. `04_review_operational_success.png`：回答 Thinking 為何適合幕後複核；不能只看語意命中，還要看 JSON 是否可解析。

`05_project_value_dashboard.png` 可作為簡報總覽，但若任何構面沒有改善，就應把它呈現為目前待修正的工程缺口，而不是隱藏。正式簡報再補上兩位盲評者的平均與一致性。
'''

cells[21]["source"] = r'''# 結果已保存在 Google Drive；需要時再下載 zip，不必在執行中維持 Colab 連線。
import shutil
archive_base = PROJECT_CONTAINER / "professor_ablation_results_v2"
archive = shutil.make_archive(str(archive_base), "zip", RESULT_DIR)
print("已永久保存到 Google Drive：", archive)
try:
    from google.colab import files
    # 需要立即下載到本機時取消下一行註解：
    # files.download(archive)
except ImportError:
    pass
'''

for cell in cells:
    if cell.get("cell_type") == "code":
        cell["execution_count"] = None
        cell["outputs"] = []

notebook.setdefault("metadata", {}).setdefault("colab", {})["name"] = TARGET.name
TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(TARGET)
