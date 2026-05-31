import ast
import json
import re

from jsonschema import Draft202012Validator

# Full-width Unicode characters that Qwen2.5 sometimes emits instead of ASCII punctuation.
_FULLWIDTH_MAP = str.maketrans({
    '，': ',', '。': '.', '：': ':', '；': ';',
    '（': '(', '）': ')',
    '｛': '{', '｝': '}',
    '「': '"', '」': '"',
    '、': ',',  # ideographic comma
})


def _normalize_fullwidth(text: str) -> str:
    """Replace full-width/CJK punctuation with ASCII equivalents."""
    return text.translate(_FULLWIDTH_MAP)


def normalize_json_keys(d):
    if isinstance(d, dict):
        return {k.strip().lower().replace(' ', '_').replace('-', '_'): normalize_json_keys(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [normalize_json_keys(item) for item in d]
    return d


def _scan_depth(text, start):
    """Walk text from `start` tracking JSON object depth.
    Returns (end_index, 0) when the outer `{` is closed, else (last_index, depth)."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_string:
            if ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i, 0
    return len(text) - 1, depth


def _auto_close(text, start):
    """Append missing closing chars so a truncated JSON string becomes parseable."""
    stack = []
    in_string = False
    escape = False
    for ch in text[start:]:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_string:
            if ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]") and stack and stack[-1] == ch:
            stack.pop()
    suffix = '"' if in_string else ""
    suffix += "".join(reversed(stack))
    return text[start:] + suffix


def _strip_trailing_commas(text):
    """Remove trailing commas before `}` or `]` — common truncation artifact."""
    result = text
    prev = None
    while prev != result:
        prev = result
        result = re.sub(r',(\s*[}\]])', r'\1', result)
    return result


def _find_best_complete_json(text):
    """Return the first `{...}` block in `text` that is balanced AND parses as JSON."""
    pos = 0
    while pos < len(text):
        s = text.find('{', pos)
        if s < 0:
            break
        end, depth = _scan_depth(text, s)
        if depth == 0:
            candidate = text[s:end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass
        pos = s + 1
    return None


def _try_parse_closed(closed):
    """Apply heuristic repairs to auto-closed JSON; return first parseable variant or None."""
    base = _strip_trailing_commas(closed)
    variants = [
        closed,
        base,
        re.sub(r',\s*"[^"]*"\s*:\s*([}\]])', r'\1', base),
        re.sub(r',\s*"[^"]*"\s*([}\]])', r'\1', base),
    ]
    for v in variants:
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            pass
    return None


def _fix_unclosed_simple_strings(text):
    """Fix "word) → "word") — model omits closing quote before ) for simple word-like values.
    Also handles leading spaces and apostrophes, e.g. " Rolle's Theorem).
    """
    # Allow optional leading whitespace, a required word-start, then word chars / spaces / apostrophes.
    return re.sub(r'"(\s*\w[\w\s\']*)\)', r'"\1")', text)


def _fix_quoted_object_start(text):
    """Fix "{key" → {"key — model sometimes prepends a quote before an object-opening brace.
    Only matches when a letter/underscore follows optional whitespace after "{".
    """
    return re.sub(r'"\{(\s*)([a-zA-Z_])', r'{\1"\2', text)


def _fix_unclosed_strings_with_parens(text):
    """Fix unclosed string values that end with ) used as object-closer.
    Uses paren-depth counting: a ) with no matching ( in the current string
    is structural (closes the object/array), not part of the string value.
    This correctly handles math like "Eq(f(c), N)" — all ) there have matching (.
    """
    result = []
    in_string = False
    escape = False
    paren_depth = 0  # ( ) balance inside current string
    i = 0
    while i < len(text):
        ch = text[i]
        if escape:
            escape = False
            result.append(ch)
            i += 1
            continue
        if ch == '\\' and in_string:
            escape = True
            result.append(ch)
            i += 1
            continue
        if ch == '"':
            if not in_string:
                in_string = True
                paren_depth = 0
            else:
                in_string = False
                paren_depth = 0
            result.append(ch)
            i += 1
            continue
        if in_string:
            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                if paren_depth > 0:
                    # Matched ( inside string — keep in string
                    paren_depth -= 1
                else:
                    # No matching ( → structural closer, insert " to close string
                    result.append('"')
                    result.append(')')
                    in_string = False
                    paren_depth = 0
                    i += 1
                    continue
        result.append(ch)
        i += 1
    return ''.join(result)


def _fix_close_parens(text):
    """Replace ) outside JSON strings with the appropriate closer based on context stack.
    Qwen2.5-Math uses ) as object closer (→ }) and as spurious separator after array items (→ ]).
    """
    result = []
    in_string = False
    escape = False
    stack = []  # '{' for object context, '[' for array context
    for ch in text:
        if escape:
            escape = False
            result.append(ch)
            continue
        if ch == '\\' and in_string:
            escape = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
        elif not in_string:
            if ch == '{':
                stack.append('{')
                result.append(ch)
            elif ch == '[':
                stack.append('[')
                result.append(ch)
            elif ch == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
                    result.append(ch)
                # else: drop spurious } with no matching {
            elif ch == ']':
                if stack and stack[-1] == '[':
                    stack.pop()
                    result.append(ch)
                # else: drop spurious ] with no matching [
            elif ch == ')':
                if stack and stack[-1] == '{':
                    result.append('}')
                    stack.pop()
                elif stack and stack[-1] == '[':
                    result.append(']')
                    stack.pop()
                # else drop (spurious ) with no context)
            else:
                result.append(ch)
        else:
            result.append(ch)
    return ''.join(result)


def _fix_invalid_json_escapes(text):
    # JSON allows: \" \\ \/ \b \f \n \r \t \u (+ 4 hex digits)
    # LaTeX outputs \( \) \[ \] \{ \} \frac etc. which are invalid JSON escapes.
    # Drop the backslash before any char not in the valid-escape set.
    return re.sub(r'\\([^"\\\/bfnrtu])', r'\1', text)


def extract_json_object(text):
    if not isinstance(text, str):
        raise ValueError("model output is not a string")
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_+-]*", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    # Normalize full-width Unicode punctuation before any structural parsing.
    # Qwen2.5-Math sometimes emits ）、， etc. as JSON structural characters.
    text = _normalize_fullwidth(text)
    if text.find("{") < 0:
        raise ValueError("no JSON object start found")

    text = _fix_invalid_json_escapes(text)
    text = _fix_quoted_object_start(text)
    text = _fix_unclosed_strings_with_parens(text)
    text = _fix_unclosed_simple_strings(text)
    text = _fix_close_parens(text)
    complete = _find_best_complete_json(text)
    if complete:
        return complete

    pos = 0
    while pos < len(text):
        s = text.find('{', pos)
        if s < 0:
            break
        repaired = _try_parse_closed(_auto_close(text, s))
        if repaired:
            return repaired
        pos = s + 1

    raise ValueError("no complete JSON object found")


def parse_json_from_text(text):
    extracted = extract_json_object(text)
    try:
        return normalize_json_keys(json.loads(extracted))
    except json.JSONDecodeError:
        pass
    try:
        val = ast.literal_eval(extracted)
        if isinstance(val, dict):
            return normalize_json_keys(json.loads(json.dumps(val, ensure_ascii=False)))
    except Exception:
        pass
    try:
        fixed = extracted
        fixed = re.sub(r'True', 'true', fixed)
        fixed = re.sub(r'False', 'false', fixed)
        fixed = re.sub(r'None', 'null', fixed)
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        return normalize_json_keys(json.loads(fixed))
    except Exception:
        pass
    raise ValueError(f"Cannot parse JSON from model output: {extracted[:300]!r}")


def schema_errors(data, schema):
    return [f"{chr(39).join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in Draft202012Validator(schema).iter_errors(data)]


def validate_or_raise(name, data, schema):
    errs = schema_errors(data, schema)
    if errs:
        raise ValueError(f"{name} schema errors: " + "; ".join(errs[:5]))
    return data


def compact_json(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    _TESTS = [
        ("complete JSON", '{"a": 1, "b": "hello"}', {"a": 1, "b": "hello"}),
        ("JSON with preamble text", 'Here is the answer:\n{"a": 1}', {"a": 1}),
        ("prepended-{ + thinking text + real JSON", '{\nLet me think...\n{"problem_id": "p1", "raw_problem": "test"}', {"problem_id": "p1", "raw_problem": "test"}),
        ("truncated JSON — trailing comma before value", '{"a": 1, "b": ', {"a": 1}),
        ("truncated JSON — inside key name", '{"a": 1, "ke', {"a": 1}),
        ("truncated JSON — key with no value", '{"a": 1, "b": }', {"a": 1}),
        ("code block JSON", '```json\n{"a": 1}\n```', {"a": 1}),
        ("double-brace: outer-{ wrapping thinking + inner complete JSON", '{Some text {"x": 42}}', {"x": 42}),
    ]
    _ok = _bad = 0
    print("─" * 55)
    for name, inp, expected in _TESTS:
        try:
            got = json.loads(extract_json_object(inp))
            if got == expected:
                print(f"  PASS  {name}")
                _ok += 1
            else:
                print(f"  FAIL  {name}\n        expected {expected}\n        got      {got}")
                _bad += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e!r}")
            _bad += 1
    print("─" * 55)
    print(f"  extract_json_object: {_ok} pass, {_bad} fail")
    print("─" * 55)
