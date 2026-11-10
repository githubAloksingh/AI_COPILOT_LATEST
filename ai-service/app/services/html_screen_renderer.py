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
    ICONS = {
        "home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
        "chart": '<path d="M4 19V5m0 14h17"/><path d="m7 15 4-4 3 2 6-7"/>',
        "users": '<circle cx="9" cy="8" r="3"/><path d="M3 20v-1a6 6 0 0 1 12 0v1z"/><path d="M16 5.2a3 3 0 0 1 0 5.6M18 14a5 5 0 0 1 3 4.6"/>',
        "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
        "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
        "file": '<path d="M6 3h8l5 5v13H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M14 3v6h6M8 14h8M8 18h8"/>',
        "check": '<path d="m5 12 4 4L19 6"/>',
        "arrow-right": '<path d="M4 12h15m-6-6 6 6-6 6"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
        "filter": '<path d="M4 6h16M7 12h10m-7 6h4"/>',
        "settings": '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.8-.7a8 8 0 0 1-1.6.9l-.3 1.9h-2.8l-.3-1.9a8 8 0 0 1-1.6-.9l-1.8.7-1.4-2.4 1.5-1.2a7 7 0 0 1 0-1.8l-1.5-1.2 1.4-2.4 1.8.7a8 8 0 0 1 1.6-.9l.3-1.9h2.8l.3 1.9a8 8 0 0 1 1.6.9l1.8-.7 1.4 2.4-1.5 1.2a7 7 0 0 1 0 1.8z"/>',
        "shield": '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11z"/><path d="m9 12 2 2 4-4"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        "trend-up": '<path d="m3 17 6-6 4 4 8-9m-6 0h6v6"/>',
        "wallet": '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 9h18m-5 5h2"/>',
        "bell": '<path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-8 12h4"/>',
        "lock": '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
        "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
        "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18m0-18a15 15 0 0 0 0 18"/>',
        "briefcase": '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4h8v3M3 12h18m-11 0v2h4v-2"/>',
        "heart": '<path d="M20.8 8.6c0 4.5-8.8 10.1-8.8 10.1S3.2 13.1 3.2 8.6a4.6 4.6 0 0 1 8.8-1.8 4.6 4.6 0 0 1 8.8 1.8z"/>',
        "box": '<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="M3 8v9l9 5 9-5V8m-9 5v9"/>',
        "truck": '<path d="M3 6h11v12H3zM14 10h4l3 4v4h-7"/><circle cx="7" cy="19" r="2"/><circle cx="18" cy="19" r="2"/>',
        "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1M8 10h8m-8 4h8m-8 4h5"/>',
        "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
        "refresh": '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 9A7 7 0 0 1 18 6l2 2M4 16l2 2a7 7 0 0 0 12.5-3"/>',
        "alert": '<path d="M12 3 2.8 19h18.4L12 3z"/><path d="M12 9v4m0 3h.01"/>',
    }

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
        content = self._content(spec, layout, asset_uri)
        asset_embedded_in_panel = bool(spec.fields) or (
            bool(spec.components)
            and layout in {"dashboard", "report", "form", "profile", "detail", "approval", "confirmation"}
        )
        brand = html.escape(design.brand_name if design.brand_name != "Enterprise Suite" else "")
        role = f'<span class="role">{self._text(spec.user_role)}</span>' if spec.user_role else ""
        brand_icon = self._icon("globe", "brand-icon")

        if layout == "login":
            body = (
                f'<main class="login"><aside class="login-art">{self._asset(asset_uri)}'
                f'<div class="login-brand"><span class="brand-mark">{brand_icon}</span>'
                f'<strong>{brand or " "}</strong></div><div class="login-welcome">'
                f'<span class="illustration-badge" aria-hidden="true">{self._icon("shield")}</span>'
                f'<small>{self._text(spec.screen_type)}</small>'
                f'<h1>{self._text(spec.name)}</h1><p>{self._text(spec.purpose)}</p></div></aside>'
                f'<section class="login-form"><div class="card">{content}</div></section></main>'
            )
        else:
            body = (
                f'<main class="app {layout}"><header><div class="brand"><span class="brand-mark">'
                f'{brand_icon}</span>{brand}</div><nav>{nav}</nav>{role}</header>'
                f'<section class="heading"><small>SCREEN {spec.sequence:02d} · {self._text(spec.screen_type)}</small>'
                f'<h1>{self._text(spec.name)}</h1><p>{self._text(spec.purpose)}</p></section>'
                f'<section class="workspace">{content}'
                f'{self._asset(asset_uri) if not asset_embedded_in_panel else ""}'
                f'</section></main>'
            )

        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--brand:{color};--surface:{surface};--background:{background};--ink:#172033;--muted:#667085;--line:#e7e9ef;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--background);color:var(--ink);font:18px/1.45 Inter,Segoe UI,Arial,sans-serif}}
