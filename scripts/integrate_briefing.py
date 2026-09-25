#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高顿升学 · 简报集成工具
将生成的 briefing_YYYY-MM-DD.html 自动集成到 index.html 中。

用法:
    python3 scripts/integrate_briefing.py --date 2026-09-22
"""

import argparse
import os
import re
import sys
from datetime import date, datetime

# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INDEX_FILE = os.path.join(BASE_DIR, "index.html")
FIRST_ISSUE_DATE = date(2026, 8, 17)  # 第1期

# 报告容器的样式模板（与 index.html 中现有容器保持一致）
REPORT_CONTAINER_STYLE = (
    'max-width:900px!important;margin:0 auto!important;'
    'padding:40px 32px 60px!important;background:#fff;'
    'border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.08)'
)


def error_exit(msg):
    """打印错误信息并退出"""
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def calc_issue_number(target_date):
    """计算期数: (目标日期 - 2026-08-17).days + 1"""
    delta = (target_date - FIRST_ISSUE_DATE).days
    if delta < 0:
        error_exit(f"日期 {target_date} 早于第一期 ({FIRST_ISSUE_DATE})")
    return delta + 1


def extract_report_container(briefing_html):
    """
    从简报 HTML 中提取报告容器部分。
    从 <div class="container report-view 开始，通过 div 嵌套计数找到对应的闭合标签。
    返回完整的容器 HTML 字符串。
    """
    # 查找容器起始位置
    pattern = re.compile(r'<div\s+class="container\s+report-view')
    match = pattern.search(briefing_html)
    if not match:
        return None

    start = match.start()
    # 从起始位置开始，通过 div 嵌套计数找到匹配的闭合标签
    depth = 0
    i = start
    length = len(briefing_html)

    while i < length:
        # 匹配开标签 <div 或 <div...
        if briefing_html[i:i+4] == '<div':
            # 确保是 <div 后面跟空格或 >
            next_char_pos = i + 4
            if next_char_pos < length and briefing_html[next_char_pos] in (' ', '>', '\n', '\r', '\t'):
                depth += 1
        # 匹配闭标签 </div>
        elif briefing_html[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                end = i + 6  # 包含 </div>
                return briefing_html[start:end]
        i += 1

    return None


def extract_stats(briefing_html):
    """
    从简报 HTML 的 .stats 区域解析统计信息。
    返回 (total, science, arts) 元组。
    """
    # 匹配资讯总数
    total_match = re.search(r'资讯共?\s*(\d+)\s*条', briefing_html)
    # 匹配理工科数
    science_match = re.search(r'理工科?\s*(\d+)\s*条', briefing_html)
    # 匹配文科数
    arts_match = re.search(r'文科?\s*(\d+)\s*条', briefing_html)

    total = int(total_match.group(1)) if total_match else 0
    science = int(science_match.group(1)) if science_match else 0
    arts = int(arts_match.group(1)) if arts_match else 0

    return total, science, arts


def build_report_item_html(date_str, issue_num, total, science, arts):
    """构建报告列表条目 HTML"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    month = dt.month
    day = dt.day

    return (
        f'<div class="report-item latest" onclick="showReport(\'{date_str}\')">\n'
        f'  <span class="date">第{issue_num}期 · 高顿升学 · 每日行业速览</span>\n'
        f'  <span class="weekday">{month}月{day}日</span>\n'
        f'  <span style="font-size:13px;color:#718096;margin-left:12px;">资讯 {total} 条 · 理工 {science} · 文科 {arts}</span>\n'
        f'  <span class="badge badge-latest">最新</span>\n'
        f'  <button class="pdf-btn" onclick="event.stopPropagation(); downloadPDF(\'{date_str}\', this)">📥 打印为PDF</button>\n'
        f'</div>'
    )


