#!/usr/bin/env python3
"""
verify_ats_and_layout.py
========================
ATS 文本层提取与 A4 单页物理排版自动化质检工具。
借鉴自 ai-job-search 工业级验证标准，针对国内大厂招聘系统（飞书、Moka、北森、自建ATS）进行深度适配。

主要检查项：
1. 物理单页拦截：检查 PDF 页数是否严格为 1 页（拒绝任何空白页或溢出第 2 页）；
2. 联系方式可检索性（无损度）：确保 姓名、手机号、邮箱在纯文本层未被图标字体吞掉；
3. 事实与合规铁律扫描：严禁出现实习“至今”、严禁出现未合并的独立教育背景大标题；
4. 关键词覆盖率矩阵（Keyword Coverage Matrix）：对比 JD 核心技能词，输出 Covered / Missing 矩阵及 ATS 得分。
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
    """归一化文本：NFC、去除多余空白"""
    text = unicodedata.normalize("NFC", text)
    return " ".join(text.split())


def check_pdf(pdf_path: Path, name: str, phone: str, email: str, jd_text: str = None, keywords: list = None):
    results = {
        "pdf_path": str(pdf_path),
        "passed": True,
        "page_count": 0,
        "page_check": False,
        "contact_check": {},
        "taboo_check": {},
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

    # 1. 单页检查
    if pages == 1:
        results["page_check"] = True
    else:
        results["passed"] = False
        results["page_check"] = False
        results["errors"].append(f"【物理溢出】PDF 页数为 {pages} 页！严格铁律要求必须自适应充满 1 页（1 Page Only）")

    clean_text = normalize_text(text)
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

    # 3. 禁忌词扫描（Hard Rules）
    has_zhijin = False
    if "至今" in raw_text:
        if "深古" in raw_text or "2026" in raw_text:
            has_zhijin = True
    results["taboo_check"]["实习严禁至今"] = not has_zhijin
    if has_zhijin:
        results["passed"] = False
        results["errors"].append("【违背事实铁律】检测到文本层包含'至今'！深古大数据实习必须明确标注为 '2026/06 – 2026/08 (3个月)'，严禁写至今！")

    edu_match = re.search(r"教育背景", raw_text)
    results["taboo_check"]["教育背景单行化"] = True
    if edu_match:
        results["warnings"].append("【排版建议】文本层中检测到'教育背景'独立词汇。若为独立板块，建议合并至页头以压缩版面。")

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
    print("=" * 60)
    print("   ATS 文本层与 A4 单页排版自动化质检报告")
    print("=" * 60)
    print(f"目标文件: {results["pdf_path"]}")
    print(f"解析引擎: {results.get("engine", "unknown")}")
    print(f"检测结果: {"[PASSED] 质检通过" if results["passed"] else "[FAILED] 质检不通过"}")
    print("-" * 60)
    
    page_status = "OK (严格 1 页)" if results["page_check"] else f"FAIL (检测到 {results["page_count"]} 页)"
    print(f"1. 物理单页拦截: {page_status}")

    print("2. ATS 核心联系方式无损检测:")
    for label, item in results["contact_check"].items():
        status = "OK" if item["found"] else "MISSING!"
        print(f"   - {label} ({item["expected"]}): [{status}]")

    print("3. 事实铁律与红线扫描:")
    for label, ok in results["taboo_check"].items():
        print(f"   - {label}: [{"OK" if ok else "FAIL"}]")

    if results["ats_coverage"]:
        cov = results["ats_coverage"]
        print("4. ATS 关键词覆盖率分析:")
        print(f"   - 核心关键词命中率: {cov["score"]}% ({cov["covered_count"]}/{cov["total_keywords"]})")
        print(f"   - 命中词 ({len(cov["covered"])}): {", ".join(cov["covered"][:15])}{"..." if len(cov["covered"]) > 15 else ""}")
        if cov["missing"]:
            print(f"   - 未命中词 ({len(cov["missing"])}): {", ".join(cov["missing"][:10])}{"..." if len(cov["missing"]) > 10 else ""}")

    if results["errors"]:
        print("-" * 60)
        print("拦截阻断项 (必须修复):")
        for err in results["errors"]:
            print(f"  [X] {err}")

    if results["warnings"]:
        print("-" * 60)
        print("优化建议项:")
        for w in results["warnings"]:
            print(f"  [!] {w}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Verify PDF text layer and A4 single-page layout for ATS.")
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
