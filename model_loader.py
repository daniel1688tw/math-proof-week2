from dataclasses import dataclass
from typing import Any

from config import (
    LOAD_HF_MODEL, MODEL_NAME, USE_4BIT_IF_AVAILABLE,
    MAX_NEW_TOKENS, MIN_NEW_TOKENS, TEMPERATURE,
)

try:
    import torch
except Exception as exc:
    torch = None
    print("Torch import failed:", repr(exc))

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
except Exception as exc:
    AutoModelForCausalLM = None
    AutoTokenizer = None
    BitsAndBytesConfig = None
    print("Transformers import failed:", repr(exc))


@dataclass
class LLMBackend:
    backend: str
    model_name: str
    tokenizer: Any = None
    model: Any = None
    error: str | None = None

    def generate(self, prompt, max_new_tokens=MAX_NEW_TOKENS, json_prefix=False):
        if self.backend != "hf":
            raise RuntimeError(f"ACTIVE_LLM backend is {self.backend}, not a real HF model: {self.error}")
        messages = [
            {"role": "system", "content": "You output ONLY valid JSON. No explanations, no markdown, no text outside the JSON object."},
            {"role": "user", "content": prompt},
        ]
        if hasattr(self.tokenizer, "apply_chat_template"):
            input_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            input_text = prompt
        if json_prefix:
            input_text = input_text + "{"

        inputs = self.tokenizer(input_text, return_tensors="pt")
        prompt_len = inputs["input_ids"].shape[-1]
        model_max_len = getattr(self.model.config, "max_position_embeddings", 4096)
        available = model_max_len - prompt_len
        print(f"  [generate] prompt_tokens={prompt_len}, model_max={model_max_len}, available={available}")

        if available < MIN_NEW_TOKENS:
            raise RuntimeError(
                f"prompt_too_long: prompt uses {prompt_len} tokens, only {available} tokens available "
                f"(need at least {MIN_NEW_TOKENS}). Retry with a shorter prompt."
            )
        actual_max_new_tokens = min(max_new_tokens, available)

        device = next(self.model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=actual_max_new_tokens,
                do_sample=TEMPERATURE > 0,
                temperature=TEMPERATURE if TEMPERATURE > 0 else None,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        new_tokens = output_ids[0][inputs["input_ids"].shape[-1]:]
        decoded = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return ("{" + decoded) if json_prefix else decoded


def can_use_cuda():
    return torch is not None and torch.cuda.is_available()


def load_small_model():
    if not LOAD_HF_MODEL:
        return LLMBackend(backend="fallback", model_name="deterministic_fallback", error="LOAD_HF_MODEL=False")
    if AutoTokenizer is None or AutoModelForCausalLM is None or torch is None:
        return LLMBackend(backend="fallback", model_name="deterministic_fallback", error="transformers or torch unavailable")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        kwargs = {"trust_remote_code": True}
        if can_use_cuda():
            if USE_4BIT_IF_AVAILABLE and BitsAndBytesConfig is not None:
                try:
                    # device_map={"":0} forces all layers onto GPU 0; "auto" may
                    # dispatch layers to CPU which bitsandbytes 4-bit does not support.
                    kwargs["device_map"] = {"": 0}
                    kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_use_double_quant=True,
                    )
                except Exception:
                    kwargs["device_map"] = "auto"
                    kwargs["torch_dtype"] = torch.float16
            else:
                kwargs["device_map"] = "auto"
                kwargs["torch_dtype"] = torch.float16
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, **kwargs)
        model.eval()
        return LLMBackend(backend="hf", model_name=MODEL_NAME, tokenizer=tokenizer, model=model)
    except Exception as exc:
        return LLMBackend(backend="fallback", model_name="deterministic_fallback", error=repr(exc))


ACTIVE_LLM = load_small_model()
print("ACTIVE_LLM.backend:", ACTIVE_LLM.backend)
print("ACTIVE_LLM.model_name:", ACTIVE_LLM.model_name)
print("ACTIVE_LLM.error:", ACTIVE_LLM.error)
