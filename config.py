from pathlib import Path

MODEL_NAME = "Qwen/Qwen2.5-Math-7B-Instruct"
LOAD_HF_MODEL = True
USE_4BIT_IF_AVAILABLE = True
REQUIRE_HF_MODEL_FOR_TESTS = True
MAX_NEW_TOKENS = 2000
MIN_NEW_TOKENS = 100
TEMPERATURE = 0.1
MAX_REPAIR_ATTEMPTS = 3
ARTIFACT_DIR = Path("week2_outputs")
ARTIFACT_DIR.mkdir(exist_ok=True)

SOURCE_NODE_TYPES = {
    "assumption",
    "allowed_reference",
    "side_condition",   # definitional/notational — e.g. "let u = x^2"; no proof needed
}

VAGUE_TERMS = ["obvious", "clearly", "some theorem", "顯然", "容易看出"]
