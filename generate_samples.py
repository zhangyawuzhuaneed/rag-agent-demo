import platform
from pathlib import Path
from fpdf import FPDF
from docx import Document

DATA = Path("./data")
DATA.mkdir(exist_ok=True)

def get_font_path():
    sys_os = platform.system()
    if sys_os == "Windows":
        return "C:/Windows/Fonts/simhei.ttf"
    elif sys_os == "Darwin":
        return "/System/Library/Fonts/PingFang.ttc"
    else:
        return "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

FONT = get_font_path()

def pdf(name, title, sections):
    p = FPDF()
    p.add_page()
    p.add_font("SimHei", "", FONT)
    p.set_font("SimHei", size=16)
    p.set_margins(left=10, right=10, top=10) # 设置边距
    p.multi_cell(0, 10, title)
    p.ln(4)
    for h, b in sections:
        p.set_font("SimHei", size=13)
        p.multi_cell(0, 8, h)
        p.set_font("SimHei", size=10)
        p.multi_cell(w=180, h=6, txt=b)
        p.ln(4)
    p.output(str(DATA / name))
    print(f"✅ {name}")


def docx(name, title, sections):
    d = Document()
    d.add_heading(title, 0)
    for h, b in sections:
        d.add_heading(h, 1)
        d.add_paragraph(b)
    d.save(str(DATA / name))
    print(f"✅ {name}")


pdf("扫地机器人用户手册.pdf", "智扫通 X1 用户手册", [
    ("产品参数", "型号 X1，吸力 5000Pa，尘盒 400ml，续航约 180 分钟。适用木地板、瓷砖、短毛地毯。"),
    ("日常维护", "尘盒每 3 天清理一次。主刷每两周清理毛发。滤网不可水洗，每 3 个月更换。"),
    ("常见故障", "提示轮子悬空：检查是否卡在门槛或线缆上，放回平地重启。湿度超 80% 建议关闭拖地。"),
])

docx("服装售后FAQ.docx", "服装电商售后", [
    ("退货", "签收后 7 天内无理由退货，吊牌需完整、未洗涤。退款 3 个工作日内原路返回。"),
    ("换货", "签收后 15 天内可换货，来回运费由用户承担，质量问题除外。"),
])

(DATA / "综合知识.txt").write_text(
    "会员积分：每消费 1 元累计 1 积分，100 积分抵扣 1 元，有效期 12 个月。\n"
    "顶级会员：每消费 1 元累计 1000 积分，免费赠送鸡蛋大米各一斤。\n"
    "客服时间：每天 9:00-21:00。\n",
    encoding="utf-8",
)
print("✅ 综合知识.txt")
