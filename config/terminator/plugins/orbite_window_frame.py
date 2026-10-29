"""Apply the borderless maximized window setting without restarting terminals."""
from gi.repository import GLib, GObject, Gtk
from terminatorlib import plugin
from terminatorlib.terminator import Terminator

AVAILABLE = ['OrbiteWindowFrame']


class OrbiteWindowFrame(plugin.Plugin):
    capabilities = []

    def __init__(self):
        self._hook = GObject.add_emission_hook(Gtk.Window, 'map', self._on_map)
        for window in Terminator().windows:
            self._apply(window)

    def _on_map(self, widget, *args):
        if isinstance(widget, Gtk.Window) and widget.get_style_context().has_class(
                'terminator-terminal-window'):
            GLib.idle_add(self._apply, widget)
        return True

    @staticmethod
    def _apply(window):
        window.set_decorated(False)
        window.maximize()
        return False

    def unload(self):
        GObject.remove_emission_hook(Gtk.Window, 'map', self._hook)
