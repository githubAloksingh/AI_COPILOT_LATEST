import base64
import html
import logging
import math
from typing import Any, Dict, List, Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from app.api.schemas import DesignContext, ScreenComponent, ScreenField, ScreenSpecification, ScreenTable

logger = logging.getLogger(__name__)


class HtmlScreenRenderer:
    WIDTH = 1600
    HEIGHT = 900
    RENDER_TIMEOUT_MS = 30_000

    def render(
        self,
        spec: ScreenSpecification,
        design: DesignContext,
        visual_asset: Optional[bytes] = None,
    ) -> bytes:
        document = self.build_document(spec, design, visual_asset)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(
                        viewport={"width": self.WIDTH, "height": self.HEIGHT},
                        device_scale_factor=1,
                    )
                    page.set_content(document, wait_until="load", timeout=self.RENDER_TIMEOUT_MS)
                    page.evaluate("document.fonts.ready")
                    return page.screenshot(type="png", full_page=True, animations="disabled")
                finally:
                    browser.close()
        except PlaywrightError as exc:
            logger.exception("Chromium failed to render screen %s.", spec.screen_id)
            raise RuntimeError("HTML/CSS rendering failed. Verify Playwright Chromium is installed.") from exc

    def build_document(
        self,
        spec: ScreenSpecification,
        design: DesignContext,
        visual_asset: Optional[bytes] = None,
    ) -> str:
        color = self._color(design.primary_color, "#ef7625")
        surface = self._color(design.surface_color, "#ffffff")
        background = self._color(design.neutral_light, "#fffaf5")
        asset_uri = (
            f"data:image/png;base64,{base64.b64encode(visual_asset).decode('ascii')}"
            if visual_asset
            else ""
        )
        layout = self._layout(spec)
        nav = self._navigation(spec)
        content = self._content(spec)
        brand = html.escape(design.brand_name if design.brand_name != "Enterprise Suite" else "")
        role = f'<span class="role">{self._text(spec.user_role)}</span>' if spec.user_role else ""

        if layout == "login":
            body = (
                f'<main class="login"><aside class="login-art">{self._asset(asset_uri)}'
                f'<span class="brand-mark">{brand or " "}</span><div><small>{self._text(spec.screen_type)}</small>'
                f'<h1>{self._text(spec.name)}</h1><p>{self._text(spec.purpose)}</p></div></aside>'
                f'<section class="login-form"><div class="card">{content}</div></section></main>'
            )
        else:
            body = (
                f'<main class="app {layout}"><header><div class="brand"><span class="brand-mark">'
                f'{brand or " "}</span>{brand}</div><nav>{nav}</nav>{role}</header>'
                f'<section class="heading"><small>SCREEN {spec.sequence:02d} · {self._text(spec.screen_type)}</small>'
                f'<h1>{self._text(spec.name)}</h1><p>{self._text(spec.purpose)}</p></section>'
                f'<section class="workspace">{self._asset(asset_uri)}{content}</section></main>'
            )

        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width={self.WIDTH}, initial-scale=1">
