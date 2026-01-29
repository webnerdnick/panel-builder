import re
import xml.etree.ElementTree as ET

from flask import Flask, render_template, request, make_response

app = Flask(__name__)


def clamp_panel_size(value, default=40):
    if not str(value).isdigit():
        return default
    size = int(value)
    size = max(8, min(40, size))
    if size % 2 != 0:
        size += 1
        size = min(40, size)
    return size


@app.route("/", methods=["GET", "POST"])
def index():
    panel_size = 40
    panel_size_selected = False
    slots = [{"a": "", "b": ""} for _ in range(panel_size)]
    title = ""
    if request.method == "POST":
        change_size = request.form.get("change_size") == "1"
        panel_size = clamp_panel_size(request.form.get("panel_size", "40"))
        panel_size_selected = True
        slots = [{"a": "", "b": ""} for _ in range(panel_size)]
        title = request.form.get("title", "").strip()
        if change_size:
            prev_size = clamp_panel_size(request.form.get("prev_size", panel_size))
            carry_count = min(prev_size, panel_size)
        else:
            carry_count = panel_size
        for i in range(carry_count):
            number = i + 1
            slots[i]["a"] = request.form.get(f"slot_{number}_a", "").strip()
            slots[i]["b"] = request.form.get(f"slot_{number}_b", "").strip()
    left = [(i + 1, slots[i]) for i in range(0, panel_size, 2)]
    right = [(i + 1, slots[i]) for i in range(1, panel_size, 2)]
    show_preview_hint = request.method == "POST" and not request.form.get("change_size") == "1"
    return render_template(
        "index.html",
        title=title,
        left=left,
        right=right,
        slots=slots,
        show_preview_hint=show_preview_hint,
        panel_size=panel_size,
        panel_size_selected=panel_size_selected,
    )


@app.route("/export", methods=["POST"])
def export_schedule():
    title = request.form.get("title", "").strip()
    panel_size = clamp_panel_size(request.form.get("panel_size", "40"))
    slots = []
    for i in range(panel_size):
        number = i + 1
        slots.append(
            {
                "number": number,
                "a": request.form.get(f"slot_{number}_a", "").strip(),
                "b": request.form.get(f"slot_{number}_b", "").strip(),
            }
        )

    root = ET.Element("panelSchedule")
    if title:
        root.set("title", title)
    root.set("size", str(panel_size))
    for slot in slots:
        slot_el = ET.SubElement(
            root,
            "slot",
            {
                "number": str(slot["number"]),
                "tandem": "true" if slot["b"] else "false",
            },
        )
        breaker_a = ET.SubElement(slot_el, "breaker", {"index": "1"})
        breaker_a.text = slot["a"]
        breaker_b = ET.SubElement(slot_el, "breaker", {"index": "2"})
        breaker_b.text = slot["b"]

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "-", title).strip("-").lower()
    filename = f"{safe_title or 'panel-schedule'}.xml"
    response = make_response(xml_bytes)
    response.headers["Content-Type"] = "application/xml"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.route("/import", methods=["POST"])
def import_schedule():
    title = ""
    panel_size = 40
    slots = [{"a": "", "b": ""} for _ in range(panel_size)]
    upload = request.files.get("schedule_file")
    if upload and upload.filename:
        try:
            tree = ET.parse(upload.stream)
            root = tree.getroot()
            title = root.get("title", "").strip()
            panel_size = clamp_panel_size(root.get("size", "40"))
            slots = [{"a": "", "b": ""} for _ in range(panel_size)]
            for slot_el in root.findall("slot"):
                number_str = slot_el.get("number", "")
                if not number_str.isdigit():
                    continue
                number = int(number_str)
                if not 1 <= number <= panel_size:
                    continue
                slot = slots[number - 1]
                breakers = slot_el.findall("breaker")
                if len(breakers) >= 1 and breakers[0].text:
                    slot["a"] = breakers[0].text.strip()
                if len(breakers) >= 2 and breakers[1].text:
                    slot["b"] = breakers[1].text.strip()
        except ET.ParseError:
            pass

    left = [(i + 1, slots[i]) for i in range(0, panel_size, 2)]
    right = [(i + 1, slots[i]) for i in range(1, panel_size, 2)]
    return render_template(
        "index.html",
        title=title,
        left=left,
        right=right,
        slots=slots,
        show_preview_hint=True,
        panel_size=panel_size,
        panel_size_selected=True,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
