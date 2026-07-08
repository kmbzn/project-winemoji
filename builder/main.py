import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango
import os
import threading
from processor import build_winemoji

# Wayland에서 아이콘을 매칭하기 위해 prgname을 .desktop 파일 이름과 동일하게 설정합니다.
GLib.set_prgname('winemoji')

class WinemojiApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Winemoji Builder")
        self.set_default_size(600, 480)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)
            Gtk.Window.set_default_icon_from_file(icon_path)

        # Explicitly force GTK to use the exact system theme and color scheme
        try:
            import subprocess
            
            # 1. Force Theme Name
            theme_res = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], capture_output=True, text=True)
            theme_name = theme_res.stdout.strip().strip("'")
            if theme_name:
                Gtk.Settings.get_default().set_property("gtk-theme-name", theme_name)
                
            # 2. Force Dark Mode Preference
            color_res = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'], capture_output=True, text=True)
            if 'prefer-dark' in color_res.stdout:
                Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
        except Exception:
            pass

        # HeaderBar for true Ubuntu Native Look
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "Winemoji Builder"
        self.set_titlebar(hb)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        self.add(vbox)

        # Subtitle
        subtitle = Gtk.Label(label="Automated Font Subsetting & Emoji Patching")
        subtitle.get_style_context().add_class("dim-label")
        vbox.pack_start(subtitle, False, False, 0)

        # Font Selection row
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label="Base Font:")
        hbox.pack_start(label, False, False, 0)
        
        self.file_chooser = Gtk.FileChooserButton(title="Select Base Font", action=Gtk.FileChooserAction.OPEN)
        
        sys_fonts = "/usr/local/share/fonts"
        if not os.path.exists(sys_fonts):
            sys_fonts = os.path.expanduser("~/.local/share/fonts")
        if os.path.exists(sys_fonts):
            self.file_chooser.set_current_folder(sys_fonts)
            
        font_filter = Gtk.FileFilter()
        font_filter.set_name("Fonts")
        font_filter.add_pattern("*.ttf")
        font_filter.add_pattern("*.otf")
        self.file_chooser.add_filter(font_filter)
        hbox.pack_start(self.file_chooser, True, True, 0)
        vbox.pack_start(hbox, False, False, 0)

        # Log View
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        
        font_desc = Pango.FontDescription("Ubuntu Mono 11")
        self.textview.override_font(font_desc)
        
        self.textbuffer = self.textview.get_buffer()
        self.textbuffer.set_text("Ready to build...\n")
        scrolled_window.add(self.textview)
        vbox.pack_start(scrolled_window, True, True, 0)

        # Progress bar
        self.progress = Gtk.ProgressBar()
        vbox.pack_start(self.progress, False, False, 0)

        # Build Button
        self.build_btn = Gtk.Button(label="Build Winemoji")
        self.build_btn.get_style_context().add_class("suggested-action")
        self.build_btn.set_size_request(-1, 50)
        self.build_btn.connect("clicked", self.on_build_clicked)
        vbox.pack_start(self.build_btn, False, False, 0)

    def log(self, message):
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.insert(end_iter, message + "\n")
        
        mark = self.textbuffer.create_mark("end", self.textbuffer.get_end_iter(), False)
        self.textview.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
        return False

    def on_build_clicked(self, widget):
        base_font = self.file_chooser.get_filename()
        if not base_font:
            self.show_error("Please select a base font file.")
            return

        emoji_font = os.path.join(os.path.dirname(__file__), "assets", "NotoEmoji.ttf")
        if not os.path.exists(emoji_font):
            self.show_error("Emoji font asset is missing.")
            return

        base_dir = os.path.dirname(base_font)
        base_name, _ = os.path.splitext(os.path.basename(base_font))

        if not os.access(base_dir, os.W_OK):
            base_dir = os.path.expanduser("~/.local/share/fonts")
            os.makedirs(base_dir, exist_ok=True)

        output_font = os.path.join(base_dir, f"{base_name}-winemoji.ttf")

        self.build_btn.set_sensitive(False)
        self.file_chooser.set_sensitive(False)
        self.build_btn.set_label("Building...")
        self.textbuffer.set_text("")
        self.log(f"Target Output Path: {output_font}")
        
        self.pulse_timer = GLib.timeout_add(100, self.pulse_progress)

        thread = threading.Thread(target=self.build_thread, args=(base_font, emoji_font, output_font))
        thread.start()

    def pulse_progress(self):
        self.progress.pulse()
        return True

    def build_thread(self, base_font, emoji_font, output_font):
        try:
            def progress_cb(msg):
                GLib.idle_add(self.log, msg)

            build_winemoji(base_font, emoji_font, output_font, progress_callback=progress_cb)
            GLib.idle_add(self.build_success)
        except Exception as e:
            GLib.idle_add(self.build_error, str(e))

    def build_success(self):
        GLib.source_remove(self.pulse_timer)
        self.progress.set_fraction(1.0)
        self.build_btn.set_sensitive(True)
        self.file_chooser.set_sensitive(True)
        self.build_btn.set_label("Build Winemoji")
        
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Success"
        )
        dialog.format_secondary_text("Winemoji built successfully!")
        dialog.run()
        dialog.destroy()
        return False

    def build_error(self, error_msg):
        GLib.source_remove(self.pulse_timer)
        self.progress.set_fraction(0.0)
        self.build_btn.set_sensitive(True)
        self.file_chooser.set_sensitive(True)
        self.build_btn.set_label("Build Winemoji")
        
        self.log(f"ERROR: {error_msg}")
        self.show_error("An error occurred during build. Check the log for details.")
        return False
        
    def show_error(self, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(msg)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    app = WinemojiApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
