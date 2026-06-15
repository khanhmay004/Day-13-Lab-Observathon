import json
import importlib.util
import os

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("w", os.path.join(_here, "wrapper.py"))
w = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w)


def mitigate(call_next, question, config, context):
    conf = dict(config)
    conf["system_prompt"] = w._BASE_PROMPT + (w._INJECTION_GUARD if w._looks_injected(question) else "")
    r = call_next(question, conf)
    try:
        with open("dump.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"qid": context.get("qid"), "q": question,
                                "answer": r.get("answer"), "trace": r.get("trace")},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass
    return r
