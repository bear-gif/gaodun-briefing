#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate 3 briefing HTML files with full content cards."""
import os

WORK_DIR = "/Coze/Drive/\u9ad8\u987f\u5347\u5b66_·_\u884c\u4e1a\u8d44\u8baf"

COMMON_CSS = r"""
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body { font-family: -apple-system, BlinkmacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; background: #f5f7fa; color: #1a1a2e; line-height: 1.7; }
  .container { max-width: 960px; margin: 0 auto; padding: 30px 20px 60px; }
  .report-header { background: #fff; border-radius: 14px; padding: 28px 32px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
  .report-header .date-line { font-size: 20px; font-weight: 700; color: #1a1a2e; margin-bottom: 6px; }
  .report-header .stats { font-size: 14px; color: #718096; margin-bottom: 16px; }
  .report-header .stats span { display: inline-block; margin-right: 14px; }
  .core-judgments { background: #f7fafc; border-left: 4px solid #4299e1; padding: 16px 20px; border-radius: 0 8px 8px 0; }
  .core-judgments h3 { font-size: 15px; color: #2d3748; margin-bottom: 8px; }
  .core-judgments ul { list-style: none; }
  .core-judgments li { font-size: 14px; color: #4a5568; padding: 4px 0; padding-left: 18px; position: relative; }
  .core-judgments li::before { content: "\25b8"; position: absolute; left: 0; color: #4299e1; font-weight: bold; }
  .card { background: #fff; border-radius: 14px; padding: 28px 32px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border-top: 4px solid transparent; }
  .card.science { border-top-color: #4299e1; }
  .card.arts { border-top-color: #48bb78; }
  .card-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
  .card-head h2 { font-size: 18px; font-weight: 700; color: #1a1a2e; flex: 1; min-width: 200px; }
  .meta { display: flex; gap: 16px; font-size: 13px; color: #a0aec0; margin-bottom: 12px; flex-wrap: wrap; }
  .content p, .content li { font-size: 15px; color: #4a5568; line-height: 1.8; }
  .content ul { list-style: disc; padding-left: 20px; margin: 6px 0; }
  .content li { margin: 4px 0; }
  .footer { text-align: center; padding: 40px 20px; color: #a0aec0; font-size: 12px; }
  .sub-title { font-size: 15px; margin: 14px 0 6px; border-left: 3px solid #4299e1; padding-left: 10px; font-weight: 600; }
  .sub-title.sc { color: #4299e1; border-color: #4299e1; }
  .sub-title.gg { color: #48bb78; border-color: #48bb78; }
  .tip-block { background: #fef3c7; border-radius: 8px; padding: 14px 18px; margin: 12px 0; }
  .tip-block h3 { color: #92400e; font-size: 15px; margin: 0 0 8px; }
  .tip-block p { color: #92400e; margin: 0; font-size: 14px; line-height: 1.9; }
  /* Print styles */
  @media print {
    body.printing-report .container.report-view { padding: 0 8mm !important; margin: 0 auto !important; }
    .print-watermark { display: block !important; margin: 0 0 4mm 0 !important; }
    @page { margin: 10mm 18mm 10mm 18mm; size: auto; }
    body { margin: 0 !important; padding: 0 !important; background: #fff !important; }
    .quick-nav { display: none !important; }
    .card { margin-bottom: 4px !important; padding: 10px 14px !important; }
    [id^="section-"] { margin: 4px 0 2mm 0 !important; padding: 4px 8px !important; }
    .report-header a, .report-header .date-line, .report-header .stats { display: none !important; }
    body.printing-report #site-brand-header, body.printing-report #index-view, body.printing-report #watermark-view, body.printing-report .footer, body.printing-report .report-view { display: none !important; }
    body.printing-report .report-view.print-target { display: block !important; }
  }
"""

