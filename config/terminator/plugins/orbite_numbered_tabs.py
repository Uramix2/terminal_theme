"""Compact numbered native Terminator tabs, updated only on notebook events."""
from weakref import WeakKeyDictionary, ref
from pathlib import Path

from gi.repository import Gdk, Gio, GLib, GObject, Gtk
from terminatorlib import plugin
from terminatorlib.notebook import Notebook
from terminatorlib.terminator import Terminator

AVAILABLE = ['OrbiteNumberedTabs']


class OrbiteNumberedTabs(plugin.Plugin):
    capabilities = []

    def __init__(self):
        self._css_path = Path.home() / '.config/orbite/terminator-tabs.css'
        self._css = Gtk.CssProvider()
        self._css.load_from_path(str(self._css_path))
        self._screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            self._screen, self._css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        self._monitor = Gio.File.new_for_path(str(self._css_path)).monitor_file(
            Gio.FileMonitorFlags.NONE, None)
        self._monitor.connect('changed', self._reload_css)
        self._pending = set()
        self._idle = 0
        self._labels = WeakKeyDictionary()
        self._hooks = []
        for signal in ['page-added', 'page-removed', 'page-reordered', 'switch-page']:
            hook = GObject.add_emission_hook(Gtk.Notebook, signal, self._on_pages_changed)
            self._hooks.append((signal, hook))
        # Handle notebooks already present when the plugin is enabled.
        for window in Terminator().windows:
            self._find_notebooks(window)

    def _reload_css(self, monitor, file, other_file, event):
        if event in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CREATED):
            try:
                self._css.load_from_path(str(self._css_path))
            except GLib.Error:
                pass

    def _find_notebooks(self, widget):
        if isinstance(widget, Notebook):
            self._queue(widget)
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                self._find_notebooks(child)

    def _on_pages_changed(self, notebook, *args):
        if isinstance(notebook, Notebook):
            self._queue(notebook)
        return True

    def _queue(self, notebook):
        self._pending.add(notebook)
        if not self._idle:
            self._idle = GLib.idle_add(self._refresh)

    def _refresh(self):
        self._idle = 0
        pending, self._pending = self._pending, set()
        for notebook in pending:
            for index in range(notebook.get_n_pages()):
                page = notebook.get_nth_page(index)
                label = notebook.get_tab_label(page)
                if label is None or not hasattr(label, 'set_custom_label'):
                    continue
                if label not in self._labels:
                    self._labels[label] = {
                        'text': label.get_label(), 'custom': label.get_custom_label(),
                        'number': '',
                    }
                    weak_label = ref(label)
                    handler = label.label._label.connect(
                        'notify::label',
                        lambda widget, prop, weak_label=weak_label:
                            self._keep_number(weak_label, widget))
                    self._labels[label]['handler'] = handler
                number = str(index + 1)
                self._labels[label]['number'] = number
                label.set_custom_label(number, force=True)
                notebook.child_set_property(page, 'tab-expand', False)
                notebook.child_set_property(page, 'tab-fill', False)
                hint = f'Terminal {number}'
                if index < 9:
                    hint += f' · Alt+{number}'
                label.set_tooltip_text(hint)
        return False

    def _keep_number(self, weak_label, widget):
        # Startup layouts can assign their titles after a page-added event.
        label = weak_label()
        if label is None:
            return
        state = self._labels.get(label)
        if state and state['number'] and widget.get_text() != state['number']:
            widget.set_text(state['number'])

    def unload(self):
        self._monitor.cancel()
        Gtk.StyleContext.remove_provider_for_screen(self._screen, self._css)
        for signal, hook in self._hooks:
            GObject.remove_emission_hook(Gtk.Notebook, signal, hook)
        if self._idle:
            GLib.source_remove(self._idle)
        self._pending.clear()
        for label, state in list(self._labels.items()):
            label.label._label.disconnect(state['handler'])
            text, custom = state['text'], state['custom']
            label.label._custom = custom is not None
            label.set_label(custom if custom is not None else text)
            label.set_tooltip_text(None)
        self._labels.clear()
