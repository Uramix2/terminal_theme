#!/usr/bin/env python3
"""Exercise installed Terminator plugins with a private HOME and tmux server."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def parent():
    with tempfile.TemporaryDirectory(prefix='orbite-gtk-') as tmp:
        home = Path(tmp)/'home with spaces'
        home.mkdir()
        subprocess.run([str(ROOT/'install.sh'),'--home',str(home),'--no-packages','--no-network','--skip-vscode'],check=True)
        socket = 'orbite-gtk-'+str(os.getpid())
        env = dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),ZDOTDIR=str(home),
                   PATH=str(home/'.local/bin')+':'+os.environ['PATH'],ORBITE_TMUX_SOCKET=socket,
                   ORBITE_WALLPAPER_CSS_ONLY='1',SHELL='/usr/bin/zsh')
        env.pop('TMUX',None);env.pop('TMUX_PANE',None)
        try:
            subprocess.run([sys.executable,__file__,'--child'],env=env,cwd=home,check=True,timeout=30)
        finally:
            subprocess.run([shutil.which('tmux'),'-L',socket,'kill-server'],capture_output=True)


def child():
    import gi
    gi.require_version('Gtk','3.0')
    gi.require_version('Gdk','3.0')
    gi.require_version('Vte','2.91')
    from gi.repository import Gdk, GLib, Gtk
    from terminatorlib import optionparse
    from terminatorlib.terminator import Terminator
    from terminatorlib.plugin import PluginRegistry
    sys.argv = ['terminator','--no-dbus']
    optionparse.parse_options()
    app = Terminator()
    app.set_origcwd(str(Path.home()))
    app.reconfigure()
    app.create_layout('default')
    app.layout_done()
    registry = PluginRegistry()
    registry.load_plugins()
    window = app.windows[0]
    errors = []
    socket = os.environ['ORBITE_TMUX_SOCKET']
    tmux = [shutil.which('tmux'),'-L',socket]

    def check(function):
        def wrapper():
            try: function()
            except Exception as exc:
                import traceback
                traceback.print_exc()
                errors.append(str(exc));Gtk.main_quit()
            return False
        return wrapper

    def tabs():
        expected = {'OrbiteNumberedTabs','OrbiteTabKeys','OrbiteWindowFrame','OrbiteCloseRightTab','OrbiteWallpaper'}
        assert expected <= registry.instances.keys(), str(registry.instances.keys())
        assert not window.get_decorated()
        window.tab_new()
        window.tab_new()

    def verify():
        notebook = window.get_child()
        assert notebook.get_n_pages() == 3
        labels = [notebook.get_tab_label(notebook.get_nth_page(i)).get_custom_label() for i in range(3)]
        assert labels == ['1','2','3'], labels
        clients = subprocess.check_output(tmux+['list-clients','-F','#{session_id}'],text=True).splitlines()
        assert len(clients) == len(set(clients)) == 3, clients
        assert len(registry.instances['OrbiteWallpaper']._widgets) == 3, 'wallpaper fallback missed new tabs'
        event = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        event.state = Gdk.ModifierType.MOD1_MASK
        event.keyval = Gdk.KEY_KP_End
        assert registry.instances['OrbiteTabKeys']._on_key(window,event)
        assert notebook.get_current_page() == 0
        # Capture only this isolated test window if explicitly requested.
        screenshot = os.environ.get('ORBITE_TEST_SCREENSHOT')
        if screenshot:
            width,height = window.get_size()
            Gdk.pixbuf_get_from_window(window.get_window(),0,0,width,height).savev(screenshot,'png',[],[])
        registry.instances['OrbiteCloseRightTab']._kill_rightmost(window)

    def finished():
        assert window.get_child().get_n_pages() == 2
        assert len(subprocess.check_output(tmux+['list-sessions','-F','#{session_id}'],text=True).splitlines()) == 2
        print('GTK OK: numbered tabs, keypad, separate tmux sessions, wallpaper fallback, rightmost close.')
        Gtk.main_quit()

    GLib.timeout_add(1200,check(tabs))
    GLib.timeout_add(2800,check(verify))
    GLib.timeout_add(3800,check(finished))
    Gtk.main()
    if errors: raise SystemExit(1)


if __name__ == '__main__':
    child() if '--child' in sys.argv else parent()
