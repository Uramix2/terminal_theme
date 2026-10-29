"""Wallpaper compatibility for stock Terminator versions without image support."""
import os
from weakref import WeakKeyDictionary
from gi.repository import Gdk, GLib, GObject, Gtk, Vte
from terminatorlib import plugin
from terminatorlib.terminator import Terminator

AVAILABLE = ['OrbiteWallpaper']


class OrbiteWallpaper(plugin.Plugin):
    capabilities = []

    def __init__(self):
        self._widgets = WeakKeyDictionary()
        self._provider = None
        self._screen = Gdk.Screen.get_default()
        self._hook = GObject.add_emission_hook(Gtk.Widget, 'map', self._on_map)
        self._scan()

    def _on_map(self, widget, *args):
        if isinstance(widget, Vte.Terminal):
            self._scan()
        return True

    def _scan(self):
        for terminal in Terminator().terminals:
            if hasattr(terminal, 'set_background_image') and not os.environ.get('ORBITE_WALLPAPER_CSS_ONLY'):
                continue
            if self._provider is None:
                self._provider = Gtk.CssProvider()
                self._provider.load_from_data(b'''
                    .terminator-terminal-window .terminator-profile-default {
                        background-color: transparent;
                        background-image: none;
                    }
                ''')
                Gtk.StyleContext.add_provider_for_screen(
                    self._screen, self._provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 2)
            vte = terminal.vte
            if vte is not None and vte not in self._widgets:
                self._widgets[vte] = vte.connect('style-updated', self._style_updated)
                GLib.idle_add(self._transparent, vte)

    def _style_updated(self, widget):
        GLib.idle_add(self._transparent, widget)

    @staticmethod
    def _transparent(widget):
        colour = Gdk.RGBA()
        colour.parse('rgba(0,0,0,0)')
        widget.set_color_background(colour)
        return False

    def unload(self):
        GObject.remove_emission_hook(Gtk.Widget, 'map', self._hook)
        for widget, handler in list(self._widgets.items()):
            widget.disconnect(handler)
        self._widgets.clear()
        if self._provider is not None:
            Gtk.StyleContext.remove_provider_for_screen(self._screen, self._provider)
