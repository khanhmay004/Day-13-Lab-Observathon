import sys, json, re, base64, importlib.util
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = json.load(open("run_output.json", encoding="utf-8"))
sealed = d["sealed"]
print("== sealed ==")
print(" alg:", sealed.get("alg"), "| note:", sealed.get("note"))
data = sealed.get("data")
print(" data type:", type(data).__name__, "preview:", str(data)[:160])
if isinstance(data, str):
    try:
        print(" data decoded:", base64.b64decode(data)[:200])
    except Exception as e:
        print(" decode fail:", e)

s = importlib.util.spec_from_file_location("w", "solution/wrapper.py")
w = importlib.util.module_from_spec(s); s.loader.exec_module(w)
rows = {json.loads(l)["qid"]: json.loads(l) for l in open("dump.jsonl", encoding="utf-8") if l.strip()}
sub = {x["qid"]: x for x in d["results"]}


def fields(trace):
    f = dict(ns=0, found=None, instock=None, unit=None, uw=None, item=None, pct=0, stacked=False, ship=None, sw=None, sf=False, su=False)
    for st in trace or []:
        o = st.get("observation") or {}; t = st.get("tool")
        if t == "check_stock":
            f["ns"] += 1; f.update(found=o.get("found"), instock=o.get("in_stock"), unit=o.get("unit_price_vnd"), uw=o.get("weight_kg"), item=o.get("item"))
        elif t == "get_discount":
            f["stacked"] = bool(o.get("_stacked")); f["pct"] = (o.get("percent") or 0) if o.get("valid") is not False else 0
        elif t == "calc_shipping":
            err = str(o.get("error") or "").lower(); c = o.get("cost_vnd")
            if "not_served" in err: f["sf"] = True
            elif err or c is None: f["su"] = True
            else: f["ship"] = int(c); f["sw"] = o.get("weight_kg")
    return f


def subtot(a):
    m = re.search(r"tong\s*cong:\s*([\d.,]+)", a or "", re.I)
    return int(re.sub(r"[.,]", "", m.group(1))) if m else None


stacked_n = ship_mismatch = 0
recs = []
for qid, tr in sorted(rows.items()):
    f = fields(tr["trace"])
    if f["ns"] != 1 or f["found"] is False or f["instock"] is False or f["sf"]:
        continue
    qty = w._order_qty(tr["q"], f["uw"], f["sw"])
    pct, ship = f["pct"], (f["ship"] or 0)
    base = pct // 2 if f["stacked"] else pct
    sub_w = f["unit"] * qty
    v0 = sub_w * (100 - pct) // 100 + ship                              # current (additive stacked)
    v2 = sub_w * (100 - base) // 100 + ship                             # base coupon only
    v1 = sub_w * (100 - base) // 100 * (100 - base) // 100 + ship       # multiplicative
    if f["stacked"]:
        stacked_n += 1
    exp_w = round((f["uw"] or 0) * qty, 3)
    if f["sw"] is not None and abs(f["sw"] - exp_w) > 0.01:
        ship_mismatch += 1
    recs.append((qid, f["item"], qty, pct, int(f["stacked"]), ship, f["sw"], exp_w, v0, v1, v2, subtot(sub.get(qid, {}).get("answer"))))

print("\nstacked orders:", stacked_n, "| shipping-weight mismatches:", ship_mismatch, "| total computable:", len(recs))
# agreement of each variant vs submission
for name, idx in [("v0", 8), ("v1", 9), ("v2", 10)]:
    ag = sum(1 for r in recs if r[idx] == r[11])
    print("  %s == submission: %d/%d" % (name, ag, len(recs)))
print("\nqid       item     qty pct stk ship    sw   expW    v0(add)    v1(mult)   v2(base)   submission")
for r in recs:
    print("  %-9s %-7s %d  %2d  %d %6s %5s %6s  %10d %10d %10d  %s" % r)
