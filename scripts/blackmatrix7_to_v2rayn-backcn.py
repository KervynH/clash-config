#!/usr/bin/env python3
"""blackmatrix7 Clash 文本规则 → v2rayN 路由规则组 JSON（回国分流）。

生成物名字由脚本文件名去掉 blackmatrix7_to_ 前缀得到：
    scripts/blackmatrix7_to_v2rayn-backcn.py  ->  v2rayn-backcn.json

要再出一份别的 v2rayN 配置，把本文件复制一份改名，改下面的清单即可。
"""
import json, sys, urllib.request, pathlib

# ────────────── 改这里 ──────────────

# 走代理（回国节点）的 blackmatrix7 规则集，名字取自
# https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Clash
# 共 679 个可选，前面加 # 即注释掉
RULESETS = [
    "iQIYI",
    "TencentVideo",
    "Youku",
    "BiliBili",
    "HunanTV",
    "Sohu",
    "PPTV",
    "LeTV",
    "ChinaMobile",
    "NetEaseMusic",
    "KugouKuwo",
    "AcFun",
    "HuaShuTV",
    "BesTV",
    "SMG",
    "Funshion",
    "KuKeMusic",
    "TaiheMusic",
    "IPTVMainland",
    "ChinaMedia",
    # "Migu",
    # "XiaMiMusic",
]

# 规则集之外额外追加的，语法同 Xray：domain: / full: / keyword: / regexp:
EXTRA_DOMAIN = [
    "domain:ip111.cn",
    "domain:ottcn.com",
    "domain:speedtest.cn",
]
EXTRA_IP = []

PROXY_TAG = "proxy"      # 命中上面这些走什么出站
FINAL_TAG = "direct"     # 兜底：其余全部直连；设成 None 则不生成兜底规则
DIRECT_PRIVATE = True    # 首条规则：内网地址直连
REMARKS = "国内流媒体 → 回国节点"

# ────────────── 以下一般不用动 ──────────────

RAW = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/{0}/{0}.yaml"
PREFIX = "blackmatrix7_to_"

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                    # 仓库根目录，生成物落在这里
OUT = ROOT / (pathlib.Path(__file__).stem[len(PREFIX):] + ".json")

def fetch(name):
    req = urllib.request.Request(RAW.format(name), headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")

def parse(text, dom, ip, skipped):
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        parts = [x.strip() for x in line[2:].split(",")]
        t, v = parts[0], parts[1]
        if t == "DOMAIN":
            dom.add("full:" + v)
        elif t == "DOMAIN-SUFFIX":
            dom.add("domain:" + v)
        elif t == "DOMAIN-KEYWORD":
            dom.add("keyword:" + v)
        elif t == "DOMAIN-REGEX":
            dom.add("regexp:" + ",".join(parts[1:]).replace(",", "<COMMA>"))
        elif t in ("IP-CIDR", "IP-CIDR6"):
            ip.add(v)
        else:
            skipped[t] = skipped.get(t, 0) + 1

def prune(dom):
    """丢掉已被 domain: 后缀覆盖的 full: 条目"""
    suf = {d[7:] for d in dom if d.startswith("domain:")}
    def covered(h):
        p = h.split(".")
        return any(".".join(p[i:]) in suf for i in range(len(p)))
    return {d for d in dom if not (d.startswith("full:") and covered(d[5:]))}

def sort_key(d):
    k, v = d.split(":", 1)
    return (k, v)

def main():
    dom, ip, skipped = set(), set(), {}
    for name in RULESETS:
        parse(fetch(name), dom, ip, skipped)
    dom |= set(EXTRA_DOMAIN)
    ip |= set(EXTRA_IP)
    dom = prune(dom)

    rules = []
    if DIRECT_PRIVATE:
        rules.append({"outboundTag": "direct", "ip": ["geoip:private"],
                      "enabled": True, "remarks": "内网直连"})
    item = {"outboundTag": PROXY_TAG, "enabled": True, "remarks": REMARKS}
    if dom:
        item["domain"] = sorted(dom, key=sort_key)
    if ip:
        item["ip"] = sorted(ip)
    rules.append(item)
    if FINAL_TAG:
        rules.append({"outboundTag": FINAL_TAG, "port": "0-65535",
                      "enabled": True, "remarks": "兜底 (final)"})

    OUT.write_text(json.dumps(rules, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT.name}: {len(RULESETS)} rulesets -> {len(dom)} domain, {len(ip)} ip",
          file=sys.stderr)
    if skipped:
        print(f"未映射的规则类型（已忽略）: {skipped}", file=sys.stderr)

if __name__ == "__main__":
    main()