.app{{width:100%;min-height:100vh;padding:0 56px 52px;background:linear-gradient(140deg,#fff 0%,var(--background) 70%)}}
header{{height:76px;display:flex;align-items:center;gap:40px;border-bottom:1px solid var(--line);background:#ffffffd9}}
.brand{{min-width:190px;display:flex;align-items:center;gap:12px;font-weight:700}}.brand-mark{{width:34px;height:34px;border-radius:11px;background:var(--brand);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:800}}.brand-mark svg{{width:19px;height:19px}}
nav{{display:flex;gap:12px;flex:1;flex-wrap:wrap}} nav span{{display:inline-flex;align-items:center;gap:7px;padding:8px 12px;border-radius:9px;color:#475467;background:#fff}}nav .active{{color:var(--brand);background:#fff1e6}}nav .icon{{width:16px;height:16px}}
.role{{border:1px solid var(--line);border-radius:20px;padding:7px 12px;color:#475467;font-size:12px}}
.heading{{padding:34px 0 20px}}small,.eyebrow{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--brand);font-weight:700}}
h1,h2,h3,p{{margin-top:0}}h1{{font-size:36px;line-height:1.2;margin:8px 0}}.heading p,.muted{{color:var(--muted);max-width:950px}}
.workspace{{position:relative;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:20px;align-items:start}}
.card,.panel{{position:relative;z-index:1;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:24px;box-shadow:0 12px 32px #1d29390d;grid-column:span 12}}.panel-art{{position:absolute;z-index:0;right:18px;top:14px;width:126px;height:88px;object-fit:cover;opacity:.20;mask-image:radial-gradient(ellipse,#000 20%,transparent 78%);pointer-events:none}}.panel>*:not(.panel-art){{position:relative;z-index:1}}
.dashboard .panel:first-child,.report .panel:first-child{{grid-column:span 12}}.form .panel,.profile .panel{{grid-column:span 10}}.approval .panel,.confirmation .panel{{grid-column:span 10;margin:auto}}
.collection .panel,.document_review .panel{{grid-column:span 12}}.workflow .panel{{grid-column:span 12}}
.panel h2{{font-size:21px;margin-bottom:8px}}.panel>p{{color:var(--muted)}}
.field-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 20px}}.field{{display:flex;flex-direction:column;gap:7px;margin:8px 0}}label{{font-size:15px;font-weight:650}}input,select,textarea{{font:inherit;border:1px solid #d0d5dd;border-radius:9px;padding:12px;background:#fff;color:var(--ink);width:100%}}textarea{{min-height:88px}}
.required{{color:#d92d20}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:13px 15px;border-bottom:1px solid var(--line)}}th{{background:#fff7ed;color:#475467;font-weight:700}}td{{color:#344054}}
.actions{{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}}button{{display:inline-flex;align-items:center;justify-content:center;gap:9px;border:1px solid var(--line);background:#fff;border-radius:9px;padding:11px 18px;font:inherit;color:#344054}}button.primary{{background:var(--brand);color:#fff;border-color:var(--brand);font-weight:650}}.icon{{width:18px;height:18px;display:inline-block;vertical-align:middle;flex:0 0 auto}}.brand-icon{{width:20px;height:20px}}.field-label{{display:flex;align-items:center;gap:8px}}.field-label .icon{{color:var(--brand)}}.panel-title{{display:flex;align-items:center;gap:10px}}.panel-title .icon{{color:var(--brand)}}.stat-top{{display:flex;justify-content:space-between;align-items:center}}.stat-icon{{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:#fff3e7;color:var(--brand)}}.stat-icon .icon{{width:20px;height:20px}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;grid-column:span 12}}.stat-card{{display:flex;flex-direction:column;gap:8px;padding:20px 22px;background:var(--surface);border:1px solid var(--line);border-radius:15px;box-shadow:0 10px 24px #1d29390d}}.stat-card strong{{font-size:28px;line-height:1.2}}.stat-card span{{font-size:14px;color:var(--muted)}}
.progress-block{{margin:12px 0 4px}}.progress-meta{{display:flex;justify-content:space-between;gap:12px;margin-bottom:8px;color:#475467;font-size:14px}}.progress-track{{height:10px;background:#f2f4f7;border-radius:99px;overflow:hidden}}.progress-fill{{height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--brand),#f5a623)}}.progress-footnote{{margin:8px 0 0;color:var(--muted);font-size:12px}}
.chart-panel{{grid-column:span 6;min-width:0}}.chart-panel.single-chart{{grid-column:span 12}}.chart-wrap{{width:100%;overflow-x:auto}}.chart-wrap svg{{display:block;width:100%;height:auto;max-height:420px;font-family:Inter,Segoe UI,Arial,sans-serif}}.chart-legend{{font-size:12px;fill:#475467}}.chart-note{{color:var(--muted);font-size:13px;margin:12px 0 0}}.pie-layout{{display:flex;align-items:center;gap:28px;flex-wrap:wrap}}.pie-layout svg{{width:min(230px,40%);min-width:180px;flex:0 0 auto}}.pie-legend{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;flex:1;min-width:230px}}.pie-legend li{{display:flex;gap:10px;align-items:flex-start;min-width:0}}.pie-legend strong,.pie-legend small{{display:block;overflow-wrap:anywhere}}.pie-legend small{{color:var(--muted);margin-top:3px}}.chart-swatch{{width:11px;height:11px;border-radius:4px;flex:0 0 auto;margin-top:4px}}.chart-bars{{display:grid;gap:12px}}.chart-bar-row{{display:grid;grid-template-columns:minmax(120px,1.2fr) minmax(140px,3fr) minmax(65px,.6fr);align-items:center;gap:12px}}.chart-bar-label{{overflow-wrap:anywhere;color:#344054;font-size:14px}}.chart-bar-track{{height:24px;position:relative;background:#f2f4f7;border-radius:6px;overflow:hidden}}.chart-bar-track.diverging{{background:linear-gradient(to right,transparent 49.8%,#98a2b3 49.8%,#98a2b3 50.2%,transparent 50.2%),#f2f4f7}}.chart-bar-fill{{position:absolute;height:100%;top:0;border-radius:6px;background:var(--brand)}}.chart-bar-fill.negative{{background:#b54708}}.chart-bar-fill.positive-only{{left:0}}.chart-bar-value{{font-size:14px;font-weight:650;text-align:right;font-variant-numeric:tabular-nums}}.chart-scale{{display:flex;justify-content:space-between;margin:9px 85px 0 0;color:var(--muted);font-size:12px}}.line-data{{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0;padding:0;list-style:none}}.line-data li{{border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:12px;color:#475467}}.line-data strong{{color:var(--ink);margin-left:6px}}
.fields-panel{{grid-column:span 10}}.table-panel{{grid-column:span 12}}.table-panel table{{font-size:15px}}.workspace>.actions,.workspace>.notice{{grid-column:span 12}}
.notice{{padding:16px 18px;border:1px solid #f5d7bd;background:#fff8f1;border-radius:12px;margin:12px 0}}.rules li{{margin:5px 0}}.asset{{position:absolute;right:0;top:0;width:38%;height:220px;object-fit:cover;opacity:.11;mask-image:linear-gradient(90deg,transparent,#000);pointer-events:none}}
.login{{min-height:100vh;display:grid;grid-template-columns:1fr 1fr;background:#fff}}.login-art{{padding:72px;display:flex;flex-direction:column;justify-content:space-between;background:linear-gradient(145deg,#fff3e7,#fff 70%);position:relative;overflow:hidden}}.login-art .asset{{width:100%;height:100%;opacity:.30;mask-image:linear-gradient(90deg,transparent 4%,#000 85%)}}.login-brand{{position:relative;z-index:1;display:flex;align-items:center;gap:12px;font-weight:700}}.login-welcome{{position:relative;z-index:1;max-width:520px}}.illustration-badge{{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;border:1px solid #f5d7bd;background:#ffffffc9;border-radius:14px;color:#475467;margin-bottom:18px}}.illustration-badge .icon{{color:var(--brand)}}.login-welcome h1{{font-size:46px}}.login-welcome p{{color:var(--muted)}}.login-form{{display:flex;align-items:center;justify-content:center;padding:56px}}.login-form .card{{max-width:600px;width:100%}}
.confirmation .panel{{border-top:4px solid var(--brand)}}.collection .panel{{overflow:hidden}}.workflow .panel{{border-left:4px solid var(--brand)}}.document_review .panel{{background:linear-gradient(110deg,#fff,#fffaf5)}}
@media(max-width:900px){{.chart-panel,.chart-panel.single-chart,.form .panel,.profile .panel,.approval .panel,.confirmation .panel{{grid-column:span 12}}.chart-bar-row{{grid-template-columns:minmax(90px,1fr) minmax(120px,2fr) minmax(55px,.5fr)}}}}
</style></head><body>{body}</body></html>"""

    def _content(self, spec: ScreenSpecification, layout: str, asset_uri: str) -> str:
        parts: List[str] = []
        if spec.header_stats:
            stat_items = "".join(
                f'<article class="stat-card"><small>{self._text(item.label)}</small>'
                f'{f"<div class=stat-icon>{self._icon(item.icon)}</div>" if item.icon else ""}'
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
                '<section class="panel fields-panel">'
                f'{self._asset(asset_uri, "panel-art") if asset_uri else ""}'
                '<h2>Fields</h2>'
                '<div class="field-grid">' + "".join(top_level_fields) + "</div></section>"
            )
        chart_count = sum(1 for component in spec.components if component.chart_type)
        asset_attached = bool(top_level_fields)
        for component in spec.components:
            use_asset = (
                bool(asset_uri)
                and not asset_attached
                and layout in {"dashboard", "report", "form", "profile", "detail", "approval", "confirmation"}
            )
            parts.append(
                self._component(
                    component,
                    seen_fields,
                    single_chart=chart_count == 1,
                    decorative_asset=self._asset(asset_uri, "panel-art") if use_asset else "",
                )
            )
            asset_attached = asset_attached or use_asset
        for table in spec.tables:
            table_content = self._table(table)
            if table_content:
                parts.append(
                    f'<section class="panel table-panel">'
                    f'{f"<h2>{self._text(table.title)}</h2>" if table.title else ""}'
                    f"{table_content}</section>"
                )
        actions = spec.actions + [
            action for component in spec.components for action in component.actions
        ]
        if actions:
            parts.append(
                '<div class="actions">'
                + "".join(
                    f'<button class="{ "primary" if action.type == "primary" else ""}">'
                    f'{self._icon(action.icon)}{self._text(action.label)}</button>'
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
        decorative_asset: str = "",
    ) -> str:
        content = []
        chart = self._chart(component)
        if chart:
            content.append(chart)
        if component.progress_value is not None:
            label = self._text(component.progress_label or component.title or "Progress")
            note = (
                f'<p class="progress-footnote">{self._text(component.progress_note)}</p>'
                if component.progress_note
                else ""
            )
            content.append(
                f'<div class="progress-block" role="group" aria-label="{label}">'
                f'<div class="progress-meta"><span>{label}</span>'
                f'<strong>{component.progress_value:g}%</strong></div>'
                f'<div class="progress-track" role="progressbar" aria-label="{label}" '
                f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{component.progress_value:g}">'
                f'<div class="progress-fill" style="width:{component.progress_value:g}%"></div></div>{note}</div>'
            )
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
                    f'{self._icon(stat.icon, "stat-icon") if stat.icon else ""}'
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
            f'{decorative_asset}'
            f'<h2 class="panel-title">{self._icon(component.icon)}'
            f'{self._text(component.title or component.type)}</h2>'
            + "".join(content)
            + "</section>"
        )

    def _chart(self, component: ScreenComponent) -> str:
        if not component.chart_type:
            return ""
        if not component.chart_data:
            raise ValueError(f"Chart component '{component.title or component.type}' requires chart_data.")

        data = component.chart_data
        if component.chart_type in {"pie", "donut"}:
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
                f'<div class="pie-layout"><svg viewBox="0 0 220 220" role="img" aria-label="{component.chart_type.title()} chart">'
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
        label = (
            f'<label class="field-label">{self._icon(field.icon)}'
            f'{self._text(field.label)}{required}</label>'
        )
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
                icon = self._icon(item.get("icon")) if isinstance(item, dict) else ""
                labels.append(f'<span class="{state}">{icon}{self._text(label)}</span>')
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
    def _asset(data_uri: str, class_name: str = "asset") -> str:
        return (
            f'<img class="{html.escape(class_name, quote=True)}" src="{data_uri}" alt="" aria-hidden="true">'
            if data_uri
            else ""
        )

    @staticmethod
    def _text(value: Any) -> str:
        return html.escape(str(value)) if value is not None else ""

    @classmethod
    def _icon(cls, name: Optional[str], extra_class: str = "icon") -> str:
        normalized = str(name or "").strip().casefold().replace("_", "-")
        paths = cls.ICONS.get(normalized)
        if not paths:
            return ""
        return (
            f'<svg class="{html.escape(extra_class, quote=True)}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
        )

    @staticmethod
    def _color(value: Optional[str], fallback: str) -> str:
        if isinstance(value, str) and len(value) in (4, 7) and value.startswith("#"):
            if all(char in "0123456789abcdefABCDEF" for char in value[1:]):
                return value
        return fallback


html_screen_renderer = HtmlScreenRenderer()
