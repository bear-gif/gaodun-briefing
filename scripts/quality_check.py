#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高顿升学 · 报告质量检查工具
对每期行业报告执行14项质量检查，并可选择性自动修复部分问题。

用法:
    python3 quality_check.py [--date YYYY-MM-DD] [--briefing-file path] [--index-file path] [--fix]
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, date

# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INDEX_FILE = os.path.join(BASE_DIR, "index.html")
FIRST_ISSUE_DATE = date(2026, 8, 17)  # 第1期

REQUIRED_FIELDS = ["事件背景", "行业简述", "关联专业", "学历·岗位·薪资", "地域优势", "报考小贴士"]

SCIENCE_MAJORS = {
    "电子信息工程", "计算机科学与技术", "人工智能", "自动化", "通信工程",
    "软件工程", "数据科学与大数据技术", "物联网工程", "网络工程", "信息安全",
    "机械设计制造及其自动化", "电气工程及其自动化", "电子信息科学与技术",
    "微电子科学与工程", "光电信息科学与工程", "能源与动力工程", "建筑学",
    "土木工程", "测绘工程", "化学工程与工艺", "材料科学与工程", "生物工程",
    "生物医学工程", "食品科学与工程", "航空航天工程", "船舶与海洋工程",
    "核工程与核技术", "机器人工程", "智能制造工程", "储能科学与工程",
    "气象学", "大气科学", "海洋科学", "地质学", "地理科学", "物理学",
    "应用物理学", "数学", "应用数学", "统计学", "化学", "应用化学",
    "材料化学", "新能源科学与工程", "车辆工程", "交通工程", "导航工程",
    "武器系统与工程", "智能科学与技术", "空间科学与技术", "飞行器设计与工程",
    "医学", "临床医学", "口腔医学", "药学", "护理学", "预防医学",
}

# 领域识别关键词（文科多样性用）
DOMAIN_KEYWORDS = {
    "金融/经济": ["金融", "股票", "基金", "证券", "银行", "保险", "投资", "IPO", "融资", "市值"],
    "教育": ["教育", "学校", "专业", "招生", "考试", "教师", "学生"],
    "法律/政策": ["法律", "法规", "政策", "规划", "部门", "政府"],
    "传媒/文化": ["媒体", "新闻", "文化", "艺术", "出版", "影视"],
    "文旅/消费": ["旅游", "文旅", "消费", "酒店", "餐饮"],
    "医疗/健康": ["医疗", "健康", "医院", "药品", "疫苗"],
}

# 理科领域识别关键词
SCIENCE_DOMAIN_KEYWORDS = {
    "计算机/AI": ["AI", "人工智能", "计算机", "算法", "大模型", "芯片", "软件"],
    "航空航天": ["航天", "火箭", "卫星", "飞机", "航空"],
    "能源/材料": ["能源", "电池", "光伏", "材料", "新能源"],
    "生物/医学": ["生物", "医学", "基因", "药物", "疫苗"],
    "基础科学": ["物理", "数学", "化学", "天文", "地质"],
    "工程/制造": ["工程", "制造", "机器人", "自动化"],
    "通信/网络": ["通信", "5G", "网络", "互联网"],
}

# 禁止出现在文科内容中的关键词
FORBIDDEN_KEYWORDS = [
    "股价", "股市", "金融", "基金", "证券", "银行理财",
    "保险投资", "IPO", "市值", "涨停", "跌停", "指数涨跌",
    "心理学", "应用心理学",
]


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────
def read_file(path):
    """读取文件，UTF-8编码"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path, content):
    """写入文件，UTF-8编码"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def backup_file(path):
    """备份文件为 .bak"""
    bak = path + ".bak"
    shutil.copy2(path, bak)
    return bak


