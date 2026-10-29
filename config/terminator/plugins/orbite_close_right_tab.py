"""Ctrl+Shift+Delete kills only the tmux session(s) in the rightmost native tab."""
import os
from pathlib import Path
import subprocess
import shutil
from weakref import WeakKeyDictionary, WeakSet

from gi.repository import Gdk, GLib, GObject, Gtk
from terminatorlib import plugin
from terminatorlib.notebook import Notebook
from terminatorlib.terminator import Terminator

AVAILABLE = ['OrbiteCloseRightTab']


class OrbiteCloseRightTab(plugin.Plugin):
    capabilities = []

    def __init__(self):
        self._windows = WeakKeyDictionary()
        self._busy = WeakSet()
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
        required = Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK
        unwanted = Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.SUPER_MASK
        if event.state & required != required or event.state & unwanted:
            return False
        if event.keyval not in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete,
                                Gdk.KEY_KP_Decimal, Gdk.KEY_KP_Separator):
            return False
        if window not in self._busy:
            self._busy.add(window)
            GLib.idle_add(self._kill_rightmost, window)
        return True

    @staticmethod
    def _terminals(widget):
        if hasattr(widget, 'vte') and hasattr(widget, 'pid'):
            return [widget]
        result = []
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                result.extend(OrbiteCloseRightTab._terminals(child))
        return result

    def _kill_rightmost(self, window):
        try:
            root = window.get_child()
            page = (root.get_nth_page(root.get_n_pages() - 1)
                    if isinstance(root, Notebook) else root)
            terminals = self._terminals(page)
            if not terminals:
                return False
            tmux = [(shutil.which('tmux') or '/usr/bin/tmux'), '-L',
                    os.environ.get('ORBITE_TMUX_SOCKET', 'default')]
            result = subprocess.run(
                tmux + ['list-clients', '-F', '#{client_pid}\t#{session_id}'],
                check=True, capture_output=True, text=True, timeout=2)
            clients = {int(pid): session for pid, session in
                       (line.split('\t') for line in result.stdout.splitlines())}
            # Resolve every terminal first: never guess a session name or index.
            if any(terminal.pid not in clients for terminal in terminals):
                raise ValueError('La session tmux de cet onglet ne peut pas être identifiée.')
            sessions = {clients[terminal.pid] for terminal in terminals}
            for session in sessions:
                subprocess.run(tmux + ['kill-session', '-t', session], check=True,
                               capture_output=True, text=True, timeout=2)
            # Terminator's existing exit_action=close removes the exited tab.
        except (ValueError, subprocess.SubprocessError, OSError) as error:
            dialog = Gtk.MessageDialog(
                transient_for=window, modal=True, message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE, text='Fermeture de la session impossible')
            dialog.format_secondary_text(str(error))
            dialog.run()
            dialog.destroy()
        finally:
            self._busy.discard(window)
        return False

    def unload(self):
        GObject.remove_emission_hook(Gtk.Window, 'map', self._hook)
        for window, handler in list(self._windows.items()):
            window.disconnect(handler)
        self._windows.clear()
