import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont

from PIL import Image, ImageTk

from weather_core import (
    build_alerts,
    build_outfit_icons,
    build_outlook,
    get_current_data,
    get_default_data,
    get_greeting,
    get_location,
    get_weather,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
NIMBUS_LARGE = os.path.join(_HERE, "nimbus_large.png")
NIMBUS_SMALL = os.path.join(_HERE, "nimbus_small.png")
ICONS_DIR = os.path.join(_HERE, "icons", "icons")
OUTFIT_DIR = os.path.join(_HERE, "outfit_icons")

W, H = 1152, 648

THEMES = {
    "dark": {
        "app_bg": "#090d12",
        "panel_bg": "#1a2030",
        "card_bg": "#242c3a",
        "border": "#3d4f6e",
        "text_primary": "#e6edf3",
        "text_secondary": "#8b949e",
        "accent": "#58a6ff",
        "button_bg": "#e6edf3",
        "button_fg": "#0d1117",
        "button_hover": "#ffffff",
        "entry_bg": "#2d3748",
        "entry_border": "#4a5568",
        "status_error": "#da3633",
        "status_ok": "#8b949e",
        "theme_button_bg": "#e6edf3",
        "theme_button_fg": "#0d1117",
    },
    "light": {
        "app_bg": "#eef4fb",
        "panel_bg": "#ffffff",
        "card_bg": "#f8fbff",
        "border": "#c7d6ea",
        "text_primary": "#17324d",
        "text_secondary": "#5f7288",
        "accent": "#1f6feb",
        "button_bg": "#1f6feb",
        "button_fg": "#ffffff",
        "button_hover": "#4387f6",
        "entry_bg": "#edf3fb",
        "entry_border": "#8aaacb",
        "status_error": "#c93c37",
        "status_ok": "#5f7288",
        "theme_button_bg": "#edf3fb",
        "theme_button_fg": "#17324d",
    },
}

SEV_COLORS = {
    "dark": {
        "danger": {"bg": "#2d1414", "bar": "#da3633", "fg": "#ff7b7b"},
        "warning": {"bg": "#2d2214", "bar": "#d29922", "fg": "#e3b341"},
        "info": {"bg": "#0f2233", "bar": "#1f6feb", "fg": "#79c0ff"},
        "success": {"bg": "#0f2117", "bar": "#3fb950", "fg": "#56d364"},
    },
    "light": {
        "danger": {"bg": "#fdecec", "bar": "#d84b4b", "fg": "#b42318"},
        "warning": {"bg": "#fff4dd", "bar": "#d4a017", "fg": "#9a6700"},
        "info": {"bg": "#e9f2ff", "bar": "#1f6feb", "fg": "#1756b3"},
        "success": {"bg": "#e7f7ec", "bar": "#2da44e", "fg": "#1f7a38"},
    },
}


class RoundedPanel(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        canvas_bg,
        bg_color,
        border_color,
        radius=24,
        padding=14,
        **kwargs,
    ):
        super().__init__(master, bg=canvas_bg, highlightthickness=0, bd=0, **kwargs)
        self._bg_color = bg_color
        self._border_color = border_color
        self._radius = radius
        self._padding = padding
        self.content = tk.Frame(self, bg=bg_color, bd=0, highlightthickness=0)
        self._window_id = self.create_window((padding, padding), window=self.content, anchor="nw")
        self.bind("<Configure>", self._redraw)

    def _rounded_points(self, width, height, radius):
        return [
            radius, 0,
            width - radius, 0,
            width, 0,
            width, radius,
            width, height - radius,
            width, height,
            width - radius, height,
            radius, height,
            0, height,
            0, height - radius,
            0, radius,
            0, 0,
        ]

    def _redraw(self, _event=None):
        width = max(self.winfo_width(), 2)
        height = max(self.winfo_height(), 2)
        radius = min(self._radius, width // 2, height // 2)
        self.delete("panel")
        self.create_polygon(
            self._rounded_points(width - 1, height - 1, radius),
            smooth=True,
            splinesteps=24,
            fill=self._bg_color,
            outline=self._border_color,
            width=1.5,
            tags="panel",
        )
        self.tag_lower("panel")
        inner_w = max(width - (self._padding * 2), 1)
        inner_h = max(height - (self._padding * 2), 1)
        self.coords(self._window_id, self._padding, self._padding)
        self.itemconfigure(self._window_id, width=inner_w, height=inner_h)


def get_temp_color(temp):
    if temp <= 10:
        return "#a8d8f0"
    if temp <= 25:
        return "#60b8e8"
    if temp <= 32:
        return "#4da6d9"
    if temp <= 45:
        return "#5bc4c4"
    if temp <= 60:
        return "#56d364"
    if temp <= 75:
        return "#d2e86a"
    if temp <= 85:
        return "#f0c040"
    if temp <= 95:
        return "#f08c30"
    if temp <= 105:
        return "#e05020"
    return "#da3633"


class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weather or Not")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)

        self._theme_name = "dark"
        self._current_data = None
        self._alerts = []
        self._outlook = []
        self._location_name = ""
        self._user_name = ""
        self._active_screen = "loading"

        self._img_nimbus_large = None
        self._img_nimbus_small = None
        self._icons_xl = {}
        self._icons_md = {}
        self._outfit_icons = {}
        self._outfit_suggestions = []

        self._build_fonts()
        self._load_images()
        self._rebuild_ui()
        self._show_loading()

    @property
    def palette(self):
        return THEMES[self._theme_name]

    def _severity_palette(self, severity):
        return SEV_COLORS[self._theme_name].get(severity, SEV_COLORS[self._theme_name]["info"])

    def _build_fonts(self):
        self.f_huge = tkfont.Font(family="Helvetica", size=78, weight="bold")
        self.f_h1 = tkfont.Font(family="Helvetica", size=24, weight="bold")
        self.f_h2 = tkfont.Font(family="Helvetica", size=17, weight="bold")
        self.f_body = tkfont.Font(family="Helvetica", size=15)
        self.f_small = tkfont.Font(family="Helvetica", size=13)
        self.f_tiny = tkfont.Font(family="Helvetica", size=11)
        self.f_label = tkfont.Font(family="Helvetica", size=13, weight="bold")

    def _load_images(self):
        try:
            self._img_nimbus_large = ImageTk.PhotoImage(Image.open(NIMBUS_LARGE).convert("RGBA"))
        except Exception:
            self._img_nimbus_large = None
        try:
            self._img_nimbus_small = ImageTk.PhotoImage(Image.open(NIMBUS_SMALL).convert("RGBA"))
        except Exception:
            self._img_nimbus_small = None

        icon_files = [
            "clear_day", "clear_night", "cloudy", "overcast", "partly_cloudy_day",
            "partly_cloudy_night", "overcast_day", "overcast_night", "rain",
            "overcast_rain", "overcast_day_rain", "overcast_night_rain",
            "partly_cloudy_day_rain", "partly_cloudy_night_rain", "extreme_rain",
            "extreme_day_rain", "drizzle", "overcast_day_drizzle",
            "overcast_night_drizzle", "extreme_drizzle", "snow", "overcast_snow",
            "overcast_day_snow", "overcast_night_snow", "extreme_snow",
            "extreme_day_snow", "wind_snow", "thunderstorm", "thunderstorm_day",
            "thunderstorm_night", "thunderstorm_rain", "thunderstorm_day_rain",
            "thunderstorm_night_rain", "thunderstorm_extreme",
            "thunderstorm_day_extreme", "thunderstorm_snow", "fog", "fog_day",
            "fog_night", "mist", "overcast_fog", "overcast_day_fog",
            "overcast_night_fog", "extreme_fog", "haze", "haze_day", "haze_night",
            "extreme_haze", "extreme_day_haze", "dust", "dust_day", "dust_night",
            "dust_wind", "smoke", "overcast_smoke", "extreme_smoke",
            "extreme_day_smoke", "sleet", "overcast_sleet", "overcast_day_sleet",
            "overcast_night_sleet", "hail", "overcast_hail", "extreme_hail",
            "tornado", "hurricane", "extreme", "extreme_day", "extreme_night",
            "wind", "wind_alert", "not_available",
        ]
        for name in icon_files:
            path = os.path.join(ICONS_DIR, f"{name}.png")
            try:
                img = Image.open(path).convert("RGBA")
                self._icons_xl[name] = ImageTk.PhotoImage(img.resize((120, 120), Image.LANCZOS))
                self._icons_md[name] = ImageTk.PhotoImage(img.resize((72, 72), Image.LANCZOS))
            except Exception:
                self._icons_xl[name] = None
                self._icons_md[name] = None

        outfit_files = [
            "umbrella", "boots", "jacket", "jacket__1_", "scarf",
            "winter-gloves", "sweater-with-deer", "t-shirt", "sunglasses", "sunscreen",
        ]
        for name in outfit_files:
            path = os.path.join(OUTFIT_DIR, f"{name}.png")
            try:
                img = Image.open(path).convert("RGBA")
                self._outfit_icons[name] = ImageTk.PhotoImage(img.resize((60, 60), Image.LANCZOS))
            except Exception:
                self._outfit_icons[name] = None

    def _rebuild_ui(self):
        name_value = getattr(self, "_name_entry", None).get() if hasattr(self, "_name_entry") else ""
        zip_value = getattr(self, "_zip_entry", None).get() if hasattr(self, "_zip_entry") else ""
        current_screen = self._active_screen

        for frame_name in ("_loading", "_splash", "_dashboard"):
            frame = getattr(self, frame_name, None)
            if frame is not None:
                frame.destroy()

        self.configure(bg=self.palette["app_bg"])
        self._loading = tk.Frame(self, bg=self.palette["app_bg"], width=W, height=H)
        self._splash = tk.Frame(self, bg=self.palette["app_bg"], width=W, height=H)
        self._dashboard = tk.Frame(self, bg=self.palette["app_bg"], width=W, height=H)

        self._build_loading()
        self._build_splash()
        self._build_dashboard()

        self._name_entry.insert(0, name_value)
        self._zip_entry.insert(0, zip_value)

        if current_screen == "dashboard" and self._current_data:
            self._refresh_dashboard()
            self._show_dashboard()
        elif current_screen == "splash":
            self._show_splash()
        else:
            self._show_loading()

    def _toggle_theme(self):
        self._theme_name = "light" if self._theme_name == "dark" else "dark"
        self._rebuild_ui()

    def _build_theme_button(self, parent):
        label = "Light Mode" if self._theme_name == "dark" else "Dark Mode"
        return tk.Button(
            parent,
            text=label,
            bg=self.palette["theme_button_bg"],
            fg=self.palette["theme_button_fg"],
            activebackground=self.palette["button_hover"],
            activeforeground=self.palette["theme_button_fg"],
            relief="solid",
            bd=1,
            cursor="hand2",
            font=self.f_tiny,
            padx=12,
            pady=6,
            highlightthickness=1,
            highlightbackground=self.palette["border"],
            command=self._toggle_theme,
        )

    def _build_loading(self):
        center = tk.Frame(self._loading, bg=self.palette["app_bg"])
        center.place(relx=0.5, rely=0.5, anchor="center")

        self._build_theme_button(self._loading).place(x=W - 118, y=18)

        if self._img_nimbus_large:
            tk.Label(center, image=self._img_nimbus_large, bg=self.palette["app_bg"]).pack(pady=(0, 20))
        else:
            tk.Label(center, text="Weather", bg=self.palette["app_bg"], fg=self.palette["accent"], font=self.f_h1).pack(pady=(0, 20))

        tk.Label(
            center,
            text="Weather or Not",
            bg=self.palette["app_bg"],
            fg=self.palette["text_primary"],
            font=tkfont.Font(family="Helvetica", size=36, weight="bold"),
        ).pack()
        tk.Label(
            center,
            text="Not just a forecast, but a plan.",
            bg=self.palette["app_bg"],
            fg=self.palette["text_secondary"],
            font=tkfont.Font(family="Helvetica", size=16, slant="italic"),
        ).pack(pady=(8, 0))

    def _build_splash(self):
        if self._img_nimbus_small:
            tk.Label(self._splash, image=self._img_nimbus_small, bg=self.palette["app_bg"]).place(x=12, y=8)

        self._build_theme_button(self._splash).place(x=W - 118, y=18)

        center = tk.Frame(self._splash, bg=self.palette["app_bg"])
        center.place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(center, text="Weather or Not", bg=self.palette["app_bg"], fg=self.palette["text_primary"], font=self.f_h1).pack()
        tk.Label(
            center,
            text="Your local weather advisory system",
            bg=self.palette["app_bg"],
            fg=self.palette["text_secondary"],
            font=self.f_body,
        ).pack(pady=(6, 28))

        form_panel = RoundedPanel(
            center,
            canvas_bg=self.palette["panel_bg"],
            bg_color=self.palette["panel_bg"],
            border_color=self.palette["border"],
            width=520,
            height=240,
            radius=30,
            padding=20,
        )
        form_panel.pack()
        form = form_panel.content

        name_row = tk.Frame(form, bg=self.palette["panel_bg"])
        name_row.pack(fill="x", pady=(8, 12))
        tk.Label(name_row, text="Your name", bg=self.palette["panel_bg"], fg=self.palette["text_secondary"], font=self.f_label, width=10, anchor="e").pack(side="left", padx=(0, 12))
        self._name_entry = tk.Entry(
            name_row,
            bg=self.palette["entry_bg"],
            fg=self.palette["text_primary"],
            insertbackground=self.palette["text_primary"],
            relief="flat",
            bd=0,
            font=self.f_body,
            width=24,
            highlightthickness=2,
            highlightcolor=self.palette["accent"],
            highlightbackground=self.palette["entry_border"],
        )
        self._name_entry.pack(side="left", ipady=9, ipadx=8)

        zip_row = tk.Frame(form, bg=self.palette["panel_bg"])
        zip_row.pack(fill="x", pady=(0, 20))
        tk.Label(zip_row, text="ZIP code", bg=self.palette["panel_bg"], fg=self.palette["text_secondary"], font=self.f_label, width=10, anchor="e").pack(side="left", padx=(0, 12))
        self._zip_entry = tk.Entry(
            zip_row,
            bg=self.palette["entry_bg"],
            fg=self.palette["text_primary"],
            insertbackground=self.palette["text_primary"],
            relief="flat",
            bd=0,
            font=self.f_body,
            width=24,
            highlightthickness=2,
            highlightcolor=self.palette["accent"],
            highlightbackground=self.palette["entry_border"],
        )
        self._zip_entry.bind("<Return>", lambda _e: self._fetch_weather())
        self._zip_entry.pack(side="left", ipady=9, ipadx=8)

        self._go_btn = tk.Button(
            form,
            text="Get My Weather",
            bg=self.palette["button_bg"],
            fg=self.palette["button_fg"],
            font=self.f_h2,
            relief="flat",
            padx=32,
            pady=12,
            cursor="hand2",
            activebackground=self.palette["button_hover"],
            activeforeground=self.palette["button_fg"],
            command=self._fetch_weather,
        )
        self._go_btn.pack()

        self._splash_status = tk.Label(center, text="", bg=self.palette["app_bg"], fg=self.palette["text_secondary"], font=self.f_small)
        self._splash_status.pack(pady=(14, 0))

    def _make_panel(self, parent, width, height, radius=24, padding=14):
        return RoundedPanel(
            parent,
            canvas_bg=self.palette["panel_bg"],
            bg_color=self.palette["panel_bg"],
            border_color=self.palette["border"],
            width=width,
            height=height,
            radius=radius,
            padding=padding,
        )

    def _make_card(self, parent, width, height, radius=24, padding=14):
        return RoundedPanel(
            parent,
            canvas_bg=self.palette["card_bg"],
            bg_color=self.palette["card_bg"],
            border_color=self.palette["border"],
            width=width,
            height=height,
            radius=radius,
            padding=padding,
        )

    def _build_dashboard(self):
        f = self._dashboard
        topbar_h = 54
        alerts_h = 160
        main_y = topbar_h + 8
        main_h = H - topbar_h - alerts_h - 18
        alerts_y = main_y + main_h + 8
        pad = 10
        hero_w = 286
        center_x = pad + hero_w + pad
        center_w = W - hero_w - (pad * 3)

        self._top_bar = tk.Frame(f, bg=self.palette["panel_bg"], height=topbar_h)
        self._top_bar.place(x=12, y=10, width=W - 24, height=topbar_h)

        if self._img_nimbus_small:
            tk.Label(self._top_bar, image=self._img_nimbus_small, bg=self.palette["panel_bg"]).pack(side="left", padx=(14, 6), pady=6)

        self._loc_lbl = tk.Label(self._top_bar, text="", bg=self.palette["panel_bg"], fg=self.palette["text_primary"], font=self.f_h2)
        self._loc_lbl.pack(side="left")

        self._build_theme_button(self._top_bar).pack(side="right", padx=(0, 12), pady=10)
        self._new_search_btn = tk.Button(
            self._top_bar,
            text="New Search",
            bg=self.palette["theme_button_bg"],
            fg=self.palette["theme_button_fg"],
            font=self.f_tiny,
            relief="solid",
            bd=1,
            padx=12,
            pady=6,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=self.palette["border"],
            activebackground=self.palette["button_hover"],
            activeforeground=self.palette["theme_button_fg"],
            command=self._go_back,
        )
        self._new_search_btn.pack(side="right", padx=(0, 10), pady=10)

        self._time_lbl = tk.Label(self._top_bar, text="", bg=self.palette["panel_bg"], fg=self.palette["text_secondary"], font=self.f_small)
        self._time_lbl.pack(side="right", padx=(0, 12))

        self._hero_panel = self._make_panel(f, hero_w, main_h, radius=30, padding=18)
        self._hero_panel.place(x=pad, y=main_y, width=hero_w, height=main_h)
        hero = self._hero_panel.content
        self._hero_icon = tk.Label(hero, image="", bg=self.palette["panel_bg"])
        self._hero_icon.pack(pady=(16, 2))
        self._hero_temp = tk.Label(hero, text="", bg=self.palette["panel_bg"], fg=self.palette["text_primary"], font=self.f_huge)
        self._hero_temp.pack()
        self._hero_cond = tk.Label(hero, text="", bg=self.palette["panel_bg"], fg=self.palette["text_primary"], font=self.f_h2)
        self._hero_cond.pack(pady=(4, 0))
        self._hero_desc = tk.Label(hero, text="", bg=self.palette["panel_bg"], fg=self.palette["text_secondary"], font=self.f_small)
        self._hero_desc.pack()
        self._hero_feels = tk.Label(hero, text="", bg=self.palette["panel_bg"], fg=self.palette["text_secondary"], font=self.f_small)
        self._hero_feels.pack(pady=(2, 0))
        tk.Frame(hero, bg=self.palette["border"], height=1).pack(fill="x", padx=8, pady=14)
        self._hero_greeting = tk.Label(hero, text="", bg=self.palette["panel_bg"], fg=self.palette["accent"], font=self.f_small, wraplength=220, justify="center")
        self._hero_greeting.pack(padx=10)
        self._hero_date = tk.Label(hero, text="", bg=self.palette["panel_bg"], fg=self.palette["text_secondary"], font=self.f_tiny)
        self._hero_date.pack(pady=(4, 0))

        stats_h = int(main_h * 0.5)
        outlook_h = main_h - stats_h - pad

        stats_frame = tk.Frame(f, bg=self.palette["app_bg"])
        stats_frame.place(x=center_x, y=main_y, width=center_w, height=stats_h)

        self._stat_widgets = {}
        stat_keys = [
            ("humidity", "Humidity", "%"),
            ("wind_speed", "Wind", " mph"),
            ("uv_index", "UV Index", ""),
            ("visibility", "Visibility", " mi"),
            ("cloud_cover", "Cloud Cover", "%"),
            ("dew_point", "Dew Point", "°F"),
            ("pressure", "Pressure", " hPa"),
            ("wind_gust", "Wind Gust", " mph"),
        ]
        cols = 4
        for i, (key, label, unit) in enumerate(stat_keys):
            ri = i // cols
            ci = i % cols
            card = self._make_card(stats_frame, 0, 0, radius=22, padding=12)
            card.grid(row=ri, column=ci, padx=4, pady=4, sticky="nsew")
            stats_frame.columnconfigure(ci, weight=1)
            stats_frame.rowconfigure(ri, weight=1)
            inner = card.content
            tk.Label(inner, text=label, bg=self.palette["card_bg"], fg=self.palette["text_secondary"], font=self.f_body).pack(pady=(8, 2))
            val_lbl = tk.Label(inner, text="--", bg=self.palette["card_bg"], fg=self.palette["text_primary"], font=self.f_h1)
            val_lbl.pack(pady=(0, 8))
            self._stat_widgets[key] = (val_lbl, unit)

        outlook_y = main_y + stats_h + pad
        outlook_frame = tk.Frame(f, bg=self.palette["app_bg"])
        outlook_frame.place(x=center_x, y=outlook_y, width=center_w, height=outlook_h)
        outlook_frame.columnconfigure(0, weight=1)
        outlook_frame.columnconfigure(1, weight=1)
        outlook_frame.rowconfigure(0, weight=1)

        self._outlook_cards = []
        for col_i in range(2):
            card = self._make_card(outlook_frame, 0, 0, radius=26, padding=14)
            card.grid(row=0, column=col_i, padx=4, pady=0, sticky="nsew")
            inner = card.content

            top_row = tk.Frame(inner, bg=self.palette["card_bg"])
            top_row.pack(fill="x", pady=(2, 4))
            day_lbl = tk.Label(top_row, text="", bg=self.palette["card_bg"], fg=self.palette["text_secondary"], font=self.f_small)
            day_lbl.pack(side="left")
            pop_lbl = tk.Label(top_row, text="", bg=self.palette["card_bg"], fg=self.palette["accent"], font=self.f_small)
            pop_lbl.pack(side="right")

            body_row = tk.Frame(inner, bg=self.palette["card_bg"])
            body_row.pack(fill="x", pady=(0, 4))
            icon_lbl = tk.Label(body_row, image="", bg=self.palette["card_bg"])
            icon_lbl.pack(side="left", padx=(2, 8))
            info_frame = tk.Frame(body_row, bg=self.palette["card_bg"])
            info_frame.pack(side="left", fill="both", expand=True)
            cond_lbl = tk.Label(info_frame, text="", bg=self.palette["card_bg"], fg=self.palette["text_primary"], font=self.f_h2, anchor="w")
            cond_lbl.pack(anchor="w")
            temp_lbl = tk.Label(info_frame, text="", bg=self.palette["card_bg"], fg=self.palette["text_secondary"], font=self.f_body, anchor="w")
            temp_lbl.pack(anchor="w")

            tk.Frame(inner, bg=self.palette["border"], height=1).pack(fill="x", pady=(4, 6))
            tip_lbl = tk.Label(inner, text="", bg=self.palette["card_bg"], fg=self.palette["accent"], font=self.f_small, wraplength=(center_w // 2) - 46, justify="left", anchor="w")
            tip_lbl.pack(fill="x")

            self._outlook_cards.append({
                "day": day_lbl,
                "icon": icon_lbl,
                "cond": cond_lbl,
                "temp": temp_lbl,
                "pop": pop_lbl,
                "tip": tip_lbl,
            })

        alerts_header = tk.Frame(f, bg=self.palette["app_bg"])
        alerts_header.place(x=12, y=alerts_y, width=W - 24, height=26)
        tk.Label(alerts_header, text="ACTIVE ALERTS", bg=self.palette["app_bg"], fg=self.palette["text_secondary"], font=self.f_tiny).pack(side="left", padx=(4, 0))

        alerts_container = tk.Frame(f, bg=self.palette["app_bg"])
        alerts_container.place(x=12, y=alerts_y + 26, width=W - 24, height=alerts_h - 26)

        self._alerts_scrollbar = tk.Scrollbar(
            alerts_container,
            orient="horizontal",
            bg=self.palette["panel_bg"],
            troughcolor=self.palette["app_bg"],
            activebackground=self.palette["accent"],
            highlightthickness=0,
            bd=0,
        )
        self._alerts_scrollbar.pack(side="bottom", fill="x")

        self._alerts_canvas = tk.Canvas(
            alerts_container,
            bg=self.palette["app_bg"],
            highlightthickness=0,
            bd=0,
            xscrollcommand=self._alerts_scrollbar.set,
        )
        self._alerts_canvas.pack(side="top", fill="both", expand=True)
        self._alerts_scrollbar.config(command=self._alerts_canvas.xview)

        self._alerts_inner = tk.Frame(self._alerts_canvas, bg=self.palette["app_bg"])
        self._alerts_window = self._alerts_canvas.create_window((0, 0), window=self._alerts_inner, anchor="nw")
        self._alerts_canvas.bind("<Configure>", self._resize_alert_window)
        self._alerts_inner.bind("<Configure>", lambda _e: self._alerts_canvas.configure(scrollregion=self._alerts_canvas.bbox("all")))
        self._alerts_canvas.bind("<MouseWheel>", lambda e: self._alerts_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        self._alerts_canvas.bind("<Button-4>", lambda e: self._alerts_canvas.xview_scroll(-1, "units"))
        self._alerts_canvas.bind("<Button-5>", lambda e: self._alerts_canvas.xview_scroll(1, "units"))

    def _resize_alert_window(self, event):
        self._alerts_canvas.itemconfigure(self._alerts_window, height=event.height)

    def _show_loading(self):
        self._active_screen = "loading"
        self._splash.place_forget()
        self._dashboard.place_forget()
        self._loading.place(x=0, y=0, width=W, height=H)
        self.after(3000, self._fade_to_splash)

    def _fade_to_splash(self):
        if self._active_screen == "loading":
            self._loading.place_forget()
            self._show_splash()

    def _show_splash(self):
        self._active_screen = "splash"
        self._loading.place_forget()
        self._dashboard.place_forget()
        self._splash.place(x=0, y=0, width=W, height=H)

    def _show_dashboard(self):
        self._active_screen = "dashboard"
        self._loading.place_forget()
        self._splash.place_forget()
        self._dashboard.place(x=0, y=0, width=W, height=H)

    def _get_condition_key(self, condition, cloud_cover=0):
        hour = datetime.now().hour
        is_day = 6 <= hour < 19
        heavy = cloud_cover >= 75

        if condition == "Clear":
            return "clear_day" if is_day else "clear_night"
        if condition == "Clouds":
            if heavy:
                return "overcast_day" if is_day else "overcast_night"
            return "partly_cloudy_day" if is_day else "partly_cloudy_night"
        if condition == "Rain":
            if heavy:
                return "overcast_day_rain" if is_day else "overcast_night_rain"
            return "rain"
        if condition == "Drizzle":
            return "overcast_day_drizzle" if is_day else "overcast_night_drizzle"
        if condition == "Snow":
            if heavy:
                return "overcast_day_snow" if is_day else "overcast_night_snow"
            return "snow"
        if condition == "Thunderstorm":
            return "thunderstorm_day" if is_day else "thunderstorm_night"
        if condition == "Fog":
            return "fog_day" if is_day else "fog_night"
        if condition == "Mist":
            return "mist"
        if condition == "Haze":
            return "haze_day" if is_day else "haze_night"
        if condition == "Dust":
            return "dust_day" if is_day else "dust_night"
        if condition == "Smoke":
            return "smoke"
        if condition == "Sleet":
            return "overcast_day_sleet" if is_day else "overcast_night_sleet"
        if condition == "Hail":
            return "hail"
        if condition == "Tornado":
            return "tornado"
        if condition == "Hurricane":
            return "hurricane"
        if condition == "Squall":
            return "wind_alert"
        if condition == "Sand":
            return "dust_wind"
        if condition == "Ash":
            return "extreme_smoke"
        return "not_available"

    def _go_back(self):
        self._zip_entry.delete(0, "end")
        self._splash_status.configure(text="")
        self._show_splash()

    def _set_status(self, text, is_error=False):
        self._splash_status.configure(
            text=text,
            fg=self.palette["status_error"] if is_error else self.palette["status_ok"],
        )

    def _fetch_weather(self):
        zip_code = self._zip_entry.get().strip()
        name = self._name_entry.get().strip()
        if not zip_code:
            self._set_status("Please enter a ZIP code.", is_error=True)
            return

        self._user_name = name or "Friend"
        self._set_status("Fetching weather...")
        self._go_btn.configure(state="disabled")
        threading.Thread(target=self._load_weather, args=(zip_code,), daemon=True).start()

    def _load_weather(self, zip_code):
        result = get_location(zip_code)

        if result == "MISSING_API_KEY":
            self.after(0, lambda: self._set_status("Missing API key. Set OPENWEATHER_API_KEY in a .env file or environment variable.", is_error=True))
            self.after(0, lambda: self._go_btn.configure(state="normal"))
            return

        if result == "NO_NETWORK":
            self._location_name = "No Network"
            self._current_data = get_default_data()
            self._alerts = [("danger", "No Network Connection", "Unable to reach weather service. Please check your internet connection.")]
            self._outlook = []
            self._outfit_suggestions = []
            self.after(0, self._on_data_loaded)
            return

        if not result:
            self.after(0, lambda: self._set_status("Invalid ZIP code. Please try again.", is_error=True))
            self.after(0, lambda: self._go_btn.configure(state="normal"))
            return

        lat, lon, city, state = result
        self._location_name = f"{city}, {state}" if state else city

        weather = get_weather(lat, lon)
        if weather == "MISSING_API_KEY":
            self.after(0, lambda: self._set_status("Missing API key. Set OPENWEATHER_API_KEY in a .env file or environment variable.", is_error=True))
            self.after(0, lambda: self._go_btn.configure(state="normal"))
            return

        if not weather:
            self._current_data = get_default_data()
            self._alerts = [("danger", "No Network Connection", "Location found but weather data unavailable. Check your connection.")]
            self._outlook = []
            self.after(0, self._on_data_loaded)
            return

        self._current_data = get_current_data(weather)
        self._alerts = build_alerts(weather)
        self._outlook = build_outlook(weather)
        self._outfit_suggestions = build_outfit_icons(weather)
        self.after(0, self._on_data_loaded)

    def _on_data_loaded(self):
        self._go_btn.configure(state="normal")
        self._set_status("")
        self._refresh_dashboard()
        self._show_dashboard()

    def _refresh_dashboard(self):
        d = self._current_data
        now = datetime.now()

        self._loc_lbl.configure(text=f" {self._location_name}")
        self._time_lbl.configure(text=now.strftime("%A, %B %d  •  %I:%M %p"))

        cond_key = self._get_condition_key(d["condition"], d.get("cloud_cover", 0))
        icon_img = self._icons_xl.get(cond_key)
        if icon_img:
            self._hero_icon.configure(image=icon_img)
            self._hero_icon.image = icon_img
        else:
            self._hero_icon.configure(image="")

        self._hero_temp.configure(text=f"{d['temperature']}°", fg=get_temp_color(d["temperature"]))
        self._hero_cond.configure(text=d["condition"])
        self._hero_desc.configure(text=d["description"].title())
        self._hero_feels.configure(text=f"Feels like {d['feels_like']}°F")
        self._hero_greeting.configure(text=get_greeting(self._user_name))
        self._hero_date.configure(text=now.strftime("%B %d, %Y"))

        for key, (lbl, unit) in self._stat_widgets.items():
            val = d.get(key, "--")
            if key == "wind_gust" and (val == 0 or val == "--"):
                lbl.configure(text="None")
            elif val == "--":
                lbl.configure(text="--")
            else:
                lbl.configure(text=f"{val}{unit}")

        for i in range(2):
            card = self._outlook_cards[i]
            if i >= len(self._outlook):
                card["day"].configure(text="--")
                card["icon"].configure(image="")
                card["cond"].configure(text="No data")
                card["temp"].configure(text="--", fg=self.palette["text_secondary"])
                card["pop"].configure(text="")
                card["tip"].configure(text="No network connection")
                continue

            day = self._outlook[i]
            cond_key = self._get_condition_key(day["condition"], 50)
            icon_img = self._icons_md.get(cond_key)
            card["day"].configure(text=day["label"].upper())
            if icon_img:
                card["icon"].configure(image=icon_img)
                card["icon"].image = icon_img
            else:
                card["icon"].configure(image="")
            card["cond"].configure(text=day["condition"])
            card["temp"].configure(text=f"Hi {day['temp_high']}°  Lo {day['temp_low']}°", fg=get_temp_color(day["temp_high"]))
            card["pop"].configure(text=f"Rain: {day['pop']}%")
            card["tip"].configure(text=f"Tip: {day['tip']}")

        for widget in self._alerts_inner.winfo_children():
            widget.destroy()

        # --- Alert cards first ---
        if not self._alerts:
            tk.Label(self._alerts_inner, text="No active alerts.", bg=self.palette["app_bg"],
                     fg=self.palette["text_secondary"], font=self.f_small).pack(side="left", padx=16, pady=10)

        for sev, title, body in self._alerts:
            colors = self._severity_palette(sev)
            cell = RoundedPanel(
                self._alerts_inner,
                canvas_bg=colors["bg"],
                bg_color=colors["bg"],
                border_color=colors["bar"],
                width=270,
                height=110,
                radius=22,
                padding=12,
            )
            cell.pack(side="left", fill="y", padx=4, pady=4)
            inner = cell.content
            tk.Label(inner, text=title, bg=colors["bg"], fg=colors["fg"], font=self.f_h2, anchor="w").pack(anchor="w", pady=(2, 0))
            tk.Label(inner, text=body, bg=colors["bg"], fg=self.palette["text_secondary"], font=self.f_body, wraplength=220, justify="left", anchor="w").pack(anchor="w", pady=(4, 0))

        # --- "Going out?" card — always last in the strip ---
        num_icons = len(self._outfit_suggestions) if self._outfit_suggestions else 1
        outfit_w = max(200, num_icons * 68 + 24)
        outfit_card = RoundedPanel(
            self._alerts_inner,
            canvas_bg=self.palette["card_bg"],
            bg_color=self.palette["card_bg"],
            border_color=self.palette["border"],
            width=outfit_w,
            height=110,
            radius=22,
            padding=12,
        )
        outfit_card.pack(side="left", fill="y", padx=4, pady=4)
        outfit_inner = outfit_card.content
        tk.Label(outfit_inner, text="Going out?", bg=self.palette["card_bg"],
                 fg=self.palette["text_secondary"], font=self.f_label).pack(anchor="w", pady=(0, 4))
        icons_row = tk.Frame(outfit_inner, bg=self.palette["card_bg"])
        icons_row.pack(anchor="w")
        if self._outfit_suggestions:
            for icon_name in self._outfit_suggestions:
                img = self._outfit_icons.get(icon_name)
                if img:
                    lbl = tk.Label(icons_row, image=img, bg=self.palette["card_bg"])
                    lbl.image = img
                    lbl.pack(side="left", padx=4)
        else:
            tk.Label(icons_row, text="No gear needed — enjoy!", bg=self.palette["card_bg"],
                     fg=self.palette["text_secondary"], font=self.f_tiny).pack(side="left")


if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()
