"""Isolated functional tests: no writes to the real HOME or installed VS Code."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from helpers import stop_tmux

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('orbite_install', ROOT/'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='orbite-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)/'home with spaces'
        self.home.mkdir()
        self.app = Path(self.temp.name)/'fake code/resources/app'
        self.css = self.app/'out/vs/workbench/workbench.desktop.main.css'
        self.css.parent.mkdir(parents=True)
        self.css.write_text('body { color: white; }\n')
        self.product = self.app/'product.json'
        self.product.write_text(json.dumps({'commit':'test','checksums':{'vs/workbench/workbench.desktop.main.css':'old'}}))
        self.code = Path(self.temp.name)/'fake-code'
        self.code.write_text('#!/bin/sh\nexit 0\n')
        self.code.chmod(0o755)
        self.original_zsh = '# personal config\nalias original="echo works"\n'
        (self.home/'.zshrc').write_text(self.original_zsh)
        (self.home/'.zshrc').chmod(0o600)
        (self.home/'.tmux.conf').write_text('# personal tmux\n')
        settings = self.home/'.config/Code/User/settings.json'
        settings.parent.mkdir(parents=True)
        self.original_settings = '{ // keep unrelated preferences\n "editor.tabSize": 7, "url":"https://example.org",\n}\n'
        settings.write_text(self.original_settings)

    def install(self, *extra, success=True):
        argv = [str(ROOT/'install.sh'),'--home',str(self.home),'--no-packages','--no-network',
                '--code-app',str(self.app),'--code-bin',str(self.code),*extra]
        result = subprocess.run(argv,capture_output=True,text=True)
        if success: self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return result

    def backups(self):
        return sorted((self.home/'.local/state/orbite/backups').iterdir())

    def test_install_repeat_restore_and_wallpaper(self):
        self.install()
        first = self.backups()
        zsh = (self.home/'.zshrc').read_bytes()
        settings = json.loads((self.home/'.config/Code/User/settings.json').read_text())
        self.assertEqual(settings['editor.tabSize'],7)
        self.assertEqual((self.home/'.zshrc').stat().st_mode & 0o777,0o600)
        self.assertEqual(settings['workbench.colorTheme'],'Orbite')
        self.assertEqual(settings['url'],'https://example.org')
        self.assertIn('home%20with%20spaces',(self.home/'.config/orbite/terminator-tabs.css').read_text())
        self.assertNotIn('@HOME@',(self.home/'.config/terminator/config').read_text())
        self.assertEqual(self.css.read_text().count('/* ORBITE WALLPAPER BEGIN */'),1)
        checksum = base64.b64encode(hashlib.sha256(self.css.read_bytes()).digest()).decode().rstrip('=')
        self.assertEqual(json.loads(self.product.read_text())['checksums']['vs/workbench/workbench.desktop.main.css'],checksum)
        css_bytes = self.css.read_bytes()
        self.install()
        self.assertEqual(first,self.backups(), 'second installation must not create another backup')
        self.assertEqual(zsh,(self.home/'.zshrc').read_bytes())
        self.assertEqual(css_bytes,self.css.read_bytes())
        # Restore editor application before restoring the user config.
        subprocess.run([str(self.home/'.local/bin/orbite-vscode-wallpaper'),'--remove'],check=True,capture_output=True)
        self.assertNotIn('ORBITE WALLPAPER BEGIN',self.css.read_text())
        result = subprocess.run([str(ROOT/'install.sh'),'--restore',str(first[0])],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((self.home/'.zshrc').read_text(),self.original_zsh)
        self.assertEqual((self.home/'.config/Code/User/settings.json').read_text(),self.original_settings)
        self.assertFalse((self.home/'.local/bin/orbite-tmux').exists())

    def test_restore_refuses_new_user_changes(self):
        self.install('--skip-wallpaper')
        (self.home/'.zshrc').write_text('new personal change\n')
        result = subprocess.run([str(ROOT/'install.sh'),'--restore',str(self.backups()[0])],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.home/'.zshrc').read_text(),'new personal change\n')

    def test_invalid_settings_and_dry_run_do_not_write(self):
        self.install('--dry-run')
        self.assertFalse((self.home/'.local').exists())
        (self.home/'.config/Code/User/settings.json').write_text('{invalid')
        self.install(success=False)
        self.assertEqual((self.home/'.zshrc').read_text(),self.original_zsh)
        self.assertFalse((self.home/'.local').exists())

    @unittest.skipUnless(shutil.which('zsh') and shutil.which('tmux'),'zsh/tmux required')
    def test_real_zsh_and_tmux(self):
        self.install('--skip-wallpaper')
        env = dict(os.environ,HOME=str(self.home),ZDOTDIR=str(self.home),TERM='xterm-256color',
                   XDG_CONFIG_HOME=str(self.home/'.config'))
        env.pop('ZSH',None); env.pop('ZSH_CUSTOM',None)
        # Non-PTY zsh still initializes completions, themes and plugins.
        result = subprocess.run(['zsh','-i','-c',
            'print -- $ZSH_THEME; alias c; (( ${+functions[sudo-command-line]} )) || exit 12; '
            'zstyle -s ":completion:*:local-directories" format value; print -- $value; '
            '(( ${+functions[_zsh_highlight]} && ${+functions[_zsh_autosuggest_start]} )) || exit 13'],
            env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('c=cd',result.stdout)
        self.assertIn('#edb4cd',result.stdout)
        self.assertNotIn('command not found',result.stderr)
        socket = 'orbite-test-'+str(os.getpid())+'-'+self.home.parent.name
        tmux = [shutil.which('tmux'),'-L',socket]
        # -f loads fixture config; no connection to a user's default tmux server.
        subprocess.run(tmux+['-f',str(self.home/'.tmux.conf'),'new-session','-d','-s','fixture','-c',str(self.home),'sleep 120'],check=True,env=env,capture_output=True)
        self.addCleanup(lambda:stop_tmux(tmux))
        pane = subprocess.check_output(tmux+['display-message','-p','#{pane_id}'],text=True).strip()
        env.update(ORBITE_TMUX_SOCKET=socket,TMUX='fixture',TMUX_PANE=pane)
        result = subprocess.run([str(self.home/'.local/bin/grille'),'4'],env=env,cwd=self.home,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        panes = subprocess.check_output(tmux+['list-panes','-F','#{pane_current_path}'],text=True).splitlines()
        self.assertEqual(panes,[str(self.home)]*4)
        self.assertEqual(subprocess.check_output(tmux+['show-option','-gv','pane-border-style'],text=True).strip(),'fg=#343b4d,bg=default,nobold')


class Wallpaper(unittest.TestCase):
    def test_invalid_product_never_modifies_css(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            css = root/'out/vs/workbench/workbench.desktop.main.css'
            css.parent.mkdir(parents=True);css.write_text('original')
            (root/'product.json').write_text('{}')
            result = subprocess.run(['python3',str(ROOT/'scripts/vscode_wallpaper.py'),'--app-dir',tmp,
                '--image',str(ROOT/'assets/images/vscode.png'),'--backup-dir',str(root/'backup')],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(css.read_text(),'original')


if __name__ == '__main__': unittest.main(verbosity=2)
