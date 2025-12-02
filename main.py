import os
import re
import threading
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.carousel import Carousel
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
import yt_dlp as youtube_dl
from pathlib import Path
from datetime import datetime
import webbrowser

# Set window size for mobile emulation jj
Window.size = (400, 700)
Window.clearcolor = (0.96, 0.96, 0.96, 1)

class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)  # Transparent background
        self.background_normal = ''
        self.background_down = ''
        
        with self.canvas.before:
            Color(0.1, 0.5, 0.8, 1)
            self.rect = RoundedRectangle(
                size=self.size,
                pos=self.pos,
                radius=[dp(10)]
            )
        
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class EnhancedQualityPopup(Popup):
    def __init__(self, qualities, callback, video_title="", **kwargs):
        super().__init__(**kwargs)
        self.title = f"Select Quality for: {video_title[:30]}..."
        self.size_hint = (0.95, 0.85)
        self.title_size = '18sp'
        self.title_color = (0.1, 0.5, 0.8, 1)
        self.separator_color = (0.1, 0.5, 0.8, 1)
        self.callback = callback
        self.selected_quality = None
        
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Video Info Header
        info_header = BoxLayout(orientation='vertical', size_hint_y=0.15, padding=dp(5))
        info_header.add_widget(Label(
            text=f"[b]{video_title[:50]}...[/b]" if len(video_title) > 50 else f"[b]{video_title}[/b]",
            font_size='16sp',
            color=(0.2, 0.2, 0.2, 1),
            markup=True,
            halign='center'
        ))
        info_header.add_widget(Label(
            text=f"Found {len(qualities)} quality options",
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1)
        ))
        layout.add_widget(info_header)
        
        # Quality Categories
        categories = self.categorize_qualities(qualities)
        
        # Create tabs using Carousel
        carousel = Carousel(direction='right', size_hint_y=0.65)
        
        # 4K/2K Tab
        if categories.get('4k'):
            tab1 = self.create_quality_tab(categories['4k'], "4K/2K Ultra HD", (0.8, 0.2, 0.2, 1))
            carousel.add_widget(tab1)
        
        # 1080p Tab
        if categories.get('1080p'):
            tab2 = self.create_quality_tab(categories['1080p'], "Full HD 1080p", (0.2, 0.6, 0.2, 1))
            carousel.add_widget(tab2)
        
        # 720p Tab
        if categories.get('720p'):
            tab3 = self.create_quality_tab(categories['720p'], "HD 720p", (0.1, 0.5, 0.8, 1))
            carousel.add_widget(tab3)
        
        # SD Tab
        if categories.get('sd'):
            tab4 = self.create_quality_tab(categories['sd'], "Standard Quality", (0.6, 0.3, 0.8, 1))
            carousel.add_widget(tab4)
        
        # Audio Only Tab
        if categories.get('audio'):
            tab5 = self.create_quality_tab(categories['audio'], "Audio Only", (0.9, 0.6, 0.1, 1))
            carousel.add_widget(tab5)
        
        layout.add_widget(carousel)
        
        # Carousel indicators
        indicators = BoxLayout(size_hint_y=0.05, spacing=dp(5))
        for i in range(len(carousel.slides)):
            indicator = Label(
                text="●",
                font_size='20sp',
                color=(0.1, 0.5, 0.8, 1) if i == carousel.index else (0.8, 0.8, 0.8, 1)
            )
            indicators.add_widget(indicator)
        layout.add_widget(indicators)
        
        # Action Buttons
        action_layout = BoxLayout(size_hint_y=0.15, spacing=dp(10), padding=dp(5))
        
        auto_best_btn = Button(
            text="[b]Auto Select Best[/b]",
            background_color=(0.1, 0.6, 0.3, 1),
            color=(1, 1, 1, 1),
            markup=True
        )
        auto_best_btn.bind(on_press=lambda x: self.auto_select_best(qualities))
        action_layout.add_widget(auto_best_btn)
        
        select_btn = Button(
            text="[b]Select Quality[/b]",
            background_color=(0.1, 0.5, 0.8, 1),
            color=(1, 1, 1, 1),
            markup=True,
            disabled=True
        )
        select_btn.bind(on_press=self.confirm_selection)
        self.select_btn = select_btn
        action_layout.add_widget(select_btn)
        
        cancel_btn = Button(
            text="[b]Cancel[/b]",
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            markup=True
        )
        cancel_btn.bind(on_press=self.dismiss)
        action_layout.add_widget(cancel_btn)
        
        layout.add_widget(action_layout)
        
        self.add_widget(layout)
    
    def categorize_qualities(self, qualities):
        """Categorize qualities by resolution"""
        categories = {
            '4k': [],    # 4K and 2K
            '1080p': [], # 1080p
            '720p': [],  # 720p
            'sd': [],    # Below 720p
            'audio': []  # Audio only
        }
        
        for quality in qualities:
            vcodec = quality.get('vcodec', 'none')
            acodec = quality.get('acodec', 'none')
            
            if vcodec == 'none' and acodec != 'none':
                categories['audio'].append(quality)
                continue
            
            res = quality.get('resolution', '')
            if '3840' in res or '2160' in res or '1440' in res or '2880' in res:
                categories['4k'].append(quality)
            elif '1080' in res:
                categories['1080p'].append(quality)
            elif '720' in res:
                categories['720p'].append(quality)
            else:
                categories['sd'].append(quality)
        
        return categories
    
    def create_quality_tab(self, qualities, title, title_color):
        """Create a tab for specific quality category"""
        tab = BoxLayout(orientation='vertical', spacing=dp(5))
        
        # Tab title
        title_label = Label(
            text=f"[b]{title}[/b]",
            font_size='16sp',
            size_hint_y=0.1,
            color=title_color,
            markup=True
        )
        tab.add_widget(title_label)
        
        # Scrollable quality list
        scroll = ScrollView()
        quality_grid = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        quality_grid.bind(minimum_height=quality_grid.setter('height'))
        
        for quality in qualities:
            quality_btn = self.create_quality_button(quality)
            quality_grid.add_widget(quality_btn)
        
        quality_grid.height = len(qualities) * dp(80)
        scroll.add_widget(quality_grid)
        tab.add_widget(scroll)
        
        return tab
    
    def create_quality_button(self, quality):
        """Create a quality selection button"""
        btn = Button(
            size_hint_y=None,
            height=dp(75),
            background_color=(0.95, 0.95, 0.95, 1),
            background_normal='',
            background_down=''
        )
        
        # Create custom layout inside button
        with btn.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            Rectangle(pos=btn.pos, size=btn.size)
        
        # Main button layout
        btn_layout = BoxLayout(orientation='vertical', padding=dp(5))
        
        # Top row: Resolution and Format
        top_row = BoxLayout(size_hint_y=0.4)
        
        resolution = quality.get('resolution', 'Unknown')
        format_note = quality.get('format_note', '')
        
        resolution_label = Label(
            text=f"[b]{resolution}[/b]",
            font_size='14sp',
            halign='left',
            markup=True
        )
        top_row.add_widget(resolution_label)
        
        format_label = Label(
            text=f"{format_note}",
            font_size='12sp',
            halign='right',
            color=(0.5, 0.5, 0.5, 1)
        )
        top_row.add_widget(format_label)
        
        # Middle row: Codec info
        middle_row = BoxLayout(size_hint_y=0.3)
        
        vcodec = quality.get('vcodec', 'none')
        acodec = quality.get('acodec', 'none')
        
        if vcodec != 'none' and acodec != 'none':
            codec_text = "🎥+🔊 Video+Audio"
            codec_color = (0.2, 0.6, 0.2, 1)
        elif vcodec != 'none':
            codec_text = "🎥 Video Only"
            codec_color = (0.8, 0.5, 0.2, 1)
        else:
            codec_text = "🔊 Audio Only"
            codec_color = (0.8, 0.2, 0.8, 1)
        
        codec_label = Label(
            text=codec_text,
            font_size='11sp',
            color=codec_color
        )
        middle_row.add_widget(codec_label)
        
        # Bottom row: File size
        bottom_row = BoxLayout(size_hint_y=0.3)
        
        filesize = quality.get('filesize', 0)
        if filesize:
            if filesize > 1024*1024*1024:  # GB
                size_text = f"📦 {filesize/(1024*1024*1024):.1f} GB"
            elif filesize > 1024*1024:  # MB
                size_text = f"📦 {filesize/(1024*1024):.1f} MB"
            elif filesize > 1024:  # KB
                size_text = f"📦 {filesize/1024:.0f} KB"
            else:
                size_text = f"📦 {filesize} B"
        else:
            size_text = "📦 Size: Unknown"
        
        size_label = Label(
            text=size_text,
            font_size='11sp',
            color=(0.4, 0.4, 0.4, 1)
        )
        bottom_row.add_widget(size_label)
        
        # Add all rows to button layout
        btn_layout.add_widget(top_row)
        btn_layout.add_widget(middle_row)
        btn_layout.add_widget(bottom_row)
        
        btn.add_widget(btn_layout)
        
        # Bind click event
        btn.bind(on_press=lambda instance, q=quality: self.on_quality_click(instance, q))
        
        return btn
    
    def on_quality_click(self, instance, quality):
        """Handle quality button click"""
        # Reset all buttons
        for tab in self.children[0].children:
            if hasattr(tab, 'children'):
                for child in tab.children:
                    if isinstance(child, ScrollView):
                        for btn in child.children[0].children:
                            btn.background_color = (0.95, 0.95, 0.95, 1)
        
        # Highlight selected button
        instance.background_color = (0.1, 0.5, 0.8, 0.3)
        
        # Store selected quality
        self.selected_quality = quality
        
        # Enable select button
        self.select_btn.disabled = False
        
        # Update select button text with quality info
        resolution = quality.get('resolution', 'Unknown')
        filesize = quality.get('filesize', 0)
        if filesize > 1024*1024:
            size_mb = filesize/(1024*1024)
            self.select_btn.text = f"[b]Select ({resolution}, {size_mb:.1f}MB)[/b]"
        else:
            self.select_btn.text = f"[b]Select ({resolution})[/b]"
    
    def auto_select_best(self, qualities):
        """Automatically select the best quality"""
        # Prefer formats with both video and audio
        complete_formats = [q for q in qualities 
                          if q.get('vcodec') != 'none' and q.get('acodec') != 'none']
        
        if complete_formats:
            # Sort by resolution (descending)
            complete_formats.sort(
                key=lambda x: (
                    int(x['resolution'].split('x')[1]) if 'x' in x['resolution'] 
                    and x['resolution'].split('x')[1].isdigit() else 0
                ), 
                reverse=True
            )
            best = complete_formats[0]
        elif qualities:
            best = qualities[0]
        else:
            return
        
        # Find and click the corresponding button
        self.on_quality_click(None, best)
    
    def confirm_selection(self, instance):
        """Confirm quality selection"""
        if self.selected_quality and self.callback:
            self.callback(self.selected_quality)
        self.dismiss()

class FormatPopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Output Format"
        self.size_hint = (0.85, 0.6)
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        formats = [
            {
                "name": "MP4 Video",
                "value": "mp4",
                "desc": "Standard video format\nCompatible with all devices",
                "icon": "🎥",
                "color": (0.1, 0.5, 0.8, 1)
            },
            {
                "name": "MP3 Audio",
                "value": "mp3",
                "desc": "Audio only (High Quality)\nPerfect for music",
                "icon": "🎵",
                "color": (0.2, 0.6, 0.3, 1)
            },
            {
                "name": "WEBM Video",
                "value": "webm",
                "desc": "Web optimized video\nSmaller file size",
                "icon": "🌐",
                "color": (0.8, 0.5, 0.2, 1)
            },
        ]
        
        for fmt in formats:
            fmt_btn = Button(
                text=f"{fmt['icon']}  [b]{fmt['name']}[/b]\n{fmt['desc']}",
                background_color=fmt['color'],
                color=(1, 1, 1, 1),
                markup=True,
                font_size='14sp',
                size_hint_y=0.3
            )
            fmt_btn.bind(on_press=lambda btn, f=fmt['value']: self.select_format(f))
            layout.add_widget(fmt_btn)
        
        self.add_widget(layout)
    
    def select_format(self, fmt):
        if self.callback:
            self.callback(fmt)
        self.dismiss()

