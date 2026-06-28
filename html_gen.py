import os
from config import REPORTS_DIR

TEMPLATE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>گزارش حل سوالات</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Tahoma,sans-serif;background:#f0f2f5;color:#1a1a2e;line-height:1.8;padding:20px}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:30px;border-radius:16px;text-align:center;margin-bottom:30px}
.header h1{font-size:28px;margin-bottom:8px}
.header .stats{display:flex;justify-content:center;gap:40px;margin-top:16px;font-size:15px;opacity:.9}
.stat-box{background:rgba(255,255,255,.1);padding:10px 24px;border-radius:10px}
.stat-box span{font-size:22px;font-weight:bold;display:block}
.card{background:#fff;border-radius:14px;padding:28px;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,.06);border-right:5px solid #1a1a2e;transition:transform .2s}
.card:hover{transform:translateY(-2px)}
.q-title{font-size:13px;color:#888;margin-bottom:6px}
.q-text{font-size:16px;font-weight:bold;color:#1a1a2e;margin-bottom:16px;padding:12px;background:#f8f9fa;border-radius:8px}
.steps{list-style:none;counter-reset:step; padding:0}
.steps li{counter-increment:step;position:relative;padding:10px 16px 10px 48px;margin-bottom:6px;background:#f0f4ff;border-radius:8px;font-size:14px}
.steps li::before{content:counter(step);position:absolute;left:14px;top:10px;width:26px;height:26px;background:#1a1a2e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold}
.answer-box{margin-top:16px;padding:14px 18px;background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border-radius:10px;display:flex;align-items:center;gap:12px}
.answer-label{font-size:13px;color:#2e7d32;font-weight:bold;white-space:nowrap}
.answer-value{font-size:16px;font-weight:bold;color:#1b5e20}
.confidence{display:inline-block;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:bold;margin-top:10px}
.conf-high{background:#e8f5e9;color:#2e7d32}
.conf-mid{background:#fff3e0;color:#e65100}
.conf-low{background:#ffebee;color:#c62828}
.footer{text-align:center;padding:30px;color:#999;font-size:13px}
</style>
</head>
<body>

<div class="header">
  <h1>گزارش حل سوالات امتحانی</h1>
  <div class="stats">
    <div class="stat-box"><span>{{count}}</span>تعداد سوالات</div>
    <div class="stat-box"><span>{{avg_confidence}}%</span>میانگین اطمینان</div>
  </div>
</div>

{% for q in questions %}
<div class="card">
  <div class="q-title">سوال {{q.id}}</div>
  <div class="q-text">{{q.question}}</div>
  <ol class="steps">
    {% for step in q.steps %}
    <li>{{step}}</li>
    {% endfor %}
  </ol>
  <div class="answer-box">
    <span class="answer-label">پاسخ نهایی:</span>
    <span class="answer-value">{{q.final_answer}}</span>
  </div>
  {% if q.confidence >= 70 %}
  <span class="confidence conf-high">اطمینان: {{q.confidence}}%</span>
  {% elif q.confidence >= 40 %}
  <span class="confidence conf-mid">اطمینان: {{q.confidence}}%</span>
  {% else %}
  <span class="confidence conf-low">اطمینان: {{q.confidence}}%</span>
  {% endif %}
</div>
{% endfor %}

<div class="footer">تولید شده توسط Exam Agent</div>

</body>
</html>"""


def render_html(data: dict, filename: str = "report.html") -> str:
    html = TEMPLATE
    html = html.replace("{{count}}", str(data["count"]))
    html = html.replace("{{avg_confidence}}", str(data["average_confidence"]))

    questions_block = ""
    for q in data["questions"]:
        steps_html = ""
        for s in q.get("steps", []):
            steps_html += f"    <li>{s}</li>\n"

        conf = q.get("confidence", 0)
        if conf >= 70:
            conf_class = "conf-high"
        elif conf >= 40:
            conf_class = "conf-mid"
        else:
            conf_class = "conf-low"

        questions_block += f"""<div class="card">
  <div class="q-title">سوال {q['id']}</div>
  <div class="q-text">{q['question']}</div>
  <ol class="steps">
{steps_html}  </ol>
  <div class="answer-box">
    <span class="answer-label">پاسخ نهایی:</span>
    <span class="answer-value">{q['final_answer']}</span>
  </div>
  <span class="confidence {conf_class}">اطمینان: {conf}%</span>
</div>\n"""

    html = html.replace(
        "{% for q in questions %}\n<div class=\"card\">\n  <div class=\"q-title\">سوال {{q.id}}</div>\n  <div class=\"q-text\">{{q.question}}</div>\n  <ol class=\"steps\">\n    {% for step in q.steps %}\n    <li>{{step}}</li>\n    {% endfor %}\n  </ol>\n  <div class=\"answer-box\">\n    <span class=\"answer-label\">پاسخ نهایی:</span>\n    <span class=\"answer-value\">{{q.final_answer}}</span>\n  </div>\n  {% if q.confidence >= 70 %}\n  <span class=\"confidence conf-high\">اطمینان: {{q.confidence}}%</span>\n  {% elif q.confidence >= 40 %}\n  <span class=\"confidence conf-mid\">اطمینان: {{q.confidence}}%</span>\n  {% else %}\n  <span class=\"confidence conf-low\">اطمینان: {{q.confidence}}%</span>\n  {% endif %}\n</div>\n{% endfor %}",
        questions_block.strip(),
    )

    out_path = os.path.join(REPORTS_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path