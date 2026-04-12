"""
TradingView Advanced Chart — yüzen PiP benzeri pencere (sürükle, yeniden boyutlandır, üstte tut).
Widget: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import webview
from webview.window import FixPoint

_LAUNCH_CFG: dict[str, Any] = {}

_FIX_NW = FixPoint.NORTH | FixPoint.WEST


def _split_total(total: int, parts: int) -> list[int]:
    if parts <= 0:
        return []
    base = total // parts
    rem = total % parts
    return [base + (1 if i < rem else 0) for i in range(parts)]


def _primary_work_area() -> tuple[int, int, int, int]:
    """Birincil ekranın çalışma alanı (x, y, genişlik, yükseklik)."""
    if sys.platform == "win32":
        class _RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        r = _RECT()
        SPI_GETWORKAREA = 48
        if ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETWORKAREA, 0, ctypes.byref(r), 0
        ):
            return (r.left, r.top, r.right - r.left, r.bottom - r.top)
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        return (0, 0, w, h)
    except Exception:
        return (0, 0, 1920, 1080)


def _work_area_for_window(ref: webview.Window | None) -> tuple[int, int, int, int]:
    """Pencerenin üzerinde bulunduğu monitörün çalışma alanı (çoklu ekran)."""
    if sys.platform != "win32":
        return _primary_work_area()

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class _POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class _MONITORINFOEX(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", _RECT),
            ("rcWork", _RECT),
            ("dwFlags", ctypes.c_ulong),
            ("szDevice", ctypes.c_wchar * 32),
        ]

    cx, cy = 0, 0
    if ref is not None:
        try:
            cx = ref.x + max(ref.width, 1) // 2
            cy = ref.y + max(ref.height, 1) // 2
        except Exception:
            pass

    MONITOR_DEFAULTTONEAREST = 2
    pt = _POINT(cx, cy)
    hmon = ctypes.windll.user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    if not hmon:
        return _primary_work_area()

    mi = _MONITORINFOEX()
    mi.cbSize = ctypes.sizeof(_MONITORINFOEX)
    if not ctypes.windll.user32.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(mi)):
        return _primary_work_area()

    rw = mi.rcWork
    return (rw.left, rw.top, rw.right - rw.left, rw.bottom - rw.top)


def _place_window(win: webview.Window, x: int, y: int, w: int, h: int) -> None:
    w = max(win.min_size[0], int(w))
    h = max(win.min_size[1], int(h))
    win.move(int(x), int(y))
    win.resize(w, h, _FIX_NW)


def apply_workspace_layout(mode: int, reference: webview.Window | None = None) -> None:
    """Açık grafik pencerelerini çalışma alanına göre döşer.

    ``reference``: Düzen menüsüne tıklanan pencere; hangi monitörde
    döşeneceğini bu pencerenin konumu belirler (ikinci ekrandaysa orası).

    Modlar: 1 = sol|sağ (2), 2 = üst sol/sağ + alt (3), 3 = dört köşe (4),
    4 = üst|alt (2).
    """
    wins = list(webview.windows)
    if not wins:
        return
    wx, wy, ww, wh = _work_area_for_window(reference)
    if len(wins) == 1:
        _place_window(wins[0], wx, wy, ww, wh)
        return

    m = int(mode)
    if m == 1:
        col_w = _split_total(ww, 2)
        rects = [
            (wx, wy, col_w[0], wh),
            (wx + col_w[0], wy, col_w[1], wh),
        ]
    elif m == 2:
        row_h = _split_total(wh, 2)
        col_w = _split_total(ww, 2)
        h_top = row_h[0]
        h_bot = row_h[1]
        rects = [
            (wx, wy, col_w[0], h_top),
            (wx + col_w[0], wy, col_w[1], h_top),
            (wx, wy + h_top, ww, h_bot),
        ]
    elif m == 3:
        col_w = _split_total(ww, 2)
        row_h = _split_total(wh, 2)
        w_l, w_r = col_w[0], col_w[1]
        h_t, h_b = row_h[0], row_h[1]
        quads = {
            "LT": (wx, wy, w_l, h_t),
            "RT": (wx + w_l, wy, w_r, h_t),
            "LB": (wx, wy + h_t, w_l, h_b),
            "RB": (wx + w_l, wy + h_t, w_r, h_b),
        }
        # Kullanıcı sırası: sağ üst, sağ alt, sol üst, sol alt
        rects = [quads[k] for k in ("RT", "RB", "LT", "LB")]
    elif m == 4:
        row_h = _split_total(wh, 2)
        rects = [
            (wx, wy, ww, row_h[0]),
            (wx, wy + row_h[0], ww, row_h[1]),
        ]
    else:
        return

    n = min(len(wins), len(rects))
    for i in range(n):
        x, y, w, h = rects[i]
        _place_window(wins[i], x, y, w, h)


def _bundle_dir() -> Path:
    """PyInstaller: şablon ve paket verileri (genelde sys._MEIPASS)."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _writable_dir() -> Path:
    """WebView profili vb.; exe yanında yazılabilir klasör."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _widget_embed_config(
    *,
    symbol: str,
    interval: str,
    timezone: str,
    theme: str,
    locale: str,
) -> dict[str, Any]:
    background = (
        "rgba(21, 24, 37, 1)" if theme == "dark" else "rgba(255, 255, 255, 1)"
    )
    return {
        "allow_symbol_change": True,
        "calendar": False,
        "details": False,
        "hide_side_toolbar": True,
        "hide_top_toolbar": False,
        "hide_legend": True,
        "hide_volume": True,
        "hotlist": False,
        "interval": interval,
        "locale": locale,
        "save_image": False,
        "style": "1",
        "symbol": symbol,
        "theme": theme,
        "timezone": timezone,
        "backgroundColor": background,
        "gridColor": "rgba(255, 255, 255, 0)",
        "watchlist": [],
        "withdateranges": False,
        "compareSymbols": [],
        "studies": ["STD;RSI"],
        "autosize": True,
    }


def build_html(
    template: str,
    *,
    symbol: str,
    interval: str,
    timezone: str,
    theme: str,
    locale: str,
) -> str:
    cfg = _widget_embed_config(
        symbol=symbol,
        interval=interval,
        timezone=timezone,
        theme=theme,
        locale=locale,
    )
    widget_json = json.dumps(cfg, indent=2, ensure_ascii=False)
    out = template
    out = out.replace("__WIDGET_CONFIG_JSON__", widget_json)
    out = out.replace("__THEME__", theme)
    return out


class WidgetApi:
    """pywebview JS API — kapat ve çerçevesiz pencerede yeniden boyutlandır.

    Önemli: pywebview, köprü kurarken js_api nesnesindeki her public özniteliği
    tarar. `window` gibi bir `webview.Window` referansı COM/WinForms ağacına
    girer ve konsolda binlerce hata üretir. Bu yüzden pencere `_win` ile
    tutulur (alt çizgi ile başlayan isimler atlanır).
    """

    def __init__(self) -> None:
        self._win: webview.Window | None = None

    def close_window(self) -> None:
        if self._win is not None:
            self._win.destroy()

    def get_window_size(self) -> list[int]:
        if self._win is None:
            return [480, 320]
        return [self._win.width, self._win.height]

    def get_min_size(self) -> list[int]:
        if self._win is None:
            return [280, 200]
        return [self._win.min_size[0], self._win.min_size[1]]

    def resize_window(self, width: int, height: int, fix_point: int = 3) -> None:
        """Boyutlandırma; fix_point webview FixPoint bitleri (N=1 W=2 E=4 S=8)."""
        if self._win is None:
            return
        w = max(self._win.min_size[0], int(width))
        h = max(self._win.min_size[1], int(height))
        fp = FixPoint(fix_point & 15) if fix_point >= 0 else FixPoint.NORTH | FixPoint.WEST
        self._win.resize(w, h, fp)

    def open_another_chart(self) -> None:
        spawn_duplicate_chart(self)

    def apply_chart_layout(self, mode: int) -> None:
        apply_workspace_layout(int(mode), reference=self._win)


def spawn_duplicate_chart(source: WidgetApi) -> None:
    cfg = _LAUNCH_CFG
    if not cfg:
        return
    page_html = build_html(
        cfg["template"],
        symbol=cfg["symbol"],
        interval=cfg["interval"],
        timezone=cfg["timezone"],
        theme=cfg["theme"],
        locale=cfg["locale"],
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".html",
        prefix="tradingview_pip_",
        delete=False,
    ) as tmp:
        tmp.write(page_html)
        path = Path(tmp.name)

    url = path.resolve().as_uri()
    api = WidgetApi()
    theme = cfg["theme"]
    bg = "#131722" if theme == "dark" else "#ffffff"
    x: int | None = None
    y: int | None = None
    sw = source._win
    if sw is not None:
        try:
            x = sw.x + 28
            y = sw.y + 28
        except Exception:
            pass

    create_kw: dict[str, Any] = {
        "title": f"TradingView — {cfg['symbol']}",
        "url": url,
        "width": cfg["width"],
        "height": cfg["height"],
        "resizable": True,
        "fullscreen": False,
        "min_size": (280, 200),
        "on_top": cfg["on_top"],
        "frameless": True,
        "easy_drag": False,
        "shadow": True,
        "background_color": bg,
        "js_api": api,
    }
    if x is not None and y is not None:
        create_kw["x"] = x
        create_kw["y"] = y

    nw = webview.create_window(**create_kw)
    api._win = nw

    def on_closed_dup() -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    nw.events.closed += on_closed_dup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TradingView grafiğini yüzen, yeniden boyutlandırılabilir pencerede açar."
    )
    parser.add_argument(
        "--symbol",
        default="BINANCE:BTCUSDT.P",
        help="Örnek: BINANCE:BTCUSDT.P, NASDAQ:AAPL (varsayılan: BINANCE:BTCUSDT.P)",
    )
    parser.add_argument(
        "--interval",
        default="60",
        help="Dakika: 1,3,5,15,30,60,120,240, D, W (varsayılan: 60)",
    )
    parser.add_argument(
        "--timezone",
        default="Etc/UTC",
        help="TradingView zaman dilimi (varsayılan: Etc/UTC)",
    )
    parser.add_argument(
        "--theme",
        choices=("light", "dark"),
        default="dark",
        help="Tema (varsayılan: dark)",
    )
    parser.add_argument(
        "--locale",
        default="tr",
        help="Arayüz dili (varsayılan: tr)",
    )
    parser.add_argument("--width", type=int, default=480, help="Başlangıç genişliği (px)")
    parser.add_argument("--height", type=int, default=320, help="Başlangıç yüksekliği (px)")
    parser.add_argument(
        "--no-on-top",
        action="store_true",
        help="Pencereyi her zaman üstte tutma (varsayılan: üstte)",
    )
    args = parser.parse_args()

    bundle = _bundle_dir()
    base = _writable_dir()
    tpl_path = bundle / "chart_template.html"
    if not tpl_path.is_file():
        print(f"Şablon bulunamadı: {tpl_path}", file=sys.stderr)
        sys.exit(1)

    template = tpl_path.read_text(encoding="utf-8")
    page_html = build_html(
        template,
        symbol=args.symbol,
        interval=args.interval,
        timezone=args.timezone,
        theme=args.theme,
        locale=args.locale,
    )

    _LAUNCH_CFG.clear()
    _LAUNCH_CFG.update(
        template=template,
        symbol=args.symbol,
        interval=args.interval,
        timezone=args.timezone,
        theme=args.theme,
        locale=args.locale,
        width=args.width,
        height=args.height,
        on_top=not args.no_on_top,
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".html",
        prefix="tradingview_pip_",
        delete=False,
    ) as tmp:
        tmp.write(page_html)
        path = Path(tmp.name)

    url = path.resolve().as_uri()

    api = WidgetApi()
    bg = "#131722" if args.theme == "dark" else "#ffffff"
    window = webview.create_window(
        title=f"TradingView — {args.symbol}",
        url=url,
        width=args.width,
        height=args.height,
        resizable=True,
        fullscreen=False,
        min_size=(280, 200),
        on_top=not args.no_on_top,
        frameless=True,
        easy_drag=False,
        shadow=True,
        background_color=bg,
        js_api=api,
    )
    api._win = window

    def on_closed():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    window.events.closed += on_closed

    profile_dir = base / ".webview_profile"
    webview.start(
        debug=False,
        private_mode=False,
        storage_path=str(profile_dir),
    )


if __name__ == "__main__":
    main()