class SettingsPopup(Popup):
    def __init__(self, current_settings, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Download Settings"
        self.size_hint = (0.9, 0.7)
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Download Path
        path_layout = BoxLayout(orientation='vertical', size_hint_y=0.2, spacing=dp(5))
        path_layout.add_widget(Label(text="Download Folder:", font_size='14sp'))
        self.path_input = TextInput(
            text=current_settings.get('path', 'VideMon_Downloads'),
            multiline=False,
            font_size='14sp'
        )
        path_layout.add_widget(self.path_input)
        layout.add_widget(path_layout)
        
        # Concurrent Downloads
        concurrent_layout = BoxLayout(orientation='vertical', size_hint_y=0.2, spacing=dp(5))
        concurrent_layout.add_widget(Label(text="Concurrent Downloads:", font_size='14sp'))
        self.concurrent_spinner = Spinner(
            text=str(current_settings.get('concurrent', '1')),
            values=('1', '2', '3', '4'),
            font_size='14sp'
        )
        concurrent_layout.add_widget(self.concurrent_spinner)
        layout.add_widget(concurrent_layout)
        
        # Retry Attempts
        retry_layout = BoxLayout(orientation='vertical', size_hint_y=0.2, spacing=dp(5))
        retry_layout.add_widget(Label(text="Retry Attempts:", font_size='14sp'))
        self.retry_spinner = Spinner(
            text=str(current_settings.get('retry', '3')),
            values=('1', '2', '3', '5', '10'),
            font_size='14sp'
        )
        retry_layout.add_widget(self.retry_spinner)
        layout.add_widget(retry_layout)
        
        # Action Buttons
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=dp(10))
        
        save_btn = Button(
            text="[b]Save Settings[/b]",
            background_color=(0.1, 0.6, 0.3, 1),
            color=(1, 1, 1, 1),
            markup=True
        )
        save_btn.bind(on_press=self.save_settings)
        btn_layout.add_widget(save_btn)
        
        cancel_btn = Button(
            text="[b]Cancel[/b]",
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            markup=True
        )
        cancel_btn.bind(on_press=self.dismiss)
        btn_layout.add_widget(cancel_btn)
        
        layout.add_widget(btn_layout)
        
        self.add_widget(layout)
    
    def save_settings(self, instance):
        settings = {
            'path': self.path_input.text,
            'concurrent': self.concurrent_spinner.text,
            'retry': self.retry_spinner.text
        }
        if self.callback:
            self.callback(settings)
        self.dismiss()

class VideMonApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.available_qualities = []
        self.selected_quality = None
        self.selected_format = "mp4"
        self.video_info = {}
        self.download_history = []
        self.settings = {
            'path': 'VideMon_Downloads',
            'concurrent': '1',
            'retry': '3'
        }
    
    def build(self):
        self.title = "VideMon - YouTube Downloader Pro"
        self.icon = "icon.png"
        
        # Load settings if exists
        self.load_settings()
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Header with gradient background
        with main_layout.canvas.before:
            Color(0.1, 0.5, 0.8, 1)
            self.header_bg = Rectangle(pos=(0, main_layout.height - dp(150)), 
                                      size=(Window.width, dp(150)))
        
        header = BoxLayout(orientation='vertical', size_hint_y=0.18, padding=dp(10))
        
        # App title with icon
        title_row = BoxLayout(size_hint_y=0.6)
        title_label = Label(
            text="[font=fonts/arial.ttf][size=32]🎬[/size][/font] [b]VideMon[/b]",
            font_size='28sp',
            color=(1, 1, 1, 1),
            markup=True
        )
        title_row.add_widget(title_label)
        header.add_widget(title_row)
        
        # Subtitle
        subtitle_label = Label(
            text="Professional YouTube Video & Playlist Downloader",
            font_size='12sp',
            color=(0.9, 0.9, 0.9, 1)
        )
        header.add_widget(subtitle_label)
        
        main_layout.add_widget(header)
        
        # Content Card
        content_card = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        with content_card.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=content_card.pos, size=content_card.size, radius=[dp(15)])
        
        # URL Input Section
        url_section = BoxLayout(orientation='vertical', size_hint_y=0.2, spacing=dp(5))
        url_section.add_widget(Label(
            text="YouTube URL:",
            font_size='14sp',
            color=(0.3, 0.3, 0.3, 1)
        ))
        
        url_input_layout = BoxLayout(spacing=dp(5))
        self.url_input = TextInput(
            hint_text="Paste YouTube video or playlist URL here...",
            multiline=False,
            font_size='14sp',
            background_color=(0.98, 0.98, 0.98, 1),
            padding_x=dp(15),
            padding_y=dp(12)
        )
        url_input_layout.add_widget(self.url_input)
        
        # Paste button
        paste_btn = Button(
            text="📋",
            size_hint_x=0.15,
            font_size='18sp',
            background_color=(0.9, 0.9, 0.9, 1)
        )
        paste_btn.bind(on_press=self.paste_from_clipboard)
        url_input_layout.add_widget(paste_btn)
        
        url_section.add_widget(url_input_layout)
        content_card.add_widget(url_section)
        
        # Quick Settings Row
        quick_settings = BoxLayout(size_hint_y=0.15, spacing=dp(10))
        
        self.quality_btn = Button(
            text="⚙️ Select Quality",
            background_color=(0.95, 0.95, 0.95, 1),
            color=(0.3, 0.3, 0.3, 1),
            font_size='12sp'
        )
        self.quality_btn.bind(on_press=self.show_quality_popup)
        quick_settings.add_widget(self.quality_btn)
        
        self.format_btn = Button(
            text="🎥 MP4",
            background_color=(0.95, 0.95, 0.95, 1),
            color=(0.3, 0.3, 0.3, 1),
            font_size='12sp'
        )
        self.format_btn.bind(on_press=self.show_format_popup)
        quick_settings.add_widget(self.format_btn)
        
        settings_btn = Button(
            text="⚙️ Settings",
            background_color=(0.95, 0.95, 0.95, 1),
            color=(0.3, 0.3, 0.3, 1),
            font_size='12sp'
        )
        settings_btn.bind(on_press=self.show_settings_popup)
        quick_settings.add_widget(settings_btn)
        
        content_card.add_widget(quick_settings)
        
        # Action Buttons
        action_buttons = BoxLayout(size_hint_y=0.18, spacing=dp(10))
        
        self.info_btn = StyledButton(
            text="[b]📊 GET VIDEO INFO[/b]",
            font_size='14sp',
            color=(1, 1, 1, 1)
        )
        self.info_btn.bind(on_press=self.get_video_info_and_qualities)
        action_buttons.add_widget(self.info_btn)
        
        self.download_btn = StyledButton(
            text="[b]⬇️ DOWNLOAD NOW[/b]",
            font_size='14sp',
            color=(1, 1, 1, 1),
            background_color=(0.1, 0.6, 0.3, 1)
        )
        self.download_btn.bind(on_press=self.start_download)
        action_buttons.add_widget(self.download_btn)
        
        content_card.add_widget(action_buttons)
        
        # Progress Section
        progress_section = BoxLayout(orientation='vertical', size_hint_y=0.15, spacing=dp(5))
        
        progress_header = BoxLayout(size_hint_y=0.3)
        progress_header.add_widget(Label(
            text="Download Progress:",
            font_size='12sp',
            color=(0.4, 0.4, 0.4, 1)
        ))
        self.percent_label = Label(
            text="0%",
            font_size='12sp',
            color=(0.1, 0.5, 0.8, 1)
        )
        progress_header.add_widget(self.percent_label)
        progress_section.add_widget(progress_header)
        
        self.progress_bar = ProgressBar(
            max=100,
            size_hint_y=0.4
        )
        progress_section.add_widget(self.progress_bar)
        
        self.status_label = Label(
            text="Ready to download",
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=0.3
        )
        progress_section.add_widget(self.status_label)
        
        content_card.add_widget(progress_section)
        
        # Stats Row
        stats_row = BoxLayout(size_hint_y=0.1)
        self.stats_label = Label(
            text="Downloads: 0 | Storage: 0 MB",
            font_size='11sp',
            color=(0.6, 0.6, 0.6, 1)
        )
        stats_row.add_widget(self.stats_label)
        content_card.add_widget(stats_row)
        
        main_layout.add_widget(content_card)
        
        # Log Section
        log_card = BoxLayout(orientation='vertical', size_hint_y=0.35, padding=dp(10))
        with log_card.canvas.before:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=log_card.pos, size=log_card.size, radius=[dp(10)])
        
        log_header = BoxLayout(size_hint_y=0.15)
        log_header.add_widget(Label(
            text="[b]Activity Log[/b]",
            font_size='14sp',
            color=(0.3, 0.3, 0.3, 1),
            markup=True
        ))
        
        clear_log_btn = Button(
            text="🗑️ Clear",
            size_hint_x=0.3,
            font_size='11sp',
            background_color=(0.95, 0.95, 0.95, 1)
        )
        clear_log_btn.bind(on_press=self.clear_log)
        log_header.add_widget(clear_log_btn)
        log_card.add_widget(log_header)
        
        # Log scroll view
        scroll = ScrollView()
        self.log_layout = GridLayout(cols=1, spacing=dp(2), size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        scroll.add_widget(self.log_layout)
        log_card.add_widget(scroll)
        
        main_layout.add_widget(log_card)
        
        # Footer
        footer = BoxLayout(orientation='vertical', size_hint_y=0.08, padding=dp(5))
        
        # Separator
        with footer.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            Rectangle(pos=footer.pos, size=footer.size)
        
        footer_text = Label(
            text="[size=11][color=#666666]Powered By :[/color] [b][color=#1a5fb4]Mina A. Soliman[/color][/b] | [color=#666666]VideMon v1.0[/color][/size]",
            markup=True,
            valign='middle',
            halign='center'
        )
        footer.add_widget(footer_text)
        
        main_layout.add_widget(footer)
        
        # Update stats
        self.update_stats()
        
        return main_layout
    
    def paste_from_clipboard(self, instance):
        """Paste from clipboard to URL input"""
        try:
            import pyperclip
            clipboard_text = pyperclip.paste()
            if clipboard_text and ('youtube.com' in clipboard_text or 'youtu.be' in clipboard_text):
                self.url_input.text = clipboard_text
                self.add_log("URL pasted from clipboard", "success")
        except:
            self.add_log("Clipboard not available", "warning")
    
    def show_quality_popup(self, instance):
        """Show enhanced quality selection popup"""
        if not self.available_qualities:
            self.show_popup("Information", "Please fetch video information first by clicking 'GET VIDEO INFO' button.")
            return
        
        video_title = self.video_info.get('title', 'Video')
        popup = EnhancedQualityPopup(
            self.available_qualities, 
            self.on_quality_selected,
            video_title
        )
        popup.open()
    
    def on_quality_selected(self, quality):
        """Handle quality selection from popup"""
        self.selected_quality = quality
        resolution = quality.get('resolution', 'Unknown')
        format_note = quality.get('format_note', '')
        self.quality_btn.text = f"📊 {resolution}"
        
        # Show quality info
        filesize = quality.get('filesize', 0)
        if filesize:
            size_mb = filesize / (1024 * 1024)
            quality_info = f"{resolution} ({format_note}) - {size_mb:.1f}MB"
        else:
            quality_info = f"{resolution} ({format_note})"
        
        self.add_log(f"Selected quality: {quality_info}", "success")
        self.update_status(f"Quality set to: {resolution}")
    
    def show_format_popup(self, instance):
        """Show format selection popup"""
        popup = FormatPopup(self.on_format_selected)
        popup.open()
    
    def on_format_selected(self, fmt):
        """Handle format selection"""
        self.selected_format = fmt
        format_names = {
            "mp4": "🎥 MP4",
            "mp3": "🎵 MP3", 
            "webm": "🌐 WEBM"
        }
        self.format_btn.text = format_names.get(fmt, fmt.upper())
        self.add_log(f"Selected format: {fmt.upper()}", "success")
    
    def show_settings_popup(self, instance):
        """Show settings popup"""
        popup = SettingsPopup(self.settings, self.on_settings_saved)
        popup.open()
    
    def on_settings_saved(self, settings):
        """Handle settings save"""
        self.settings = settings
        self.save_settings()
        self.add_log("Settings saved successfully", "success")
    
    def get_video_info_and_qualities(self, instance):
        """Fetch video information and available qualities"""
        url = self.url_input.text.strip()
        if not url:
            self.show_popup("Error", "Please enter a YouTube URL first.")
            return
        
        if not ('youtube.com' in url or 'youtu.be' in url):
            self.show_popup("Error", "Please enter a valid YouTube URL.")
            return
        
        self.update_status("🔍 Fetching video information...", (0.1, 0.5, 0.8, 1))
        self.add_log(f"Fetching info for: {url[:60]}...", "info")
        
        # Disable buttons during fetch
        self.info_btn.disabled = True
        self.download_btn.disabled = True
        
        def fetch_info():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'listformats': True,
                }
                
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Store video info
                    self.video_info = {
                        'title': info.get('title', 'Unknown Video'),
                        'duration': info.get('duration', 0),
                        'uploader': info.get('uploader', 'Unknown'),
                        'views': info.get('view_count', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'description': info.get('description', '')[:200] + '...',
                        'url': info.get('webpage_url', url)
                    }
                    
                    # Extract and format qualities
                    self.available_qualities = []
                    formats = info.get('formats', [])
                    
                    for fmt in formats:
                        quality_info = {
                            'format_id': fmt.get('format_id', ''),
                            'resolution': fmt.get('resolution', 'Unknown'),
                            'format_note': fmt.get('format_note', ''),
                            'ext': fmt.get('ext', ''),
                            'filesize': fmt.get('filesize', 0),
                            'vcodec': fmt.get('vcodec', 'none'),
                            'acodec': fmt.get('acodec', 'none'),
                            'fps': fmt.get('fps', 0),
                            'tbr': fmt.get('tbr', 0)  # Average bitrate
                        }
                        self.available_qualities.append(quality_info)
                    
                    # Sort by quality (resolution)
                    self.available_qualities.sort(
                        key=lambda x: self.get_resolution_value(x['resolution']),
                        reverse=True
                    )
                    
                    # Update UI on main thread
                    Clock.schedule_once(lambda dt: self.on_info_fetched(info))
                    
            except Exception as e:
                error_msg = str(e)
                Clock.schedule_once(lambda dt: self.on_info_error(error_msg))
        
        threading.Thread(target=fetch_info, daemon=True).start()
    
    def get_resolution_value(self, resolution):
        """Convert resolution string to numeric value for sorting"""
        if 'x' in resolution:
            try:
                return int(resolution.split('x')[1])
            except:
                return 0
        elif 'p' in resolution:
            try:
                return int(resolution.replace('p', ''))
            except:
                return 0
        return 0
    
    def on_info_fetched(self, info):
        """Handle successful info fetch"""
        # Enable buttons
        self.info_btn.disabled = False
        self.download_btn.disabled = False
        
        # Show video info
        title = self.video_info['title']
        duration = self.video_info['duration']
        uploader = self.video_info['uploader']
        views = self.video_info['views']
        
        # Format duration
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        if hours > 0:
            duration_str = f"{hours}h {minutes}m {seconds}s"
        else:
            duration_str = f"{minutes}m {seconds}s"
        
        info_text = f"[b]{title}[/b]\n\n"
        info_text += f"⏱️ Duration: {duration_str}\n"
        info_text += f"👤 Uploader: {uploader}\n"
        info_text += f"👁️ Views: {views:,}\n"
        info_text += f"📊 Qualities: {len(self.available_qualities)} available\n\n"
        info_text += "Click 'Select Quality' to choose your preferred quality."
        
        self.show_popup("Video Information", info_text)
        
        # Update status
        self.update_status(f"✅ Found: {title[:40]}...", (0.2, 0.6, 0.2, 1))
        self.add_log(f"Video info fetched: {len(self.available_qualities)} qualities available", "success")
        
        # Enable quality button
        self.quality_btn.background_color = (0.1, 0.5, 0.8, 1)
        self.quality_btn.color = (1, 1, 1, 1)
    
    def on_info_error(self, error_msg):
        """Handle info fetch error"""
        self.info_btn.disabled = False
        self.download_btn.disabled = False
        
        self.show_popup("Error", f"Failed to fetch video information:\n\n{error_msg}")
        self.update_status("❌ Failed to fetch info", (0.8, 0.2, 0.2, 1))
        self.add_log(f"Error: {error_msg}", "error")
    
    def start_download(self, instance):
        """Start download process"""
        if not self.url_input.text.strip():
            self.show_popup("Error", "Please enter a YouTube URL.")
            return
        
        if not self.selected_quality:
            self.show_popup("Info", "Please select a quality first.")
            return
        
        # Get download path
        download_path = self.settings['path']
        
        # Create directory
        try:
            os.makedirs(download_path, exist_ok=True)
        except Exception as e:
            self.show_popup("Error", f"Cannot create download folder:\n{str(e)}")
            return
        
        # Disable buttons
        self.download_btn.disabled = True
        self.info_btn.disabled = True
        self.download_btn.text = "[b]⏳ DOWNLOADING...[/b]"
        
        # Start download
        threading.Thread(
            target=self.download_content,
            args=(download_path,),
            daemon=True
        ).start()
    
    def download_content(self, download_path):
        """Download the content"""
        try:
            url = self.url_input.text.strip()
            
            # Configure download options
            if self.selected_format == 'mp3':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': f'{download_path}/%(title)s.%(ext)s',
                    'progress_hooks': [self.progress_hook],
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': False,
                }
            else:
                ydl_opts = {
                    'format': self.selected_quality['format_id'],
                    'merge_output_format': self.selected_format,
                    'outtmpl': f'{download_path}/%(title)s.%(ext)s',
                    'progress_hooks': [self.progress_hook],
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': False,
                    'retries': int(self.settings['retry']),
                }
            
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Record download
                download_record = {
                    'title': info.get('title', 'Unknown'),
                    'url': url,
                    'quality': self.selected_quality['resolution'],
                    'format': self.selected_format,
                    'path': download_path,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'size': os.path.getsize(f"{download_path}/{info.get('title', 'video')}.{self.selected_format}")
                }
                self.download_history.append(download_record)
                self.save_download_history()
                
                # Show success message
                success_msg = f"[b]✅ Download Complete![/b]\n\n"
                success_msg += f"📹 Title: {info.get('title', 'Unknown')}\n"
                success_msg += f"📊 Quality: {self.selected_quality['resolution']}\n"
                success_msg += f"📁 Format: {self.selected_format.upper()}\n"
                success_msg += f"💾 Saved to: {download_path}/\n\n"
                success_msg += "Click OK to continue."
                
                Clock.schedule_once(lambda dt: self.show_popup("Success", success_msg))
                
                self.add_log(f"Download complete: {info.get('title', 'Unknown')[:50]}...", "success")
                self.update_status("✅ Download completed!", (0.2, 0.6, 0.2, 1))
                self.update_progress(100)
                
        except Exception as e:
            error_msg = str(e)
            Clock.schedule_once(lambda dt: self.show_popup(
                "Download Error", 
                f"Download failed:\n\n{error_msg}\n\nPlease try again."
            ))
            self.update_status("❌ Download failed", (0.8, 0.2, 0.2, 1))
            self.add_log(f"Download error: {error_msg}", "error")
        
        finally:
            # Re-enable buttons
            Clock.schedule_once(lambda dt: self.enable_buttons())
            Clock.schedule_once(lambda dt: self.update_stats())
    
    def progress_hook(self, d):
        """Handle download progress updates"""
        if d['status'] == 'downloading':
            if '_percent_str' in d:
                percent_str = d['_percent_str'].strip()
                if '%' in percent_str:
                    try:
                        percentage = float(percent_str.replace('%', ''))
                        self.update_progress(percentage)
                        
                        # Get download speed
                        speed = d.get('speed', 0)
                        if speed:
                            speed_mb = speed / (1024 * 1024)
                            speed_text = f"{speed_mb:.1f} MB/s"
                        else:
                            speed_text = "Calculating..."
                        
                        # Get ETA
                        eta = d.get('eta', 0)
                        if eta:
                            eta_min = eta // 60
                            eta_sec = eta % 60
                            if eta_min > 0:
                                eta_text = f"{eta_min}m {eta_sec}s"
                            else:
                                eta_text = f"{eta_sec}s"
                        else:
                            eta_text = "Calculating..."
                        
                        status_text = f"⬇️ {percentage:.1f}% | {speed_text} | ETA: {eta_text}"
                        self.update_status(status_text, (0.1, 0.5, 0.8, 1))
                        
                    except:
                        pass
        
        elif d['status'] == 'finished':
            self.update_status("✅ Processing complete!", (0.2, 0.6, 0.2, 1))
    
    def enable_buttons(self):
        """Re-enable all buttons"""
        self.download_btn.disabled = False
        self.info_btn.disabled = False
        self.download_btn.text = "[b]⬇️ DOWNLOAD NOW[/b]"
    
    def update_progress(self, value):
        """Update progress bar"""
        def update(dt):
            self.progress_bar.value = value
            self.percent_label.text = f"{value:.1f}%"
        Clock.schedule_once(update)
    
    def update_status(self, message, color=(0.5, 0.5, 0.5, 1)):
        """Update status label"""
        def update(dt):
            self.status_label.text = message
            self.status_label.color = color
        Clock.schedule_once(update)
    
    def add_log(self, message, message_type="info"):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Define colors for different message types
        colors = {
            "error": (0.8, 0.2, 0.2, 1),
            "success": (0.2, 0.6, 0.2, 1),
            "warning": (0.9, 0.6, 0.1, 1),
            "info": (0.3, 0.3, 0.3, 1)
        }
        
        # Define icons for different message types
        icons = {
            "error": "❌",
            "success": "✅",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        color = colors.get(message_type, (0.3, 0.3, 0.3, 1))
        icon = icons.get(message_type, "ℹ️")
        
        def update_log(dt):
            log_entry = BoxLayout(size_hint_y=None, height=dp(25), spacing=dp(5))
            
            # Timestamp
            time_label = Label(
                text=f"[color=666666]{timestamp}[/color]",
                size_hint_x=0.25,
                font_size='10sp',
                markup=True
            )
            log_entry.add_widget(time_label)
            
            # Icon
            icon_label = Label(
                text=icon,
                size_hint_x=0.1,
                font_size='12sp'
            )
            log_entry.add_widget(icon_label)
            
            # Message
            msg_label = Label(
                text=message,
                size_hint_x=0.65,
                font_size='11sp',
                color=color,
                halign='left',
                text_size=(dp(250), None)
            )
            msg_label.bind(size=msg_label.setter('text_size'))
            log_entry.add_widget(msg_label)
            
            self.log_layout.add_widget(log_entry)
            
            # Keep only last 20 log entries
            if len(self.log_layout.children) > 20:
                self.log_layout.remove_widget(self.log_layout.children[-1])
        
        Clock.schedule_once(update_log)
    
    def clear_log(self, instance):
        """Clear activity log"""
        self.log_layout.clear_widgets()
        self.add_log("Log cleared", "info")
    
    def update_stats(self):
        """Update download statistics"""
        total_downloads = len(self.download_history)
        
        # Calculate total storage used
        total_size = 0
        for download in self.download_history:
            total_size += download.get('size', 0)
        
        total_size_mb = total_size / (1024 * 1024)
        
        self.stats_label.text = f"📥 Downloads: {total_downloads} | 💾 Storage: {total_size_mb:.1f} MB"
    
    def show_popup(self, title, content):
        """Show a popup message"""
        popup = Popup(
            title=title,
            content=Label(text=content, markup=True),
            size_hint=(0.85, 0.5)
        )
        popup.open()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('videmon_settings.json'):
                with open('videmon_settings.json', 'r') as f:
                    self.settings = json.load(f)
            
            if os.path.exists('videmon_history.json'):
                with open('videmon_history.json', 'r') as f:
                    self.download_history = json.load(f)
        except:
            pass
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open('videmon_settings.json', 'w') as f:
                json.dump(self.settings, f)
        except:
            pass
    
    def save_download_history(self):
        """Save download history"""
        try:
            with open('videmon_history.json', 'w') as f:
                json.dump(self.download_history, f)
        except:
            pass

if __name__ == '__main__':
    VideMonApp().run()