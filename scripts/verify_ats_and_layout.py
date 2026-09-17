#!/usr/bin/env python3
"""
verify_ats_and_layout.py
========================
ATS 文本层提取与 A4 单页物理排版自动化质检工具 (v2.1 工业级防伪增强版)。
深度集成候选人【刘仁晓君】事实真理源（SSOT）机器级断言与黑名单扫描：
1. 物理单页拦截：严格 1 页 A4，严禁任何溢出；
2. 联系方式无损存活：姓名、手机号、邮箱 100% 可检索，抗特殊图标吞字；
3. 六大事实造假与排版死穴机器级硬拦截：
   - 严禁实习“至今”
   - 严禁“连续三年”奖学金
   - 严禁凭空捏造任何竞赛（蓝桥杯、ACM、数学建模等）
   - 严禁虚标英语六级或听说流利（锁死 CET-4 仅技术文档阅读）
   - 严禁设立“核心特质/自我评价”等空洞板块
   - 严禁栏目标题中英夹杂/冗余英文单词
4. ATS 关键词覆盖率矩阵计算（Covered / Synonym / Missing）。
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path


def extract_pdf_text_and_pages(pdf_path: Path):
    # 1. 尝试 pymupdf
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        pages = len(doc)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text, pages, "pymupdf"
    except ImportError:
        pass
    except Exception as e:
        sys.stderr.write(f"[WARN] pymupdf failed: {e}\n")

    # 2. 尝试 pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages = len(reader.pages)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text, pages, "pypdf"
    except ImportError:
        pass
    except Exception as e:
        sys.stderr.write(f"[WARN] pypdf failed: {e}\n")

    # 3. 尝试 pdftotext
    import subprocess
    try:
        info_out = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True).stdout
        match = re.search(r"^Pages:\s+(\d+)\s*$", info_out, re.MULTILINE)
        pages = int(match.group(1)) if match else 1
        text = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout
        return text, pages, "pdftotext"
    except Exception:
        pass

    raise RuntimeError("无法提取 PDF 文本层：请确保已安装 pymupdf (pip install pymupdf) 或 pypdf")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return " ".join(text.split())


def check_pdf(pdf_path: Path, name: str, phone: str, email: str, jd_text: str = None, keywords: list = None, html_path: Path = None):
    results = {
        "pdf_path": str(pdf_path),
        "passed": True,
        "page_count": 0,
        "page_check": False,
        "contact_check": {},
        "truth_blacklist_check": {},
        "ats_coverage": None,
        "errors": [],
        "warnings": []
    }

    if not pdf_path.exists():
        results["passed"] = False
        results["errors"].append(f"文件不存在: {pdf_path}")
        return results

    text, pages, engine = extract_pdf_text_and_pages(pdf_path)
    results["page_count"] = pages
    results["engine"] = engine

    # 1. 物理单页检查
    if pages == 1:
        results["page_check"] = True
    else:
        results["passed"] = False
        results["page_check"] = False
        results["errors"].append(f"【物理溢出】PDF 页数为 {pages} 页！铁律要求严格自适应充满 1 页（1 Page Only）")

    raw_text = text

    # 2. 基础联系方式无损可检索性
    contact_items = {
        "姓名": name,
        "手机号": phone,
        "邮箱": email
    }
    for label, val in contact_items.items():
        compact_val = re.sub(r"[\s\-_]", "", val)
        compact_text = re.sub(r"[\s\-_]", "", raw_text)
        found = (val in raw_text) or (compact_val in compact_text)
        results["contact_check"][label] = {
            "expected": val,
            "found": found
        }
        if not found:
            results["passed"] = False
            results["errors"].append(f"【ATS关键信息丢失】文本层中未检测到完整的{label}: '{val}'（可能被特殊图标吞掉或格式混淆）")

    # 3. 候选人事实真理源（SSOT）与黑名单硬阻断校验 (Truth & Blacklist Assertions)
    
    # 3.1 严禁实习“至今”
    has_zhijin = False
    if "至今" in raw_text and ("深古" in raw_text or "2026" in raw_text):
        has_zhijin = True
    results["truth_blacklist_check"]["实习严禁至今"] = not has_zhijin
    if has_zhijin:
        results["passed"] = False
        results["errors"].append("【违背事实铁律】检测到文本层包含'至今'！深古大数据实习必须明确标注为 '2026/06 – 2026/08 (3个月)'，严禁写至今！")

    # 3.2 严禁“连续三年”奖学金虚标
    has_three_years = bool(re.search(r"连续三年|三年连续|每学年均获", raw_text))
    results["truth_blacklist_check"]["严禁连续三年奖学金"] = not has_three_years
    if has_three_years:
        results["passed"] = False
        results["errors"].append("【违背事实铁律】检测到'连续三年'奖学金表述！候选人2027届大二在读，严禁虚构连续三年，仅允许表述为'获得校级学业综合奖学金(前10%)'！")

    # 3.3 绝对禁止凭空捏造竞赛荣誉
    fake_contests = ["蓝桥杯", "数学建模", "互联网+", "挑战杯", "ACM", "程序设计竞赛", "程序设计大赛", "创新创业大赛", "软件创新大赛"]
    found_contests = [c for c in fake_contests if c in raw_text]
    results["truth_blacklist_check"]["绝对禁止捏造竞赛"] = (len(found_contests) == 0)
    if found_contests:
        results["passed"] = False
        results["errors"].append(f"【严重学术造假拦截】检测到虚构竞赛荣誉: {found_contests}！候选人知识库完全无任何竞赛获奖记录，严禁无中生有！")

    # 3.4 绝对禁止虚标英语水平（听说流利、英语六级）
    fake_english = ["英语六级", "CET-6", "CET6", "口语流利", "听说流利", "英语听说熟练", "商务英语", "流利沟通"]
    found_english = [e for e in fake_english if e in raw_text]
    results["truth_blacklist_check"]["严禁夸大英语水平"] = (len(found_english) == 0)
    if found_english:
        results["passed"] = False
        results["errors"].append(f"【英语能力虚标拦截】检测到夸大英语表述: {found_english}！候选人真实英语为 CET-4（仅技术文档/论文阅读），严禁夸大！")

    # 3.5 绝对禁止设立“核心特质/自我评价”自嗨板块
    banned_sections = ["核心特质", "自我评价", "自我介绍", "中医药+计算机复合"]
    found_sections = [s for s in banned_sections if s in raw_text]
    results["truth_blacklist_check"]["严禁主观自嗨板块"] = (len(found_sections) == 0)
    if found_sections:
        results["passed"] = False
        results["errors"].append(f"【排版规范拦截】检测到禁用自嗨模块/标签: {found_sections}！技术简历严禁放置空洞自吹自擂板块！")

    # 3.6 栏目标题中英夹杂检测
    has_english_titles = False
    for match in re.finditer(r"(?:PROJECTS?|SKILLS?|EDUCATION|WORK EXPERIENCE)", raw_text, re.IGNORECASE):
        has_english_titles = True
        break
    results["truth_blacklist_check"]["栏目标题纯中文"] = not has_english_titles
    if has_english_titles:
        results["passed"] = False
        results["errors"].append("【排版油腻感拦截】检测到栏目标题包含冗余英文单词（如 PROJECTS/SKILLS/EDUCATION）！国内大厂严禁中英拼凑，必须全中文纯粹标题！")

    # 3.7 独立教育背景排版告警
    edu_match = re.search(r"教育背景", raw_text)
    if edu_match:
        results["warnings"].append("【排版建议】文本层中检测到教育背景独立词汇。若为独立板块，必须单行合并至页头下方以压缩版面。")

    # 4. 关键词覆盖率矩阵
    kw_list = []
    if keywords:
        kw_list.extend(keywords)
    elif jd_text:
        pattern = r"[A-Za-z0-9+#\.\-]+(?:[\s][A-Za-z0-9+#\.\-]+)*|微服务|高并发|原子锁|双向通信|流式|状态机|知识库|多智能体"
        candidates = re.findall(pattern, jd_text)
        filter_words = {"and", "or", "in", "to", "for", "with", "the", "a", "an", "of", "is", "we", "you", "be"}
        kw_set = set()
        for c in candidates:
            c = c.strip()
            if len(c) > 1 and c.lower() not in filter_words and not c.isdigit():
                kw_set.add(c)
        kw_list = sorted(list(kw_set))

    if kw_list:
        covered = []
        missing = []
        for kw in kw_list:
            if re.search(r"\b" + re.escape(kw) + r"\b", raw_text, re.IGNORECASE) or kw in raw_text:
                covered.append(kw)
            else:
                missing.append(kw)
        
        score = round((len(covered) / len(kw_list)) * 100, 1) if kw_list else 100.0
        results["ats_coverage"] = {
            "total_keywords": len(kw_list),
            "covered_count": len(covered),
            "missing_count": len(missing),
            "score": score,
            "covered": covered,
            "missing": missing
        }

    return results


def print_report(results: dict):
    print("=" * 65)
    print("   ATS 文本层与 A4 单页排版自动化质检报告 (v2.1 防伪增强版)")
    print("=" * 65)
    print(f"目标文件: {results["pdf_path"]}")
    print(f"解析引擎: {results.get("engine", "unknown")}")
    print(f"检测结果: {"[PASSED] 质检通过" if results["passed"] else "[FAILED] 质检不通过 (触发硬阻断)"}")
    print("-" * 65)
    
    page_status = "OK (严格 1 页)" if results["page_check"] else f"FAIL (检测到 {results["page_count"]} 页)"
    print(f"1. 物理单页拦截: {page_status}")

    print("2. ATS 核心联系方式无损检测:")
    for label, item in results["contact_check"].items():
        status = "OK" if item["found"] else "MISSING!"
        print(f"   - {label} ({item["expected"]}): [{status}]")

    print("3. 候选人事实真理源与防伪黑名单断言 (SSOT Assertions):")
    for label, ok in results["truth_blacklist_check"].items():
        print(f"   - {label}: [{"OK" if ok else "FAIL (违规)"}]")

    if results["ats_coverage"]:
        cov = results["ats_coverage"]
        print("4. ATS 关键词覆盖率分析:")
        print(f"   - 核心关键词命中率: {cov["score"]}% ({cov["covered_count"]}/{cov["total_keywords"]})")
        print(f"   - 命中词 ({len(cov["covered"])}): {", ".join(cov["covered"][:15])}{"..." if len(cov["covered"]) > 15 else ""}")
        if cov["missing"]:
            print(f"   - 未命中词 ({len(cov["missing"])}): {", ".join(cov["missing"][:10])}{"..." if len(cov["missing"]) > 10 else ""}")

    if results["errors"]:
        print("-" * 65)
        print("🛑 拦截阻断项 (代码级强制打回，必须彻底修复):")
        for err in results["errors"]:
            print(f"  [X] {err}")

    if results["warnings"]:
        print("-" * 65)
        print("⚠️ 优化建议项:")
        for w in results["warnings"]:
            print(f"  [!] {w}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Verify PDF text layer and layout for ATS with strict SSOT truth checks.")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--name", default="刘仁晓君", help="Expected candidate name")
    parser.add_argument("--phone", default="19330633407", help="Expected phone number")
    parser.add_argument("--email", default="1120835055@qq.com", help="Expected email")
    parser.add_argument("--jd-file", help="Path to JD markdown or text file")
    parser.add_argument("--keywords", nargs="*", help="List of keywords to check")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()

    jd_text = None
    if args.jd_file:
        jd_p = Path(args.jd_file).expanduser().resolve()
        if jd_p.exists():
            jd_text = jd_p.read_text(encoding="utf-8", errors="ignore")

    results = check_pdf(
        pdf_path=pdf_path,
        name=args.name,
        phone=args.phone,
        email=args.email,
        jd_text=jd_text,
        keywords=args.keywords
    )

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results)

    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