<style>
:root{{--brand:{color};--surface:{surface};--background:{background};--ink:#172033;--muted:#667085;--line:#e7e9ef;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--background);color:var(--ink);font:18px/1.45 Inter,Segoe UI,Arial,sans-serif}}
.app{{width:100%;min-height:100vh;padding:0 56px 52px;background:linear-gradient(140deg,#fff 0%,var(--background) 70%)}}
header{{height:76px;display:flex;align-items:center;gap:40px;border-bottom:1px solid var(--line);background:#ffffffd9}}
.brand{{min-width:190px;display:flex;align-items:center;gap:12px;font-weight:700}}.brand-mark{{width:34px;height:34px;border-radius:11px;background:var(--brand);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:800}}
nav{{display:flex;gap:12px;flex:1;flex-wrap:wrap}} nav span{{padding:8px 12px;border-radius:9px;color:#475467;background:#fff}}nav .active{{color:var(--brand);background:#fff1e6}}
.role{{border:1px solid var(--line);border-radius:20px;padding:7px 12px;color:#475467;font-size:12px}}
.heading{{padding:34px 0 20px}}small,.eyebrow{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--brand);font-weight:700}}
h1,h2,h3,p{{margin-top:0}}h1{{font-size:36px;line-height:1.2;margin:8px 0}}.heading p,.muted{{color:var(--muted);max-width:950px}}
.workspace{{position:relative;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:20px;align-items:start}}
.card,.panel{{position:relative;z-index:1;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:24px;box-shadow:0 12px 32px #1d29390d;grid-column:span 12}}
.dashboard .panel:first-child,.report .panel:first-child{{grid-column:span 12}}.form .panel,.profile .panel{{grid-column:span 10}}.approval .panel,.confirmation .panel{{grid-column:span 10;margin:auto}}
.collection .panel,.document_review .panel{{grid-column:span 12}}.workflow .panel{{grid-column:span 12}}
.panel h2{{font-size:21px;margin-bottom:8px}}.panel>p{{color:var(--muted)}}
.field-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 20px}}.field{{display:flex;flex-direction:column;gap:7px;margin:8px 0}}label{{font-size:15px;font-weight:650}}input,select,textarea{{font:inherit;border:1px solid #d0d5dd;border-radius:9px;padding:12px;background:#fff;color:var(--ink);width:100%}}textarea{{min-height:88px}}
.required{{color:#d92d20}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:13px 15px;border-bottom:1px solid var(--line)}}th{{background:#fff7ed;color:#475467;font-weight:700}}td{{color:#344054}}
.actions{{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}}button{{border:1px solid var(--line);background:#fff;border-radius:9px;padding:11px 18px;font:inherit;color:#344054}}button.primary{{background:var(--brand);color:#fff;border-color:var(--brand);font-weight:650}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;grid-column:span 12}}.stat-card{{display:flex;flex-direction:column;gap:6px;padding:20px 22px;background:var(--surface);border:1px solid var(--line);border-radius:15px;box-shadow:0 10px 24px #1d29390d}}.stat-card strong{{font-size:28px;line-height:1.2}}.stat-card span{{font-size:14px;color:var(--muted)}}
.chart-panel{{grid-column:span 6;min-width:0}}.chart-panel.single-chart{{grid-column:span 12}}.chart-wrap{{width:100%;overflow-x:auto}}.chart-wrap svg{{display:block;width:100%;height:auto;max-height:420px;font-family:Inter,Segoe UI,Arial,sans-serif}}.chart-legend{{font-size:12px;fill:#475467}}.chart-note{{color:var(--muted);font-size:13px;margin:12px 0 0}}.pie-layout{{display:flex;align-items:center;gap:28px;flex-wrap:wrap}}.pie-layout svg{{width:min(230px,40%);min-width:180px;flex:0 0 auto}}.pie-legend{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;flex:1;min-width:230px}}.pie-legend li{{display:flex;gap:10px;align-items:flex-start;min-width:0}}.pie-legend strong,.pie-legend small{{display:block;overflow-wrap:anywhere}}.pie-legend small{{color:var(--muted);margin-top:3px}}.chart-swatch{{width:11px;height:11px;border-radius:4px;flex:0 0 auto;margin-top:4px}}.chart-bars{{display:grid;gap:12px}}.chart-bar-row{{display:grid;grid-template-columns:minmax(120px,1.2fr) minmax(140px,3fr) minmax(65px,.6fr);align-items:center;gap:12px}}.chart-bar-label{{overflow-wrap:anywhere;color:#344054;font-size:14px}}.chart-bar-track{{height:24px;position:relative;background:#f2f4f7;border-radius:6px;overflow:hidden}}.chart-bar-track.diverging{{background:linear-gradient(to right,transparent 49.8%,#98a2b3 49.8%,#98a2b3 50.2%,transparent 50.2%),#f2f4f7}}.chart-bar-fill{{position:absolute;height:100%;top:0;border-radius:6px;background:var(--brand)}}.chart-bar-fill.negative{{background:#b54708}}.chart-bar-fill.positive-only{{left:0}}.chart-bar-value{{font-size:14px;font-weight:650;text-align:right;font-variant-numeric:tabular-nums}}.chart-scale{{display:flex;justify-content:space-between;margin:9px 85px 0 0;color:var(--muted);font-size:12px}}.line-data{{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0;padding:0;list-style:none}}.line-data li{{border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:12px;color:#475467}}.line-data strong{{color:var(--ink);margin-left:6px}}
.fields-panel{{grid-column:span 10}}.table-panel{{grid-column:span 12}}.table-panel table{{font-size:15px}}.workspace>.actions,.workspace>.notice{{grid-column:span 12}}
.notice{{padding:16px 18px;border:1px solid #f5d7bd;background:#fff8f1;border-radius:12px;margin:12px 0}}.rules li{{margin:5px 0}}.asset{{position:absolute;right:0;top:0;width:38%;height:220px;object-fit:cover;opacity:.11;mask-image:linear-gradient(90deg,transparent,#000);pointer-events:none}}
.login{{min-height:100vh;display:grid;grid-template-columns:1fr 1fr;background:#fff}}.login-art{{padding:72px;display:flex;flex-direction:column;justify-content:space-between;background:linear-gradient(145deg,#fff3e7,#fff 70%);position:relative;overflow:hidden}}.login-art .asset{{width:90%;height:70%;opacity:.18}}.login-art>div{{position:relative;max-width:520px}}.login-art h1{{font-size:46px}}.login-art p{{color:var(--muted)}}.login-form{{display:flex;align-items:center;justify-content:center;padding:56px}}.login-form .card{{max-width:600px;width:100%}}
.confirmation .panel{{border-top:4px solid var(--brand)}}.collection .panel{{overflow:hidden}}.workflow .panel{{border-left:4px solid var(--brand)}}.document_review .panel{{background:linear-gradient(110deg,#fff,#fffaf5)}}
@media(max-width:900px){{.chart-panel,.chart-panel.single-chart,.form .panel,.profile .panel,.approval .panel,.confirmation .panel{{grid-column:span 12}}.chart-bar-row{{grid-template-columns:minmax(90px,1fr) minmax(120px,2fr) minmax(55px,.5fr)}}}}
</style></head><body>{body}</body></html>"""

    def _content(self, spec: ScreenSpecification) -> str:
        parts: List[str] = []
        if spec.header_stats:
            stat_items = "".join(
                f'<article class="stat-card"><small>{self._text(item.label)}</small>'
                f'<strong>{self._text(item.value)}</strong>'
                f'{f"<span>{self._text(item.change)}</span>" if item.change else ""}</article>'
                for item in spec.header_stats
            )
            parts.append(f'<section class="stats-grid">{stat_items}</section>')

        seen_fields = set()
        top_level_fields = []
        for field in spec.fields:
            key = field.model_dump_json()
            if key not in seen_fields:
                seen_fields.add(key)
                top_level_fields.append(self._field(field))
        if top_level_fields:
            parts.append(
                '<section class="panel fields-panel"><h2>Fields</h2>'
                '<div class="field-grid">' + "".join(top_level_fields) + "</div></section>"
            )
        chart_count = sum(1 for component in spec.components if component.chart_type)
        for component in spec.components:
            parts.append(self._component(component, seen_fields, single_chart=chart_count == 1))
        for table in spec.tables:
            table_content = self._table(table)
            if table_content:
                parts.append(
                    f'<section class="panel table-panel">'
                    f'{f"<h2>{self._text(table.title)}</h2>" if table.title else ""}'
                    f"{table_content}</section>"
                )
        if spec.business_rules or spec.notifications or spec.interaction and spec.interaction.validation_rules:
            entries = spec.business_rules + spec.notifications
            if spec.interaction:
                entries += spec.interaction.validation_rules
            parts.append(
                '<section class="notice"><strong>Requirements and guidance</strong><ul class="rules">'
                + "".join(f"<li>{self._text(item)}</li>" for item in entries)
                + "</ul></section>"
            )
        if spec.interaction and spec.interaction.navigation_flows:
            flows = "".join(
                f"<li>{self._text(flow.label or flow.from_event)} → "
                f"{self._text(flow.to_screen_id)}"
                f"{' (' + self._text(flow.condition) + ')' if flow.condition else ''}</li>"
                for flow in spec.interaction.navigation_flows
            )
            parts.append(f'<section class="panel"><h2>Navigation flow</h2><ol>{flows}</ol></section>')
        if spec.interaction and spec.interaction.events:
            events = "".join(
                f"<li><strong>{self._text(event.label)}</strong>"
                f"{' — ' + self._text(event.type) if event.type else ''}"
                f"{' · ' + self._text(event.trigger_component) if event.trigger_component else ''}</li>"
                for event in spec.interaction.events
            )
            parts.append(f'<section class="panel"><h2>Available interactions</h2><ul>{events}</ul></section>')
        actions = spec.actions + [
            action for component in spec.components for action in component.actions
        ]
        if actions:
            parts.append(
                '<div class="actions">'
                + "".join(
                    f'<button class="{ "primary" if action.type == "primary" else ""}">'
                    f'{self._text(action.label)}</button>'
                    for action in actions
                )
                + "</div>"
            )
        return "".join(part for part in parts if part)

    def _component(
        self,
        component: ScreenComponent,
        seen_fields: set,
        single_chart: bool = False,
    ) -> str:
        content = []
        chart = self._chart(component)
        if chart:
            content.append(chart)
        for field in component.fields:
            key = field.model_dump_json()
            if key not in seen_fields:
                content.append(self._field(field))
                seen_fields.add(key)
        if component.columns or component.rows:
            content.append(self._table(ScreenTable(columns=component.columns, rows=component.rows)))
        if component.stats:
            content.append(
                '<div class="field-grid">'
                + "".join(
                    f'<div class="notice"><small>{self._text(stat.label)}</small>'
                    f'<h2>{self._text(stat.value)}</h2></div>'
                    for stat in component.stats
                )
                + "</div>"
            )
        if component.steps:
            content.append("<ol>" + "".join(f"<li>{self._text(step)}</li>" for step in component.steps) + "</ol>")
        if component.description:
            content.append(f"<p>{self._text(component.description)}</p>")
        panel_class = "panel"
        if component.chart_type:
            panel_class += " chart-panel"
            if single_chart:
                panel_class += " single-chart"
        return (
            f'<section class="{panel_class}"><small>{self._text(component.type)}</small>'
            f'<h2>{self._text(component.title or component.type)}</h2>'
            + "".join(content)
            + "</section>"
        )

    def _chart(self, component: ScreenComponent) -> str:
        if not component.chart_type:
            return ""
        if not component.chart_data:
            raise ValueError(f"Chart component '{component.title or component.type}' requires chart_data.")

        data = component.chart_data
        if component.chart_type == "pie":
            colors = [
                "#ef7625", "#2f80ed", "#12b76a", "#7a5af8",
                "#f79009", "#06aed4", "#d92d20", "#667085",
            ]
            total = sum(point.value for point in data)
            circumference = 2 * math.pi * 76
            offset = 0.0
            slices = []
            legend = []
            for index, point in enumerate(data):
                length = circumference * point.value / total
                color = colors[index % len(colors)]
                slices.append(
                    f'<circle cx="110" cy="110" r="76" fill="none" stroke="{color}" '
                    f'stroke-width="34" stroke-dasharray="{length:.2f} {circumference - length:.2f}" '
                    f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 110 110)"/>'
                )
                offset += length
                legend.append(
                    f'<li><span class="chart-swatch" style="background:{color}"></span>'
                    f'<span><strong>{self._text(point.label)}</strong>'
                    f'<small>{self._chart_value(point.value, component)} · {point.value / total:.1%}</small></span></li>'
                )
            svg = (
                '<div class="pie-layout"><svg viewBox="0 0 220 220" role="img" aria-label="Pie chart">'
                + "".join(slices)
                + f'<circle cx="110" cy="110" r="52" fill="#fff"/><text x="110" y="106" '
                + 'text-anchor="middle" class="chart-legend">Total</text>'
                + f'<text x="110" y="129" text-anchor="middle" font-size="16" font-weight="700" fill="#172033">{self._text(self._chart_value(total, component))}</text>'
                + f'</svg><ul class="pie-legend">{"".join(legend)}</ul></div>'
            )
        elif component.chart_type == "bar":
            maximum = max((abs(point.value) for point in data), default=0) or 1
            has_negative = any(point.value < 0 for point in data)
            rows = []
            for point in data:
                width = abs(point.value) / maximum * (50 if has_negative else 100)
                direction = "negative" if point.value < 0 else "positive"
                position = f"right:{50 - width:.2f}%" if point.value < 0 and has_negative else (
                    "left:50%" if has_negative else "left:0"
                )
                fill_class = f"chart-bar-fill {direction}" if has_negative else "chart-bar-fill positive-only"
                rows.append(
                    f'<div class="chart-bar-row"><span class="chart-bar-label">{self._text(point.label)}</span>'
                    f'<div class="chart-bar-track{" diverging" if has_negative else ""}" role="img" aria-label="{self._text(point.label)}: '
                    f'{self._text(self._chart_value(point.value, component))}"><span class="{fill_class}" '
                    f'style="{position};width:{width:.2f}%"></span></div>'
                    f'<span class="chart-bar-value">{self._text(self._chart_value(point.value, component))}</span></div>'
                )
            scale = (
                f'<div class="chart-scale"><span>{self._text(self._chart_value(-maximum, component))}</span>'
                f'<span>{self._text(self._chart_value(0, component))}</span>'
                f'<span>{self._text(self._chart_value(maximum, component))}</span></div>'
                if has_negative else
                f'<div class="chart-scale"><span>{self._text(self._chart_value(0, component))}</span>'
                f'<span>{self._text(self._chart_value(maximum, component))}</span></div>'
            )
            svg = f'<div class="chart-bars" role="img" aria-label="Bar chart">{"".join(rows)}</div>{scale}'
        else:
            points = data
            minimum = min(point.value for point in points)
            maximum = max(point.value for point in points)
            if minimum == maximum:
                padding = max(abs(minimum) * 0.1, 1)
                minimum -= padding
                maximum += padding
            spread = maximum - minimum or 1
            width = max(620, (len(points) - 1) * 105 + 70)
            plot_left, plot_right = 48, width - 25
            plot_top, plot_bottom = 30, 200
            plot_height = plot_bottom - plot_top
            x_step = (plot_right - plot_left) / max(1, len(points) - 1)
            coords = [
                (plot_left + index * x_step, plot_bottom - ((point.value - minimum) / spread * plot_height))
                for index, point in enumerate(points)
            ]
            path = " ".join(
                f"{'M' if index == 0 else 'L'} {x:.2f} {y:.2f}"
                for index, (x, y) in enumerate(coords)
            )
            grid = []
            for index in range(5):
                y = plot_top + plot_height * index / 4
                value = maximum - spread * index / 4
                grid.append(
                    f'<line x1="{plot_left}" y1="{y:.2f}" x2="{plot_right}" y2="{y:.2f}" '
                    'stroke="#e7e9ef" stroke-width="1"/>'
                    f'<text x="{plot_left - 8}" y="{y + 4:.2f}" text-anchor="end" '
                    f'class="chart-legend">{self._text(self._chart_value(value, component))}</text>'
                )
            labels = "".join(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#ef7625"/>'
                f'<title>{self._text(points[index].label)}: {self._number(points[index].value)}</title>'
                for index, (x, y) in enumerate(coords)
            )
            category_labels = "".join(
                f'<text x="{x:.2f}" y="222" text-anchor="middle" class="chart-legend">'
                f'<title>{self._text(points[index].label)}</title>'
                f'{self._text(points[index].label[:12])}</text>'
                for index, (x, _) in enumerate(coords)
            )
            svg = (
                f'<svg viewBox="0 0 {width} 240" style="width:{width}px;max-width:none" '
                'role="img" aria-label="Line chart">'
                + "".join(grid)
                + f'<path d="M{plot_left} {plot_top} V{plot_bottom} H{plot_right}" '
                + 'fill="none" stroke="#98a2b3" stroke-width="1"/>'
                +
                f'<path d="{path}" fill="none" stroke="#ef7625" stroke-width="4" '
                f'stroke-linecap="round" stroke-linejoin="round"/>{labels}{category_labels}</svg>'
            )
            svg += '<ul class="line-data">' + "".join(
                f'<li>{self._text(point.label)}<strong>{self._text(self._chart_value(point.value, component))}</strong></li>'
                for point in points
            ) + "</ul>"
        note = f'<p class="chart-note">{self._text(component.chart_note)}</p>' if component.chart_note else ""
        return f'<div class="chart-wrap">{svg}</div>{note}'

    @staticmethod
    def _number(value: float) -> str:
        return f"{value:g}"

    def _chart_value(self, value: float, component: ScreenComponent) -> str:
        prefix = component.chart_value_prefix or ""
        if value < 0 and prefix:
            return f"-{prefix}{self._number(abs(value))}{component.chart_value_suffix or ''}"
        return (
            f"{prefix}"
            f"{self._number(value)}"
            f"{component.chart_value_suffix or ''}"
        )

    def _field(self, field: ScreenField) -> str:
        required = '<span class="required"> *</span>' if field.required else ""
        required_attribute = " required" if field.required else ""
        label = f"<label>{self._text(field.label)}{required}</label>"
        input_type = {
            "email": "email",
            "password": "password",
            "number": "number",
            "date": "date",
        }.get(field.type.casefold(), "text")
        placeholder = self._text(field.placeholder or "")
        value = self._text(field.value or "")
        if field.options:
            options = "".join(
                f'<option value="{self._text(option)}"'
                f'{" selected" if option == field.value else ""}>{self._text(option)}</option>'
                for option in field.options
            )
            control = f"<select{required_attribute}>{options}</select>"
        elif field.type.casefold() == "textarea":
            control = (
                f'<textarea placeholder="{placeholder}"{required_attribute}>'
                f"{value}</textarea>"
            )
        else:
            control = (
                f'<input type="{input_type}" placeholder="{placeholder}" '
                f'value="{value}"{required_attribute}>'
            )
        return f'<div class="field">{label}{control}</div>'

    def _table(self, table: ScreenTable) -> str:
        columns = table.columns or (list(table.rows[0].keys()) if table.rows else [])
        if not columns:
            return ""
        headers = "".join(f"<th>{self._text(column)}</th>" for column in columns)
        rows = []
        for row in table.rows:
            cells = "".join(f"<td>{self._text(row.get(column, ''))}</td>" for column in columns)
            rows.append(f"<tr>{cells}</tr>")
        return f'<div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'

    def _navigation(self, spec: ScreenSpecification) -> str:
        context = spec.navigation_context if isinstance(spec.navigation_context, dict) else {}
        items = context.get("navigation_items", [])
        if not isinstance(items, list):
            return ""
        active = str(context.get("active_nav_item") or spec.name)
        labels = []
        for item in items:
            label = str(item.get("label") or item.get("name") or "") if isinstance(item, dict) else str(item)
            if label:
                state = "active" if label.casefold() == active.casefold() else ""
                labels.append(f'<span class="{state}">{self._text(label)}</span>')
        return "".join(labels)

    @staticmethod
    def _layout(spec: ScreenSpecification) -> str:
        screen_type = spec.screen_type.casefold().replace("-", "_")
        if any(token in screen_type for token in ("login", "auth", "sign_in")):
            return "login"
        if any(token in screen_type for token in ("confirm", "receipt", "success")):
            return "confirmation"
        if any(token in screen_type for token in ("approval", "decision")):
            return "approval"
        if any(token in screen_type for token in ("report", "analytics")):
            return "report"
        if any(token in screen_type for token in ("queue", "list", "search", "history", "audit", "collection")):
            return "collection"
        if any(token in screen_type for token in ("workflow", "wizard")):
            return "workflow"
        if any(token in screen_type for token in ("document", "viewer")):
            return "document_review"
        if "profile" in screen_type:
            return "profile"
        if "dashboard" in screen_type or "overview" in screen_type:
            return "dashboard"
        if "form" in screen_type or spec.fields or any(component.fields for component in spec.components):
            return "form"
        return "detail"

    @staticmethod
    def _asset(data_uri: str) -> str:
        return f'<img class="asset" src="{data_uri}" alt="" aria-hidden="true">' if data_uri else ""

    @staticmethod
    def _text(value: Any) -> str:
        return html.escape(str(value)) if value is not None else ""

    @staticmethod
    def _color(value: Optional[str], fallback: str) -> str:
        if isinstance(value, str) and len(value) in (4, 7) and value.startswith("#"):
            if all(char in "0123456789abcdefABCDEF" for char in value[1:]):
                return value
        return fallback


html_screen_renderer = HtmlScreenRenderer()