def build_report_container(container_html, date_str, issue_num):
    """
    构建报告容器 HTML。
    仅替换最外层容器的 id/class/style，保留内部所有元素（含 section id）不变。
    """
    # 找到最外层开标签的结束位置
    first_close = container_html.find('>')
    if first_close == -1:
        error_exit("简报容器开标签格式错误")

    # 找到最外层容器对应的闭合 </div>，提取内部内容
    container_end = find_matching_div_end(container_html, 0)
    if container_end == -1:
        error_exit("简报容器无法找到匹配的闭合标签")

    inner_content = container_html[first_close + 1:container_end - 6]

    # 确保 class 包含 print-target
    opening_tag = container_html[:first_close]
    if 'print-target' not in opening_tag:
        opening_tag = opening_tag.replace(
            'container report-view',
            'container report-view print-target',
            1
        )

    # 用新的外层标签包裹内部内容（保留内部所有 id）
    result = (
        f'<div class="container report-view print-target" '
        f'id="report-{date_str}" '
        f'style="{REPORT_CONTAINER_STYLE}">'
        f'{inner_content}\n</div>'
    )

    return result


def add_report_item(index_html, new_item_html, date_str):
    """
    在 index-view 的报告列表中添加新条目。
    1. 将现有 latest 条目改为归档状态
    2. 在列表顶部插入新条目
    """
    # 检查是否已存在该日期的条目（幂等性）
    if f"showReport('{date_str}')" in index_html:
        # 检查是否是在 report-item 中（排除 report container 中的引用）
        # 查找 index-view 区域
        index_view_match = re.search(
            r'<div id="index-view">(.*?)</div>\s*(?:<!-- |<div id="watermark-view">)',
            index_html,
            re.DOTALL
        )
        if index_view_match:
            index_view_content = index_view_match.group(1)
            if f"showReport('{date_str}')" in index_view_content:
                return None, "already_exists"

    # 将现有的 latest 条目改为归档状态
    # 替换 class: "report-item latest" -> "report-item"
    index_html = re.sub(
        r'class="report-item latest"',
        'class="report-item"',
        index_html
    )
    # 替换 badge: badge-latest">最新 -> badge-archive">归档
    index_html = re.sub(
        r'class="badge badge-latest">最新',
        'class="badge badge-archive">归档',
        index_html
    )

    # 在 "📅 历史报告" 标题后插入新条目
    # 找到 <h2>📅 历史报告</h2> 后面的位置
    insert_pattern = re.compile(r'(<h2>📅 历史报告</h2>)')
    match = insert_pattern.search(index_html)
    if not match:
        return None, "insert_point_not_found"

    insert_pos = match.end()
    index_html = (
        index_html[:insert_pos]
        + '\n' + new_item_html + '\n'
        + index_html[insert_pos:]
    )

    return index_html, "ok"


def insert_report_container(index_html, container_html, date_str):
    """
    将报告容器插入到 index.html 中。
    插入位置：在 watermark-view 结束标签之后，在第一个现有报告容器之前。
    """
    # 查找 "<!-- 简报内容视图 -->" 注释作为插入标记
    marker = '<!-- 简报内容视图 -->'
    marker_pos = index_html.find(marker)

    if marker_pos != -1:
        # 在注释后面插入
        insert_pos = marker_pos + len(marker)
        # 跳过注释后面的空白行
        while insert_pos < len(index_html) and index_html[insert_pos] in ('\n', '\r', ' '):
            insert_pos += 1
        index_html = (
            index_html[:insert_pos]
            + '\n\n' + container_html + '\n\n'
            + index_html[insert_pos:]
        )
        return index_html, "ok"

    # 备选方案：查找 watermark-view 的结束标签
    # 找 <div id="watermark-view"> 之后的第一个报告容器
    wm_start = index_html.find('<div id="watermark-view">')
    if wm_start == -1:
        return None, "watermark_view_not_found"

    # 从 watermark-view 开始位置找第一个 report- 容器
    report_pattern = re.compile(r'\n<div class="container report-view')
    match = report_pattern.search(index_html, wm_start)
    if match:
        insert_pos = match.start()
        index_html = (
            index_html[:insert_pos]
            + '\n\n' + container_html + '\n'
            + index_html[insert_pos:]
        )
        return index_html, "ok"

    return None, "insert_point_not_found"