JS_BLOCK = r"""
<script>
function showIndex() {
  if (window.parent && window.parent.showIndex) { window.parent.showIndex(); return; }
  window.location.href = 'index.html';
}
function scrollToSection(id) {
  var el = document.getElementById(id);
  if (!el) return;
  var top = el.offsetTop - 20;
  window.scrollTo({ top: top, behavior: 'smooth' });
}
</script>
"""

def st(t, cls="sc"):
    return f'<h3 class="sub-title {cls}">{t}</h3>'

def mk_card(title, source, time, cat, bg, ind, majors, edu, region, tips):
    is_science = (cat == "science")
    tag_bg = "#ebf8ff" if is_science else "#f0fff4"
    tag_fg = "#4299e1" if is_science else "#48bb78"
    tag_text = "\u7406\u5de5\u79d1" if is_science else "\u6587\u79d1"
    sc = "sc" if is_science else "gg"
    
    m_html = "\n".join(f"      <li>{m}</li>" for m in majors)
    e_html = "\n".join(f"      <li>{e}</li>" for e in edu)
    
    return f'''<div class="card {cat}">
  <div class="card-head">
    <h2>{title}</h2>
    <span style="background:{tag_bg};color:{tag_fg};font-size:12px;padding:2px 10px;border-radius:10px;white-space:nowrap;">{tag_text}</span>
  </div>
  <div class="meta"><span>\U0001f4f0 {source}</span><span>\U0001f550 {time}</span></div>
  <div class="content">
    {st("\u4e8b\u4ef6\u80cc\u666f", sc)}
    <p>{bg}</p>
    {st("\u884c\u4e1a\u7b80\u8ff0", sc)}
    <p>{ind}</p>
    {st("\u5173\u8054\u4e13\u4e1a", sc)}
    <ul>
{m_html}
    </ul>
    {st("\u5b66\u5386\u00b7\u5c97\u4f4d\u00b7\u85aa\u8d44", sc)}
    <ul>
{e_html}
    </ul>
    {st("\u5730\u57df\u4f18\u52bf", sc)}
    <p>{region}</p>
    <div class="tip-block">
      <h3>\U0001f4a1 \u62a5\u8003\u5c0f\u8d34\u58eb</h3>
      <p>{tips}</p>
    </div>
  </div>
</div>
'''

def mk_page(issue, date_str, weekday, sci_count, arts_count, points, sci_cards, arts_cards, gen_time):
    pts = "\n".join(f"        <li>{p}</li>" for p in points)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>\u7b2c{issue}\u671f \u00b7 \u9ad8\u987f\u5347\u5b66 \u00b7 \u6bcf\u65e5\u884c\u4e1a\u901f\u89c8</title>
<style>
{COMMON_CSS}
</style>
</head>
<body>
<div class="container">
  <div class="report-header">
    <a href="javascript:void(0)" onclick="showIndex()" style="display:inline-block;margin-bottom:14px;font-size:14px;color:#4299e1;text-decoration:none;font-weight:500;cursor:pointer;">\u2190 \u8fd4\u56de\u5217\u8868</a>
    <div class="date-line">\U0001f4c5 \u7b2c{issue}\u671f \u00b7 \u9ad8\u987f\u5347\u5b66 \u00b7 \u6bcf\u65e5\u884c\u4e1a\u901f\u89c8</div>
    <div class="stats">
      <span>\U0001f4ca \u8d44\u8baf\u5171 {sci_count+arts_count} \u6761</span>
      <span>\U0001f52c \u7406\u5de5\u79d1 {sci_count} \u6761</span>
      <span>\U0001f4da \u6587\u79d1 {arts_count} \u6761</span>
    </div>
    <div class="core-judgments">
      <h3>\U0001f4cc \u4eca\u65e5\u8981\u70b9\u901f\u89c8</h3>
      <ul>
{pts}
      </ul>
    </div>
  </div>

  <div style="margin:20px 0 10px;padding:12px 20px;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,0.04);display:flex;align-items:center;flex-wrap:wrap;">
    <span style="font-size:14px;color:#718096;margin-right:12px;">\u5feb\u901f\u8df3\u8f6c\uff1a</span>
    <a href="javascript:void(0)" onclick="scrollToSection('section-science')" style="margin-right:20px;font-size:15px;color:#2b6cb0;text-decoration:none;font-weight:600;">\U0001f52c \u7406\u5de5\u79d1\u8d44\u8baf</a>
    <a href="javascript:void(0)" onclick="scrollToSection('section-arts')" style="margin-right:20px;font-size:15px;color:#276749;text-decoration:none;font-weight:600;">\U0001f4da \u6587\u79d1\u8d44\u8baf</a>
  </div>

  <div id="section-science" style="display:flex;align-items:center;gap:10px;margin:24px 0 18px;padding:12px 20px;background:linear-gradient(90deg,#ebf8ff,#fff);border-radius:10px;border-left:4px solid #4299e1;">
    <span style="font-size:20px;">\U0001f52c</span>
    <span style="font-size:17px;font-weight:700;color:#2b6cb0;">\u7406\u5de5\u79d1\u8d44\u8baf</span>
    <span style="font-size:13px;color:#718096;margin-left:4px;">\u5171 {sci_count} \u6761</span>
  </div>

