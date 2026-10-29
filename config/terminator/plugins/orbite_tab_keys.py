"""Keypad-friendly native tabs; shortcuts are handled before reaching tmux."""
from weakref import WeakKeyDictionary
from gi.repository import Gdk, GObject, Gtk
from terminatorlib import plugin
from terminatorlib.notebook import Notebook
from terminatorlib.terminator import Terminator

AVAILABLE = ['OrbiteTabKeys']


class OrbiteTabKeys(plugin.Plugin):
    capabilities = []

    def __init__(self):
        self._windows = WeakKeyDictionary()
        self._hook = GObject.add_emission_hook(Gtk.Window, 'map', self._on_map)
        for window in Terminator().windows:
            self._bind(window)

    def _on_map(self, widget, *args):
        if isinstance(widget, Gtk.Window) and widget.get_style_context().has_class(
                'terminator-terminal-window'):
            self._bind(widget)
        return True

    def _bind(self, window):
        if window not in self._windows:
            self._windows[window] = window.connect('key-press-event', self._on_key)

    def _on_key(self, window, event):
        notebook = window.get_child()
        if not isinstance(notebook, Notebook) or not notebook.get_n_pages():
            return False
        mods = event.state
        alt = bool(mods & Gdk.ModifierType.MOD1_MASK)
        control = bool(mods & Gdk.ModifierType.CONTROL_MASK)
        if mods & Gdk.ModifierType.SUPER_MASK:
            return False
        if alt and not control:
            keypad = {
                Gdk.KEY_KP_1: 0, Gdk.KEY_KP_End: 0,
                Gdk.KEY_KP_2: 1, Gdk.KEY_KP_Down: 1,
                Gdk.KEY_KP_3: 2, Gdk.KEY_KP_Next: 2,
                Gdk.KEY_KP_4: 3, Gdk.KEY_KP_Left: 3,
                Gdk.KEY_KP_5: 4, Gdk.KEY_KP_Begin: 4,
                Gdk.KEY_KP_6: 5, Gdk.KEY_KP_Right: 5,
                Gdk.KEY_KP_7: 6, Gdk.KEY_KP_Home: 6,
                Gdk.KEY_KP_8: 7, Gdk.KEY_KP_Up: 7,
                Gdk.KEY_KP_9: 8, Gdk.KEY_KP_Prior: 8,
                Gdk.KEY_KP_0: 9, Gdk.KEY_KP_Insert: 9,
            }
            index = keypad.get(event.keyval)
            if index is not None:
                if index < notebook.get_n_pages():
                    notebook.set_current_page(index)
                return True
        if control and not alt and event.keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            backward = bool(mods & Gdk.ModifierType.SHIFT_MASK) or event.keyval == Gdk.KEY_ISO_Left_Tab
            notebook.set_current_page((notebook.get_current_page() + (-1 if backward else 1))
                                      % notebook.get_n_pages())
            return True
        return False

    def unload(self):
        GObject.remove_emission_hook(Gtk.Window, 'map', self._hook)
        for window, handler in list(self._windows.items()):
            window.disconnect(handler)
        self._windows.clear()