def find_matching_div_end(html_content, open_start):
    """
    给定一个 <div 开标签的起始位置，通过 div 嵌套计数找到匹配的闭合 </div> 结束位置。
    返回闭合标签之后的位置；找不到返回 -1。
    """
    depth = 0
    i = open_start
    length = len(html_content)
    while i < length:
        if html_content[i:i+4] == '<div':
            next_char_pos = i + 4
            if next_char_pos < length and html_content[next_char_pos] in (' ', '>', '\n', '\r', '\t'):
                depth += 1
        elif html_content[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                return i + 6
        i += 1
    return -1


def replace_existing_report(index_html, date_str, new_container_html, total, science, arts):
    """
    --force 模式：用新的报告容器替换 index.html 中已有的同名报告容器，
    并更新索引列表条目中的资讯统计。保留原有的 latest/archive 状态。
    返回 (新html, 状态消息)。
    """
    # 1. 替换报告容器
    container_marker = f'id="report-{date_str}"'
    marker_pos = index_html.find(container_marker)
    if marker_pos == -1:
        return None, "container_not_found"

    container_open = index_html.rfind('<div', 0, marker_pos)
    container_end = find_matching_div_end(index_html, container_open)
    if container_end == -1:
        return None, "container_close_not_found"

    index_html = (
        index_html[:container_open]
        + new_container_html
        + index_html[container_end:]
    )

    # 2. 更新索引条目中的统计信息
    item_pattern = re.compile(
        r'<div class="report-item[^"]*"[^>]*onclick="showReport\(\''
        + re.escape(date_str)
        + r"'\)\""
    )
    m = item_pattern.search(index_html)
    if m:
        item_end = find_matching_div_end(index_html, m.start())
        if item_end != -1:
            item_html = index_html[m.start():item_end]
            new_item_html = re.sub(
                r'资讯 \d+ 条 · 理工 \d+ · 文科 \d+',
                f'资讯 {total} 条 · 理工 {science} · 文科 {arts}',
                item_html
            )
            index_html = (
                index_html[:m.start()]
                + new_item_html
                + index_html[item_end:]
            )

    return index_html, "ok"


def validate_div_balance(html_content):
    """
    验证 HTML 的 div 嵌套平衡。
    返回 (is_valid, error_messages)
    """
    errors = []

    # 全局 body 内的 div 平衡检查
    body_match = re.search(r'<body>(.*?)</body>', html_content, re.DOTALL)
    if body_match:
        body_content = body_match.group(1)
        balance = 0
        i = 0
        length = len(body_content)
        while i < length:
            if body_content[i:i+4] == '<div':
                next_char_pos = i + 4
                if next_char_pos < length and body_content[next_char_pos] in (' ', '>', '\n', '\r', '\t'):
                    balance += 1
            elif body_content[i:i+6] == '</div>':
                balance -= 1
            i += 1

        if balance != 0:
            errors.append(f"全局 body div balance = {balance}（应为 0）")

    # 检查每个报告容器的 div 平衡
    report_containers = re.finditer(
        r'<div class="container report-view[^"]*"[^>]*id="report-(\d{4}-\d{2}-\d{2})"',
        html_content
    )

    for match in report_containers:
        report_date = match.group(1)
        container_start = match.start()

        # 从这个容器开始计算 div 平衡
        depth = 0
        i = container_start
        length = len(html_content)
        container_end = -1

        while i < length:
            if html_content[i:i+4] == '<div':
                next_char_pos = i + 4
                if next_char_pos < length and html_content[next_char_pos] in (' ', '>', '\n', '\r', '\t'):
                    depth += 1
            elif html_content[i:i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    container_end = i + 6
                    break
            i += 1

        if depth != 0:
            errors.append(f"报告容器 report-{report_date} div balance = {depth}（应为 0）")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description='将简报集成到 index.html')
    parser.add_argument('--date', required=True, help='简报日期，格式: YYYY-MM-DD')
    parser.add_argument('--index-file', default=DEFAULT_INDEX_FILE, help='index.html 路径')
    parser.add_argument('--briefing-file', default=None, help='简报文件路径（默认自动推断）')
    parser.add_argument('--dry-run', action='store_true', help='只检查不修改')
    parser.add_argument('--force', action='store_true',
                        help='强制更新：用简报内容替换 index.html 中已有的同名报告，保留 latest/archive 状态')
    args = parser.parse_args()

    # 解析日期
    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        error_exit(f"日期格式错误: {args.date}，应为 YYYY-MM-DD")

    date_str = args.date
    issue_num = calc_issue_number(target_date)

    # 确定简报文件路径
    if args.briefing_file:
        briefing_path = args.briefing_file
    else:
        briefing_path = os.path.join(BASE_DIR, f"briefing_{date_str}.html")

    index_path = args.index_file

    # 检查文件是否存在
    if not os.path.exists(briefing_path):
        error_exit(f"简报文件不存在: {briefing_path}")
    if not os.path.exists(index_path):
        error_exit(f"index.html 不存在: {index_path}")

    # 读取简报文件
    print(f"📖 读取简报文件: {briefing_path}")
    with open(briefing_path, 'r', encoding='utf-8') as f:
        briefing_html = f.read()

    # 读取 index.html
    print(f"📖 读取 index.html: {index_path}")
    with open(index_path, 'r', encoding='utf-8') as f:
        index_html = f.read()

    # 幂等性检查：是否已集成
    already_integrated = f'id="report-{date_str}"' in index_html
    if already_integrated and not args.force:
        print(f"⏭️  第{issue_num}期 ({date_str}) 已存在于 index.html 中，跳过。")
        sys.exit(0)

    # 提取报告容器
    print(f"🔍 提取报告容器...")
    container_html = extract_report_container(briefing_html)
    if not container_html:
        error_exit("无法从简报文件中提取报告容器（未找到 <div class=\"container report-view\"）")

    # 提取统计信息
    total, science, arts = extract_stats(briefing_html)
    print(f"📊 统计信息: 资讯 {total} 条 · 理工 {science} · 文科 {arts}")

    if total == 0:
        error_exit("无法解析统计信息（资讯数为 0）")

    # 构建报告列表条目
    new_item_html = build_report_item_html(date_str, issue_num, total, science, arts)

    # 构建报告容器
    new_container_html = build_report_container(container_html, date_str, issue_num)

    if already_integrated and args.force:
        # --force 模式：替换已有报告，保留 latest/archive 状态
        print(f"🔄 强制更新第{issue_num}期 ({date_str}) 的报告内容...")
        index_html, status = replace_existing_report(
            index_html, date_str, new_container_html, total, science, arts
        )
        if status != "ok":
            error_exit(f"强制更新失败: {status}")
    else:
        # 正常模式：更新 index.html - 添加报告列表条目
        print(f"📝 添加报告列表条目...")
        index_html, status = add_report_item(index_html, new_item_html, date_str)
        if status == "already_exists":
            print(f"⏭️  第{issue_num}期 ({date_str}) 的列表条目已存在，跳过。")
            sys.exit(0)
        elif status == "insert_point_not_found":
            error_exit("未找到报告列表的插入点（📅 历史报告）")

        # 插入报告容器
        print(f"📝 插入报告容器...")
        index_html, status = insert_report_container(index_html, new_container_html, date_str)
        if status != "ok":
            error_exit(f"无法插入报告容器: {status}")

    # 验证 HTML 结构
    print(f"🔍 验证 HTML div 嵌套平衡...")
    is_valid, errors = validate_div_balance(index_html)
    if not is_valid:
        print("❌ HTML div 嵌套验证失败:", file=sys.stderr)
        for err in errors:
            print(f"   - {err}", file=sys.stderr)
        print("\n⚠️  未保存修改，index.html 保持不变。", file=sys.stderr)
        sys.exit(1)

    print("✅ div 嵌套验证通过")

    # Dry run 模式
    if args.dry_run:
        print("🏁 Dry run 模式，不保存修改。")
        sys.exit(0)

    # 保存 index.html
    print(f"💾 保存 index.html...")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)

    if already_integrated and args.force:
        print(f"✅ 第{issue_num}期 ({date_str}) 已强制更新")
    else:
        print(f"✅ 第{issue_num}期 ({date_str}) 已集成到 index.html")
    print(f"   资讯 {total} 条 · 理工 {science} · 文科 {arts}")


if __name__ == "__main__":
    main()