{"".join(sci_cards)}

  <div id="section-arts" style="display:flex;align-items:center;gap:10px;margin:30px 0 18px;padding:12px 20px;background:linear-gradient(90deg,#f0fff4,#fff);border-radius:10px;border-left:4px solid #48bb78;">
    <span style="font-size:20px;">\U0001f4da</span>
    <span style="font-size:17px;font-weight:700;color:#276749;">\u6587\u79d1\u8d44\u8baf</span>
    <span style="font-size:13px;color:#718096;margin-left:4px;">\u5171 {arts_count} \u6761</span>
  </div>

{"".join(arts_cards)}

  <div class="footer">
    <p>\u9ad8\u987f\u5347\u5b66 \u00b7 \u6bcf\u65e5\u884c\u4e1a\u901f\u89c8 | \u6570\u636e\u6765\u6e90\u4e8e\u516c\u5f00\u8d44\u8baf\uff0c\u4ec5\u4f9b\u53c2\u8003</p>
    <p>\u85aa\u8d44\u6570\u636e\u6765\u81ea\u516c\u5f00\u62db\u8058\u5e73\u53f0\u53ca\u4f01\u4e1a\u5b98\u65b9\u62ab\u9732\uff0c\u4ec5\u4f9b\u53c2\u8003</p>
    <p>\u751f\u6210\u65f6\u95f4\uff1a{gen_time}</p>
  </div>
</div>
{JS_BLOCK}
</body>
</html>"""

# ===== 学科分类规则（重要！）=====
# 归类为"理工科"的条件（满足任一即可）：
#   1. 资讯标题包含理工科关键词（半导体、芯片、AI、算法、计算机、新能源、生物、航天、机器人等）
#   2. 关联专业中至少有一个专业属于理工科（计算机科学与技术、电子信息工程、自动化、机械工程、
#      材料科学、化学、物理、光电、集成电路、软件工程、人工智能、通信工程等）
# 归类为"文科"的条件（满足任一即可）：
#   1. 资讯标题包含文科关键词（金融、经济、法律、教育、新闻、传媒、市场营销等）
#   2. 关联专业中所有专业都属于文科（金融学、经济学、法学、新闻学、工商管理等）
# 强制规则：
#   如果"关联专业"中包含计算机、电子、自动化、机械、材料、生物、化学、物理等理工科专业，
#   无论标题如何，该资讯都必须归入"理工科"
#   只有"关联专业"全部为文科专业时，才能归入"文科"

def S(title, src, time, bg, ind, majors, edu, region, tips):
    return mk_card(title, src, time, "science", bg, ind, majors, edu, region, tips)

def A(title, src, time, bg, ind, majors, edu, region, tips):
    return mk_card(title, src, time, "arts", bg, ind, majors, edu, region, tips)

print("Template functions defined OK")