def calc_expected_issue(date_str):
    """根据日期计算预期期数"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (d - FIRST_ISSUE_DATE).days + 1
    except ValueError:
        return None


def extract_date_from_briefing(html):
    """从briefing HTML中提取日期"""
    # 从 date-line 提取
    m = re.search(r'第(\d+)期.*?(\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(2)
    # 从文件名推断不了，尝试 stats 附近
    m = re.search(r'(\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(1)
    return None


def extract_report_block(html, report_id):
    """从index.html中提取指定报告的全部HTML内容"""
    pattern = rf'(<div[^>]*id="{re.escape(report_id)}"[^>]*>)(.*?)(?=<div[^>]*id="report-|</body>)'
    m = re.search(pattern, html, re.DOTALL)
    if m:
        return m.group(1) + m.group(2)
    return None


# ──────────────────────────────────────────────
# 解析卡片
# ──────────────────────────────────────────────
def parse_cards(html):
    """解析所有卡片，返回 [{type: 'science'|'arts', title, content_html, fields: {field_name: content}, ...}]"""
    cards = []
    # 匹配每个 card 块
    card_pattern = re.compile(
        r'<div\s+class="card\s+(science|arts|general)"[^>]*>(.*?)</div>\s*(?=<div\s+(?:class="card|id="section-|class="tip|style=)|</div>\s*<div\s+id="section)',
        re.DOTALL
    )
    
    # 更健壮的卡片提取：逐个找 card 开头
    card_starts = [(m.start(), m.group(1)) for m in re.finditer(r'<div\s+class="card\s+(science|arts|general)"', html)]
    
    for i, (start, card_type) in enumerate(card_starts):
        # 确定卡片结束位置
        if i + 1 < len(card_starts):
            end = card_starts[i + 1][0]
        else:
            # 最后一个卡片，找到 section 分隔或结尾
            end_match = re.search(r'<div\s+id="section-', html[start + 100:])
            if end_match:
                end = start + 100 + end_match.start()
            else:
                end = len(html)
        
        card_html = html[start:end]
        
        # 提取标题
        title_m = re.search(r'<h2>(.*?)</h2>', card_html)
        title = title_m.group(1).strip() if title_m else ""
        
        # 提取各字段内容
        fields = {}
        for field in REQUIRED_FIELDS:
            if field == "报考小贴士":
                # tip-block 中
                tip_m = re.search(r'<div\s+class="tip-block">(.*?)</div>\s*$', card_html, re.DOTALL)
                if tip_m:
                    fields[field] = tip_m.group(1).strip()
            else:
                # 在 content 区域，查找 sub-title 后的内容
                escaped_field = re.escape(field)
                field_m = re.search(
                    rf'<h3[^>]*>{escaped_field}</h3>\s*(.*?)(?=<h3|</div>\s*<div\s+class="tip|$)',
                    card_html, re.DOTALL
                )
                if field_m:
                    fields[field] = field_m.group(1).strip()
        
        # 提取关联专业文本
        majors_text = ""
        majors_m = re.search(r'关联专业</h3>\s*<p>(.*?)</p>', card_html, re.DOTALL)
        if majors_m:
            majors_text = majors_m.group(1).strip()
        
        cards.append({
            "type": card_type,
            "title": title,
            "html": card_html,
            "fields": fields,
            "majors_text": majors_text,
        })
    
    return cards


# ──────────────────────────────────────────────
# 检查结果类
# ──────────────────────────────────────────────
class CheckResult:
    def __init__(self, check_id, name):
        self.check_id = check_id
        self.name = name
        self.passed = True
        self.fixed = False
        self.needs_manual = False
        self.message = ""
    
    @property
    def status_str(self):
        if self.passed:
            return "✅ 通过"
        elif self.fixed:
            return "❌ 发现 → 已修复"
        elif self.needs_manual:
            return "❌ 发现 → 需人工"
        return "⚠️ 未知"


# ──────────────────────────────────────────────
# 14项检查
# ──────────────────────────────────────────────

def check_01_completeness(html, cards, fix=False):
    """检查项1：内容完整性"""
    result = CheckResult(1, "内容完整性")
    
    total_cards = len(cards)
    if total_cards < 7:
        result.passed = False
        result.needs_manual = True
        result.message = f"总资讯数仅 {total_cards} 条（<7），需要补充"
        return result
    
    incomplete = 0
    for card in cards:
        missing = [f for f in REQUIRED_FIELDS if f not in card["fields"] or not card["fields"][f].strip()]
        if missing:
            incomplete += 1
    
    if total_cards > 0 and incomplete / total_cards > 0.3:
        result.passed = False
        result.needs_manual = True
        result.message = f"{incomplete}/{total_cards} 卡片缺失字段（>30%），需重新抓取"
    elif incomplete > 0:
        result.passed = False
        result.needs_manual = True
        result.message = f"{incomplete}/{total_cards} 卡片缺失字段"
    
    if result.passed:
        result.message = f"{total_cards} 张卡片，字段完整"
    
    return result


def check_02_non_empty(html, cards, fix=False):
    """检查项2：页面是否有内容"""
    result = CheckResult(2, "页面非空白")
    
    if not cards:
        # 进一步确认
        card_count = len(re.findall(r'class="card\s+(science|arts|general)"', html))
        if card_count == 0:
            result.passed = False
            result.needs_manual = True
            result.message = "页面无任何卡片，为空页面"
        else:
            result.message = f"解析到 {card_count} 张卡片"
    else:
        result.message = f"共 {len(cards)} 张卡片"
    
    return result


def check_03_margins(html, fix=False):
    """检查项3：页面两侧留白"""
    result = CheckResult(3, "两侧留白")
    
    # 检查容器是否有 max-width 和 margin: auto
    container_match = re.search(
        r'<div[^>]*class="container\s+report-view[^"]*"[^>]*>',
        html
    )
    
    if not container_match:
        # 检查内嵌式
        container_match = re.search(
            r'<div[^>]*id="report-[^"]*"[^>]*class="container[^"]*report-view[^"]*"[^>]*>',
            html
        )
    
    if container_match:
        tag = container_match.group(0)
        has_max_width = bool(re.search(r'max-width\s*:', tag, re.IGNORECASE)) or \
                        bool(re.search(r'max-width\s*:\s*\d+', html[:5000]))
        has_margin_auto = bool(re.search(r'margin\s*:\s*[^;]*auto', tag, re.IGNORECASE)) or \
                          bool(re.search(r'margin\s*:\s*0\s+auto', html[:5000]))
        
        if not has_max_width or not has_margin_auto:
            result.passed = False
            if fix:
                result.message = "容器缺少 max-width 或 margin:auto"
            else:
                result.passed = False
                result.needs_manual = True
                result.message = "容器缺少 max-width 或 margin:auto，需人工修复"
        else:
            result.message = "容器设置了 max-width 和 margin:auto"
    else:
        # 检查全局CSS
        has_css_max = bool(re.search(r'\.container\s*\{[^}]*max-width\s*:', html))
        has_css_margin = bool(re.search(r'\.container\s*\{[^}]*margin\s*:\s*[^}]*auto', html))
        if has_css_max and has_css_margin:
            result.message = "通过CSS定义设置了 max-width 和 margin:auto"
        else:
            result.passed = False
            result.needs_manual = True
            result.message = "未找到容器的宽度约束设置"
    
    return result


def check_04_issue_number(date_str, html, fix=False):
    """检查项4：期数正确性"""
    result = CheckResult(4, "期数正确性")
    
    expected = calc_expected_issue(date_str)
    if expected is None:
        result.passed = False
        result.needs_manual = True
        result.message = f"无法从日期 '{date_str}' 计算期数"
        return result
    
    # 查找 date-line 中的期数
    date_line_m = re.search(r'第(\d+)期', html)
    if not date_line_m:
        result.passed = False
        result.needs_manual = True
        result.message = "未找到 date-line 中的期数标记"
        return result
    
    actual = int(date_line_m.group(1))
    
    if actual != expected:
        result.passed = False
        if fix:
            result.fixed = True
            result.message = f"期数错误：实际第{actual}期，预期第{expected}期 → 已修复"
        else:
            result.needs_manual = True
            result.message = f"期数错误：实际第{actual}期，预期第{expected}期"
    else:
        result.message = f"第{actual}期 ✓"
    
    return result


def check_05_category_correctness(cards, fix=False):
    """检查项5：文理分类正确性"""
    result = CheckResult(5, "文理分类正确性")
    
    science_issues = []
    arts_issues = []
    
    for card in cards:
        majors_text = card.get("majors_text", "")
        if not majors_text:
            continue
        
        # 提取各专业名
        majors = re.split(r'[、，,；;\s]+', majors_text)
        majors = [m.strip() for m in majors if m.strip()]
        
        if not majors:
            continue
        
        if card["type"] == "science":
            # 理工科卡片：关联专业应至少有一个理科专业
            sci_count = sum(1 for m in majors if m in SCIENCE_MAJORS)
            if sci_count == 0 and len(majors) > 0:
                science_issues.append(card["title"][:20])
        
        elif card["type"] == "arts":
            # 文科卡片：关联专业应至少有一个非理科专业（或全部非理科）
            sci_count = sum(1 for m in majors if m in SCIENCE_MAJORS)
            if sci_count == len(majors) and len(majors) > 0:
                arts_issues.append(card["title"][:20])
    
    problems = []
    if science_issues:
        problems.append(f"理工科卡片全为文科专业: {', '.join(science_issues[:3])}")
    if arts_issues:
        problems.append(f"文科卡片全为理科专业: {', '.join(arts_issues[:3])}")
    
    if problems:
        result.passed = False
        result.needs_manual = True
        result.message = "；".join(problems)
    else:
        result.message = "文理分类正确"
    
    return result


def check_06_core_judgments(html, fix=False):
    """检查项6：今日要点速览"""
    result = CheckResult(6, "今日要点速览")
    
    # 检查 core-judgments 是否存在且唯一
    cj_matches = re.findall(r'<div\s+class="core-judgments">(.*?)</div>\s*</div>', html, re.DOTALL)
    
    if not cj_matches:
        result.passed = False
        result.needs_manual = True
        result.message = "未找到 core-judgments 区块"
        return result
    
    if len(cj_matches) > 1:
        result.passed = False
        result.needs_manual = True
        result.message = f"core-judgments 出现 {len(cj_matches)} 次（应唯一）"
        return result
    
    # 提取要点数量
    cj_html = cj_matches[0]
    li_items = re.findall(r'<li>(.*?)</li>', cj_html, re.DOTALL)
    
    if len(li_items) < 3:
        result.passed = False
        result.needs_manual = True
        result.message = f"要点仅 {len(li_items)} 条（应≥3条）"
        return result
    
    # 检查重复
    seen = set()
    dupes = 0
    for item in li_items:
        clean = re.sub(r'<[^>]+>', '', item).strip()
        if clean in seen:
            dupes += 1
        seen.add(clean)
    
    if dupes > 0:
        result.passed = False
        result.needs_manual = True
        result.message = f"发现 {dupes} 条重复要点"
        return result
    
    result.message = f"{len(li_items)} 条要点，无重复"
    return result


def check_07_card_background(html, cards, fix=False):
    """检查项7：卡片背景色"""
    result = CheckResult(7, "卡片背景色")
    
    issues = []
    
    for card in cards:
        card_html = card["html"]
        # 检查 card 本身的 style 属性
        style_match = re.search(r'<div\s+class="card\s+[^"]*"[^>]*style="([^"]*)"', card_html)
        if style_match:
            style = style_match.group(1)
            # 检查是否有非白色背景
            bg_match = re.search(r'background\s*:\s*([^;]+)', style, re.IGNORECASE)
            if bg_match:
                bg_val = bg_match.group(1).strip().lower()
                # 排除白色系
                if bg_val not in ("#fff", "#ffffff", "white", "#fff!important", "rgb(255,255,255)"):
                    issues.append(f"卡片 '{card['title'][:20]}' 背景: {bg_val}")
    
    # 检查卡片是否在 core-judgments 内部（嵌套错误）
    # 查找 core-judgments 块中是否包含 card 元素
    cj_pattern = re.compile(r'<div\s+class="core-judgments">(.*?)</div>\s*(?:</div>|<div\s)', re.DOTALL)
    for m in cj_pattern.finditer(html):
        inner = m.group(1)
        if re.search(r'class="card\s+', inner):
            issues.append("卡片嵌套在 core-judgments 内部（HTML嵌套错误）")
    
    if issues:
        result.passed = False
        result.needs_manual = True
        result.message = "；".join(issues[:3])
    else:
        result.message = "卡片背景色正常"
    
    return result


def check_08_list_format(cards, fix=False):
    """检查项8：板块列表格式"""
    result = CheckResult(8, "板块列表格式")
    
    issues = []
    for card in cards:
        for field in ["关联专业", "学历·岗位·薪资"]:
            content = card["fields"].get(field, "")
            if not content:
                continue
            
            # 检查是否包含列表格式（ul/li、顿号分隔、换行分隔等）
            has_list = bool(re.search(r'<(?:ul|li|br)', content, re.IGNORECASE))
            has_separator = bool(re.search(r'[、，,；;·]', content))
            has_newline = bool(re.search(r'\n', content))
            
            # 如果纯文本且无分隔符，视为堆叠
            plain_text = re.sub(r'<[^>]+>', '', content).strip()
            if plain_text and not has_list and not has_separator and not has_newline:
                # 单个词组，可接受
                if len(plain_text.split()) > 3 and len(plain_text) > 30:
                    issues.append(f"'{card['title'][:15]}'的{field}堆叠为一段")
    
    if issues:
        result.passed = False
        result.needs_manual = True
        result.message = f"{len(issues)} 处内容堆叠为段落，需拆分为列表"
    else:
        result.message = "列表格式正常"
    
    return result


def check_09_print_visibility(html_briefing, html_index, fix=False):
    """检查项9：打印时要点可见"""
    result = CheckResult(9, "打印时要点可见")
    
    # 检查 @media print 中是否有 core-judgments 和 stats 的显示规则
    print_sections = re.findall(r'@media\s+print\s*\{(.*?)\}(?:\s*\})?', html_index or html_briefing, re.DOTALL)
    
    # 合并所有 print 块
    print_css = " ".join(print_sections)
    
    has_cj_print = bool(re.search(r'core-judgments.*?display\s*:\s*block', print_css, re.IGNORECASE | re.DOTALL))
    has_stats_print = bool(re.search(r'\.stats.*?display\s*:\s*block', print_css, re.IGNORECASE | re.DOTALL))
    
    # 也检查是否隐藏
    has_cj_hidden = bool(re.search(r'core-judgments.*?display\s*:\s*none', print_css, re.IGNORECASE | re.DOTALL))
    has_stats_hidden = bool(re.search(r'\.stats.*?display\s*:\s*none', print_css, re.IGNORECASE | re.DOTALL))
    
    if has_cj_hidden or has_stats_hidden:
        result.passed = False
        result.needs_manual = True
        result.message = "打印CSS中要点/统计被设为隐藏"
    elif has_cj_print or has_stats_print:
        result.message = "打印CSS中已设置要点/统计显示规则"
    else:
        # 检查是否整体被隐藏
        # 如果 report-header 中的 date-line/stats 被隐藏，但 core-judgments 没有被特别设置
        header_hidden = bool(re.search(r'report-header\s+(?:a|\.date-line|\.stats).*?display\s*:\s*none', print_css, re.DOTALL))
        if header_hidden and not has_cj_print:
            result.passed = False
            if fix:
                result.message = "打印时 header 被隐藏但 core-judgments 未显式显示 → 需人工添加CSS规则"
                result.needs_manual = True
            else:
                result.needs_manual = True
                result.message = "打印时 header 被隐藏，core-judgments 未显式设置显示规则"
        else:
            result.message = "打印CSS无冲突规则"
    
    return result


def check_10_index_completeness(html_index, fix=False):
    """检查项10：索引页完整性"""
    result = CheckResult(10, "索引页完整性")
    
    if not html_index:
        result.passed = False
        result.needs_manual = True
        result.message = "未提供 index.html"
        return result
    
    # 提取 report-list 中的 report-item
    report_list_m = re.search(r'class="report-list"(.*?)(?=<div\s+class="container\s+report-view|<script)', html_index, re.DOTALL)
    if not report_list_m:
        # 尝试其他匹配
        report_list_m = re.search(r'class="report-list"(.*?)(?=<div[^>]*id="report-)', html_index, re.DOTALL)
    
    if not report_list_m:
        result.passed = False
        result.needs_manual = True
        result.message = "未找到 report-list 区域"
        return result
    
    list_html = report_list_m.group(1)
    
    # 提取所有 report-item 中的日期
    items = re.findall(r"showReport\('(\d{4}-\d{2}-\d{2})'\)", list_html)
    
    # 提取所有存在的 report-YYYY-MM-DD 容器
    reports_in_page = re.findall(r'id="report-(\d{4}-\d{2}-\d{2})"', html_index)
    
    # 检查：索引项是否覆盖了所有存在的报告
    missing_from_index = set(reports_in_page) - set(items)
    extra_in_index = set(items) - set(reports_in_page)
    
    if missing_from_index:
        result.passed = False
        result.needs_manual = True
        result.message = f"索引缺失 {len(missing_from_index)} 期: {', '.join(sorted(missing_from_index)[:5])}"
        return result
    
    # 检查日期是否倒序
    dates = []
    for d in items:
        try:
            dates.append(datetime.strptime(d, "%Y-%m-%d").date())
        except ValueError:
            pass
    
    is_descending = all(dates[i] >= dates[i + 1] for i in range(len(dates) - 1))
    
    if not is_descending:
        result.passed = False
        result.needs_manual = True
        result.message = "索引未按日期倒序排列"
        return result
    
    result.message = f"索引完整（{len(items)}期），按日期倒序"
    return result


def check_11_index_no_content(html_index, fix=False):
    """检查项11：索引页不含报告正文"""
    result = CheckResult(11, "索引页不含正文")
    
    if not html_index:
        result.passed = False
        result.needs_manual = True
        result.message = "未提供 index.html"
        return result
    
    # 提取 report-list 区域
    report_list_m = re.search(r'class="report-list"(.*?)(?=<div[^>]*class="container\s+report-view|<div[^>]*id="report-)', html_index, re.DOTALL)
    if not report_list_m:
        result.message = "未找到 report-list 或已正确隔离"
        return result
    
    list_html = report_list_m.group(1)
    
    # 检查是否包含报告正文元素
    content_markers = ["事件背景", "行业简述", "关联专业", "学历·岗位·薪资", "地域优势"]
    found = []
    for marker in content_markers:
        if marker in list_html:
            found.append(marker)
    
    if found:
        result.passed = False
        result.needs_manual = True
        result.message = f"索引中混入正文内容: {', '.join(found)}"
    else:
        result.message = "索引页纯净，无正文混入"
    
    return result


def check_12_arts_diversity(cards, fix=False):
    """检查项12：文科资讯多样性"""
    result = CheckResult(12, "文科资讯多样性")
    
    arts_cards = [c for c in cards if c["type"] == "arts"]
    if not arts_cards:
        result.message = "无文科资讯，跳过"
        return result
    
    # 合并所有文科卡片的标题和内容
    all_text = ""
    for card in arts_cards:
        all_text += card.get("title", "") + " "
        all_text += card.get("majors_text", "") + " "
        for field_content in card["fields"].values():
            all_text += re.sub(r'<[^>]+>', '', field_content) + " "
    
    # 统计覆盖的领域
    covered_domains = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in all_text:
                covered_domains.add(domain)
                break
    
    if len(covered_domains) < 3:
        result.passed = False
        result.needs_manual = True
        result.message = f"文科仅覆盖 {len(covered_domains)} 个领域（需≥3）: {', '.join(covered_domains) if covered_domains else '无'}"
    else:
        result.message = f"文科覆盖 {len(covered_domains)} 个领域: {', '.join(covered_domains)}"
    
    return result


def check_13_science_diversity(cards, fix=False):
    """检查项13：理科资讯多样性"""
    result = CheckResult(13, "理科资讯多样性")
    
    sci_cards = [c for c in cards if c["type"] == "science"]
    if not sci_cards:
        result.message = "无理科资讯，跳过"
        return result
    
    # 合并所有理科卡片内容
    all_text = ""
    for card in sci_cards:
        all_text += card.get("title", "") + " "
        for field_content in card["fields"].values():
            all_text += re.sub(r'<[^>]+>', '', field_content) + " "
    
    # 统计覆盖的领域
    covered_domains = set()
    for domain, keywords in SCIENCE_DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in all_text:
                covered_domains.add(domain)
                break
    
    # 检查是否 >30% 集中在计算机/AI
    total_cards = len(sci_cards)
    ai_count = 0
    ai_keywords = SCIENCE_DOMAIN_KEYWORDS["计算机/AI"]
    for card in sci_cards:
        card_text = card.get("title", "")
        for fc in card["fields"].values():
            card_text += re.sub(r'<[^>]+>', '', fc)
        if any(kw in card_text for kw in ai_keywords):
            ai_count += 1
    
    if total_cards > 0 and ai_count / total_cards > 0.3 and len(covered_domains) < 3:
        result.passed = False
        result.needs_manual = True
        result.message = f"理科 {ai_count}/{total_cards} 集中在计算机/AI，领域覆盖不足: {', '.join(covered_domains)}"
    elif len(covered_domains) < 5:
        result.passed = False
        result.needs_manual = True
        result.message = f"理科仅覆盖 {len(covered_domains)} 个领域（需≥5）: {', '.join(covered_domains)}"
    else:
        result.message = f"理科覆盖 {len(covered_domains)} 个领域: {', '.join(sorted(covered_domains))}"
    
    return result


def check_14_arts_appropriateness(cards, fix=False):
    """检查项14：文科内容适宜性"""
    result = CheckResult(14, "文科内容适宜性")
    
    arts_cards = [c for c in cards if c["type"] == "arts"]
    if not arts_cards:
        result.message = "无文科资讯，跳过"
        return result
    
    violations = []
    for card in arts_cards:
        all_text = card.get("title", "")
        for field_content in card["fields"].values():
            all_text += " " + re.sub(r'<[^>]+>', '', field_content)
        
        for kw in FORBIDDEN_KEYWORDS:
            if kw in all_text:
                violations.append(f"'{card['title'][:15]}'含禁止词 '{kw}'")
                break  # 每张卡片只报一次
    
    if violations:
        result.passed = False
        result.needs_manual = True
        result.message = f"{len(violations)} 处违禁: {'; '.join(violations[:3])}"
    else:
        result.message = "文科内容符合规范"
    
    return result


def check_15_div_balance(html_index, fix=False):
    """检查项15：每个报告容器的div嵌套平衡性
    
    检测每个 report-view 容器是否正确闭合。
    如果某个容器的 div 未闭合，后续报告会被嵌套在该隐藏容器内导致页面空白。
    """
    result = CheckResult(15, "DIV嵌套平衡")
    
    if not html_index:
        result.passed = False
        result.needs_manual = True
        result.message = "未提供 index.html"
        return result
    
    # 找到所有报告容器的位置
    report_positions = []
    for m in re.finditer(r'<div[^>]*class="container\s+report-view[^"]*"[^>]*id="report-(\d{4}-\d{2}-\d{2})"[^>]*>', html_index):
        report_positions.append((m.start(), m.group(1)))
    
    if not report_positions:
        result.passed = False
        result.needs_manual = True
        result.message = "未找到任何报告容器"
        return result
    
    # 计算 body 开始到每个报告容器前的 div balance
    body_start = html_index.find('<body>')
    if body_start == -1:
        result.message = "无 body 标签，跳过"
        return result
    body_start += len('<body>')
    
    issues = []
    expected_balance = None
    
    for i, (pos, date_str) in enumerate(report_positions):
        section = html_index[body_start:pos]
        opens = len(re.findall(r'<div[\s>]', section))
        closes = section.count('</div>')
        balance = opens - closes
        
        if expected_balance is None:
            expected_balance = balance
        
        if balance != expected_balance:
            issues.append(f"第{calc_expected_issue(date_str) or '?'}期({date_str})前 balance={balance}（预期{expected_balance}）")
    
    # 也检查每个报告容器内部的 div 平衡
    for i, (pos, date_str) in enumerate(report_positions):
        # 找到这个容器到下一个容器之间的内容
        if i + 1 < len(report_positions):
            end_pos = report_positions[i + 1][0]
        else:
            end_pos = len(html_index)
        
        container_html = html_index[pos:end_pos]
        c_opens = len(re.findall(r'<div[\s>]', container_html))
        c_closes = container_html.count('</div>')
        c_balance = c_opens - c_closes
        
        if c_balance != 0:
            issues.append(f"第{calc_expected_issue(date_str) or '?'}期({date_str})内部 balance={c_balance}（应为0）")
    
    # 检查全局 body 的 div 平衡
    end_body = html_index.find('</body>')
    if end_body > 0:
        all_body = html_index[body_start:end_body]
        g_opens = len(re.findall(r'<div[\s>]', all_body))
        g_closes = all_body.count('</div>')
        if g_opens != g_closes:
            issues.append(f"body 全局 balance={g_opens - g_closes}（应为0）")
    
    if issues:
        result.passed = False
        if fix:
            result.needs_manual = True
            result.message = f"发现 {len(issues)} 处不平衡，需修复: {'; '.join(issues[:3])}"
        else:
            result.needs_manual = True
            result.message = f"发现 {len(issues)} 处不平衡: {'; '.join(issues[:3])}"
    else:
        result.message = f"全部 {len(report_positions)} 个报告容器 div 平衡正确"
    
    return result


def fix_div_balance(html):
    """修复报告容器的 div 嵌套不平衡问题
    
    逐个检查每个报告容器是否正确闭合。
    如果发现某个容器的 div 未闭合（balance > 0），在该容器内容结束处插入缺失的 </div>。
    """
    body_start = html.find('<body>')
    if body_start == -1:
        return html, False
    
    body_start += len('<body>')
    
    # 找到所有报告容器的位置
    report_pattern = re.compile(r'<div[^>]*class="container\s+report-view[^"]*"[^>]*id="report-(\d{4}-\d{2}-\d{2})"[^>]*>')
    report_positions = [(m.start(), m.group(1)) for m in report_pattern.finditer(html)]
    
    if len(report_positions) < 2:
        return html, False
    
    fixed = False
    # 从后往前修复，避免位置偏移
    for i in range(len(report_positions) - 2, -1, -1):
        current_pos, current_date = report_positions[i]
        next_pos, next_date = report_positions[i + 1]
        
        # 计算从 current_pos 到 next_pos 之间的 div balance
        container_section = html[current_pos:next_pos]
        opens = len(re.findall(r'<div[\s>]', container_section))
        closes = container_section.count('</div>')
        balance = opens - closes
        
        if balance > 0:
            # 容器有 balance 个未闭合的 div
            # 在 next_pos 前插入 balance 个 </div>
            insert_text = '\n' + '</div>\n' * balance
            html = html[:next_pos] + insert_text + html[next_pos:]
            fixed = True
    
    return html, fixed


# ──────────────────────────────────────────────
# 修复函数
# ──────────────────────────────────────────────
def fix_issue_number(html, date_str):
    """修复期数"""
    expected = calc_expected_issue(date_str)
    if expected is None:
        return html, False
    
    # 替换 date-line 中的期数
    new_html = re.sub(
        r'(第)\d+(期\s*·\s*高顿升学)',
        rf'\g<1>{expected}\g<2>',
        html
    )
    return new_html, new_html != html


def fix_margins_briefing(html):
    """修复briefing文件的容器留白"""
    # 检查并修改 container 的 style
    if 'max-width' not in html[:3000] or 'margin' not in html[:3000]:
        # 在 CSS 中确保有约束
        html = re.sub(
            r'(\.container\s*\{[^}]*)(})',
            lambda m: m.group(1) + ('' if 'max-width' in m.group(1) else ' max-width: 900px;') +
                      ('' if 'margin' in m.group(1) else ' margin: 0 auto;') + m.group(2),
            html, count=1
        )
    return html


def fix_print_css(html):
    """修复打印CSS中的要点显示"""
    # 在 @media print 块中添加 core-judgments 显示规则
    if re.search(r'@media\s+print', html):
        if 'core-judgments' not in re.search(r'@media\s+print\s*\{(.*?)\}', html, re.DOTALL).group(1):
            # 找到 @media print 块的结束位置
            def add_print_rule(m):
                inner = m.group(1)
                if 'core-judgments' not in inner:
                    inner += "\n    .core-judgments { display: block !important; }\n    .stats { display: block !important; }\n"
                return "@media print {" + inner + "}"
            html = re.sub(r'@media\s+print\s*\{(.*?)\}', add_print_rule, html, count=1, flags=re.DOTALL)
    return html


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────
def run_checks(date_str, briefing_file, index_file, fix_mode=False):
    """执行所有检查"""
    
    # 读取文件
    try:
        html_briefing = read_file(briefing_file)
    except FileNotFoundError:
        print(f"❌ 找不到简报文件: {briefing_file}")
        sys.exit(1)
    
    html_index = None
    if index_file and os.path.exists(index_file):
        try:
            html_index = read_file(index_file)
        except Exception:
            pass
    
    # 解析卡片
    cards = parse_cards(html_briefing)
    
    # 如果从index.html中查找，也解析一次
    report_block = None
    if html_index:
        report_id = f"report-{date_str}"
        report_block = extract_report_block(html_index, report_id)
        if report_block:
            cards_from_index = parse_cards(report_block)
            if cards_from_index:
                cards = cards_from_index
    
    results = []
    
    # 执行14项检查
    results.append(check_01_completeness(html_briefing, cards, fix_mode))
    results.append(check_02_non_empty(html_briefing, cards, fix_mode))
    results.append(check_03_margins(html_briefing, fix_mode))
    results.append(check_04_issue_number(date_str, html_briefing, fix_mode))
    results.append(check_05_category_correctness(cards, fix_mode))
    results.append(check_06_core_judgments(html_briefing, fix_mode))
    results.append(check_07_card_background(html_briefing, cards, fix_mode))
    results.append(check_08_list_format(cards, fix_mode))
    results.append(check_09_print_visibility(html_briefing, html_index, fix_mode))
    results.append(check_10_index_completeness(html_index, fix_mode))
    results.append(check_11_index_no_content(html_index, fix_mode))
    results.append(check_12_arts_diversity(cards, fix_mode))
    results.append(check_13_science_diversity(cards, fix_mode))
    results.append(check_14_arts_appropriateness(cards, fix_mode))
    results.append(check_15_div_balance(html_index, fix_mode))
    
    # 尝试修复
    if fix_mode:
        fixed_any = False
        
        # 修复期数
        if not results[3].passed and not results[3].needs_manual:
            new_html, changed = fix_issue_number(html_briefing, date_str)
            if changed:
                backup_file(briefing_file)
                write_file(briefing_file, new_html)
                results[3].fixed = True
                fixed_any = True
        
        # 修复留白
        if not results[2].passed:
            new_html = fix_margins_briefing(html_briefing)
            if new_html != html_briefing:
                backup_file(briefing_file)
                write_file(briefing_file, new_html)
                results[2].fixed = True
                fixed_any = True
        
        # 修复打印CSS
        if not results[8].passed:
            if html_index:
                new_index = fix_print_css(html_index)
                if new_index != html_index:
                    backup_file(index_file)
                    write_file(index_file, new_index)
                    results[8].fixed = True
                    fixed_any = True
        
        # 修复 div 嵌套平衡
        if not results[14].passed and html_index:
            new_index, changed = fix_div_balance(html_index)
            if changed:
                backup_file(index_file)
                write_file(index_file, new_index)
                results[14].fixed = True
                fixed_any = True
    
    return results, cards


def print_report(results, date_str, issue_num):
    """打印检查报告"""
    print()
    print("═" * 50)
    print(f"  高顿升学 · 报告质量检查报告")
    print(f"  日期：{date_str} | 期数：第{issue_num}期")
    print("═" * 50)
    
    for r in results:
        check_name = r.name
        # 对齐
        print(f"  检查项 {r.check_id:02d} - {check_name:<10s}  {r.status_str}")
        if r.message and r.message not in ("", check_name):
            # 仅当有问题时显示详情
            if not r.passed:
                print(f"    └─ {r.message}")
    
    passed_count = sum(1 for r in results if r.passed)
    fixed_count = sum(1 for r in results if r.fixed)
    manual_count = sum(1 for r in results if r.needs_manual)
    
    print("═" * 50)
    print(f"  总结：{passed_count}/15 通过，{fixed_count} 项已修复，{manual_count} 项需人工")
    print("═" * 50)
    print()


def main():
    parser = argparse.ArgumentParser(description="高顿升学 · 报告质量检查工具")
    parser.add_argument("--date", type=str, help="检查的日期 (YYYY-MM-DD)")
    parser.add_argument("--briefing-file", type=str, help="简报HTML文件路径")
    parser.add_argument("--index-file", type=str, default=DEFAULT_INDEX_FILE, help="索引HTML文件路径")
    parser.add_argument("--fix", action="store_true", help="启用自动修复模式")
    args = parser.parse_args()
    
    # 确定日期
    if args.date:
        date_str = args.date
    else:
        date_str = date.today().strftime("%Y-%m-%d")
    
    # 确定简报文件
    if args.briefing_file:
        briefing_file = args.briefing_file
    else:
        briefing_file = os.path.join(BASE_DIR, f"briefing_{date_str}.html")
    
    if not os.path.exists(briefing_file):
        # 尝试找最新的
        all_files = sorted([
            f for f in os.listdir(BASE_DIR)
            if f.startswith("briefing_") and f.endswith(".html")
        ])
        if all_files:
            latest = all_files[-1]
            date_str = latest.replace("briefing_", "").replace(".html", "")
            briefing_file = os.path.join(BASE_DIR, latest)
            print(f"⚠️  未找到 {date_str} 的简报，使用最新一期: {latest}")
        else:
            print(f"❌ 找不到任何简报文件")
            sys.exit(1)
    
    # 计算期数
    issue_num = calc_expected_issue(date_str) or "?"
    
    # 执行检查
    results, cards = run_checks(date_str, briefing_file, args.index_file, args.fix)
    
    # 打印报告
    print_report(results, date_str, issue_num)
    
    # 返回退出码
    has_manual = any(r.needs_manual for r in results)
    sys.exit(1 if has_manual else 0)


if __name__ == "__main__":
    main()
