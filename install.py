#!/usr/bin/env python3
"""Installateur Orbite pour Debian (bibliothèque standard)."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
BEGIN, END = '# >>> ORBITE BEGIN >>>', '# <<< ORBITE END <<<'


def run(argv, **kwargs):
    return subprocess.run([str(x) for x in argv], check=True, **kwargs)


def elevated(argv):
    return (['sudo'] if os.geteuid() else []) + [str(x) for x in argv]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def jsonc(text):
    # Preserve quoted strings, including URLs and escaped quotes, while removing comments.
    pattern = r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/'
    text = re.sub(pattern, lambda m: m[0] if m[0].startswith('"') else ' ', text)
    text = re.sub(r'("(?:\\.|[^"\\])*"|,)\s*(?=[}\]])',
                  lambda m: m[0] if m[0].startswith('"') else '', text)
    return json.loads(text)


class Writer:
    """Backups are written before each mutation, and record the expected installed content."""
    def __init__(self, home):
        self.home = home
        self.backup = home / '.local/state/orbite/backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        self.entries = []

    def save(self):
        self.backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.backup / 'manifest.json').write_text(json.dumps({'home': str(self.home), 'files': self.entries}, indent=2)+'\n')

    def write(self, relative, data, mode=None, symlink=None):
        path = self.home / relative
        if mode is None:
            mode = path.stat().st_mode & 0o777 if path.is_file() and not path.is_symlink() else 0o644
        if isinstance(data, str): data = data.encode()
        if path.is_dir() and not path.is_symlink():
            raise RuntimeError(f'Un dossier existe à la place du fichier : {path}')
        expected = {'link': symlink} if symlink is not None else {'sha256': digest(data), 'mode': mode}
        if symlink is not None and path.is_symlink() and os.readlink(path) == symlink: return
        if symlink is None and path.is_file() and not path.is_symlink() and path.read_bytes() == data and path.stat().st_mode & 0o777 == mode: return
        entry = {'path': str(relative), 'installed': expected, 'previous': None}
        if path.is_symlink():
            entry['previous'] = {'link': os.readlink(path)}
        elif path.exists():
            previous = path.read_bytes()
            self.backup.mkdir(parents=True, exist_ok=True, mode=0o700)
            name = f'{len(self.entries)}.bin'
            (self.backup/name).write_bytes(previous)
            (self.backup/name).chmod(0o600)
            entry['previous'] = {'file': name, 'mode': path.stat().st_mode & 0o777}
        self.entries.append(entry)
        self.save()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink(): path.unlink()
        if symlink is not None:
            path.symlink_to(symlink)
        else:
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.orbite-')
            try:
                with os.fdopen(fd, 'wb') as stream: stream.write(data)
                os.chmod(tmp, mode)
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)


def restore(directory, force=False):
    manifest = json.loads((directory/'manifest.json').read_text())
    home = Path(manifest['home'])
    conflicts = []
    for entry in manifest['files']:
        path = home / entry['path']
        state = entry['installed']
        valid = (path.is_symlink() and os.readlink(path) == state['link']) if 'link' in state else (
            path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == state['sha256'])
        if not valid: conflicts.append(str(path))
    if conflicts and not force:
        raise RuntimeError('Fichiers modifiés depuis l’installation ; restauration interrompue (utiliser --force pour les écraser) :\n'+'\n'.join(conflicts))
    for entry in reversed(manifest['files']):
        path = home / entry['path']
        if path.exists() or path.is_symlink(): path.unlink()
        old = entry['previous']
        if old:
            path.parent.mkdir(parents=True, exist_ok=True)
            if 'link' in old: path.symlink_to(old['link'])
            else:
                path.write_bytes((directory/old['file']).read_bytes())
                path.chmod(old['mode'])
    print('Configuration restaurée :', home)


def managed(original, body):
    if (BEGIN in original) != (END in original): raise RuntimeError('Bloc Orbite incomplet dans un fichier existant.')
    block = BEGIN+'\n'+body+'\n'+END
    if BEGIN in original:
        return re.sub(re.escape(BEGIN)+r'[\s\S]*?'+re.escape(END), lambda _: block, original)
    return original + ('\n' if original and not original.endswith('\n') else '') + '\n'+block+'\n'


def download(record):
    request = urllib.request.Request(record['url'], headers={'User-Agent': 'Orbite-installer'})
    with urllib.request.urlopen(request, timeout=90) as response: data = response.read()
    if digest(data) != record['sha256']: raise RuntimeError('SHA256 incorrect : '+record['url'])
    return data


def archive(writer, data, destination):
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as bundle:
        for item in bundle:
            name = Path(item.name)
            if name.is_absolute() or '..' in name.parts: raise RuntimeError('Archive non sûre.')
            if item.isdir(): continue
            target = Path(destination)/name
            if item.issym():
                # Git archives contain internal relative symlinks; reject escapes.
                resolved = os.path.normpath(str(name.parent/item.linkname))
                if os.path.isabs(item.linkname) or resolved.startswith('../'): raise RuntimeError('Lien non sûr.')
                writer.write(target, b'', symlink=item.linkname)
            elif item.isfile():
                writer.write(target, bundle.extractfile(item).read(), 0o755 if item.mode & 0o111 else 0o644)
            else: raise RuntimeError('Type d’archive non pris en charge.')


def dependencies(args):
    if args.no_packages: return
    release = Path('/etc/os-release').read_text()
    if not re.search(r'^ID=["\']?debian["\']?$', release, re.M):
        raise RuntimeError('Cet installateur cible Debian 12 et 13.')
    packages = ['zsh', 'tmux', 'terminator', 'fzf', 'fontconfig', 'curl', 'ca-certificates',
                'git', 'gpg', 'python3-gi', 'python3-cairo', 'python3-gi-cairo', 'python3-configobj',
                'gir1.2-gtk-3.0', 'gir1.2-vte-2.91', 'wl-clipboard', 'xclip']
    run(elevated(['apt-get', 'update']))
    run(elevated(['apt-get', 'install', '-y', *packages]))
    if not shutil.which('code') and not args.skip_vscode:
        arch = {'x86_64':'x64','aarch64':'arm64'}.get(platform.machine())
        if not arch: raise RuntimeError('Architecture non prise en charge pour Code.')
        # Official Microsoft HTTPS package; apt resolves its dependencies.
        with tempfile.TemporaryDirectory(prefix='orbite-code-') as tmp:
            package = Path(tmp)/'code.deb'
            with urllib.request.urlopen(f'https://update.code.visualstudio.com/latest/linux-deb-{arch}/stable', timeout=120) as response:
                package.write_bytes(response.read())
            os.chmod(tmp, 0o755)
            run(elevated(['apt-get', 'install', '-y', package]))


def find_app(explicit=None):
    if explicit: return Path(explicit).resolve()
    paths = [Path('/usr/share/code/resources/app'), Path('/usr/lib/code/resources/app'), Path('/opt/visual-studio-code/resources/app')]
    exe = shutil.which('code')
    if exe: paths.insert(0, Path(exe).resolve().parent.parent/'resources/app')
    return next((p for p in paths if (p/'product.json').is_file()), None)


def vsix():
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
        def add(name, data):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data)
        for source in sorted((ROOT/'vscode/extension').rglob('*')):
            if source.is_file():
                info = zipfile.ZipInfo('extension/'+str(source.relative_to(ROOT/'vscode/extension')), (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, source.read_bytes())
        add('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/json"/></Types>')
        add('extension.vsixmanifest', '''<?xml version="1.0"?><PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="en-US" Id="orbite" Version="1.1.0" Publisher="uramix"/><DisplayName>Orbite</DisplayName><Description>Orbite space theme</Description><Tags>theme</Tags><Categories>Themes</Categories><GalleryFlags>Public</GalleryFlags><Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.50.0"/></Properties></Metadata><Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/><Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets></PackageManifest>''')
    return output.getvalue()


def install(args):
    home = args.home.expanduser().resolve()
    if os.geteuid() == 0 and home == Path('/root'):
        raise RuntimeError('Lancer ./install.sh avec ton utilisateur habituel, sans sudo.')
    if args.no_network and not args.no_packages: raise RuntimeError('--no-network nécessite --no-packages.')
    settings_path = home/'.config/Code/User/settings.json'
    settings = jsonc(settings_path.read_text()) if settings_path.exists() and not args.skip_vscode else {}
    if not isinstance(settings, dict): raise RuntimeError('settings.json doit contenir un objet JSON.')
    theme_settings = json.loads((ROOT/'config/vscode-settings.json').read_text())
    profiles = dict(settings.get('terminal.integrated.profiles.linux') or {})
    profiles.update(theme_settings['terminal.integrated.profiles.linux'])
    settings.update(theme_settings)
    settings['terminal.integrated.profiles.linux'] = profiles
    if args.dry_run:
        print('Destination :', home)
        print('Plan : dépendances APT, images, Zsh, tmux, Terminator, thème et fond VS Code.')
        print('Sauvegarde automatique avant chaque remplacement ; aucune écriture en mode dry-run.')
        return
    dependencies(args)
    writer = Writer(home)
    # Keep wallpaper tooling and all managed files independent of the cloned repository.
    base = home/'.local/share/orbite'
    terminal = base/'images/terminal.jpg'
    image = base/'images/vscode.png'
    substitutions = {'@HOME@':str(home), '@TMUX_COMMAND@':'exec '+shlex.quote(str(home/'.local/bin/orbite-tmux'))+' start', '@TERMINAL_IMAGE@':str(terminal), '@TERMINAL_IMAGE_URI@':terminal.as_uri()}
    def render(source):
        text = (ROOT/source).read_text()
        for token, value in substitutions.items(): text = text.replace(token, value)
        return text
    def copy(source, target, mode=0o644): writer.write(target, (ROOT/source).read_bytes(), mode)
    for source, target in [
        ('assets/images/terminal.jpg','.local/share/orbite/images/terminal.jpg'),
        ('assets/images/vscode.png','.local/share/orbite/images/vscode.png'),
        ('config/init.zsh','.config/orbite/init.zsh'),
        ('config/orbite.zsh-theme','.local/share/orbite/custom/themes/orbite.zsh-theme'),
        ('config/tmux.conf','.config/tmux/tmux.conf'),
        ('config/AIDE-TMUX.txt','.config/orbite/AIDE-TMUX.txt'),
        ('scripts/vscode_wallpaper.py','.local/share/orbite/vscode_wallpaper.py')]: copy(source,target)
    copy('bin/orbite-tmux','.local/bin/orbite-tmux',0o755)
    copy('bin/orbite-copy','.local/bin/orbite-copy',0o755)
    for name in ('t','droite','bas','grille'): writer.write('.local/bin/'+name,b'',symlink='orbite-tmux')
    for source in sorted((ROOT/'config/terminator/plugins').glob('*.py')):
        copy(str(source.relative_to(ROOT)),'.config/terminator/plugins/'+source.name)
    writer.write('.config/terminator/config',render('config/terminator.conf'))
    writer.write('.config/orbite/terminator-tabs.css',render('config/terminator-tabs.css'))
    for name, source in json.loads((ROOT/'vendor/sources.json').read_text()).items():
        data = (ROOT/source['archive']).read_bytes()
        if digest(data) != source['sha256']: raise RuntimeError('Archive modifiée : '+name)
        archive(writer,data,'.local/share/orbite/vendor/'+name)
    for filename, body in [('.zshrc','[[ -r "$HOME/.config/orbite/init.zsh" ]] && source "$HOME/.config/orbite/init.zsh"'),
                           ('.tmux.conf','source-file "~/.config/tmux/tmux.conf"')]:
        path = home/filename
        writer.write(filename,managed(path.read_text() if path.exists() else '',body))
    (home/'.cache/orbite/ohmyzsh').mkdir(parents=True,exist_ok=True)
    fzf = shutil.which('fzf')
    shell = render('config/shell.zsh')
    if fzf:
        result = subprocess.run([fzf,'--zsh'],capture_output=True,text=True)
        if result.returncode == 0: writer.write('.config/orbite/fzf.zsh',result.stdout)
        else:
            fallback = next((p for p in [Path('/usr/share/doc/fzf/examples/key-bindings.zsh'),Path('/usr/share/fzf/key-bindings.zsh')] if p.exists()),None)
            if fallback: writer.write('.config/orbite/fzf.zsh',fallback.read_bytes())
            shell = re.sub(r'--walker-skip \S+ ', '', shell)
    writer.write('.config/orbite/shell.zsh',shell)
    downloads = json.loads((ROOT/'vendor/downloads.json').read_text())
    if not args.no_network:
        if not args.no_fonts:
            for key, record in downloads.items():
                if key.startswith('fonts/'):
                    writer.write('.local/share/fonts/Orbite/'+key.split('/',1)[1],download(record))
            if shutil.which('fc-cache'): run(['fc-cache','-f',home/'.local/share/fonts/Orbite'],stdout=subprocess.DEVNULL)
        if not shutil.which('eza'):
            key = 'eza/'+platform.machine()
            if key not in downloads: raise RuntimeError('Architecture eza non prise en charge.')
            with tarfile.open(fileobj=io.BytesIO(download(downloads[key])),mode='r:gz') as bundle:
                member = next(m for m in bundle if Path(m.name).name == 'eza' and m.isfile())
                writer.write('.local/bin/eza',bundle.extractfile(member).read(),0o755)
    app = find_app(args.code_app)
    if not args.skip_vscode:
        writer.write('.config/Code/User/settings.json',json.dumps(settings,indent=2,ensure_ascii=False)+'\n')
        writer.write('.local/share/orbite/orbite.vsix',vsix())
        code = args.code_bin or shutil.which('code')
        if not code: raise RuntimeError('Code introuvable ; utiliser --skip-vscode ou installer Code.')
        cli = [code,'--user-data-dir',home/'.config/Code','--extensions-dir',home/'.vscode/extensions']
        # Theme is declarative: direct files allow complete backup/restore, unlike CLI-managed extensions.
        for source in (ROOT/'vscode/extension').rglob('*'):
            if source.is_file(): copy(str(source.relative_to(ROOT)),'.vscode/extensions/uramix.orbite-1.1.0/'+str(source.relative_to(ROOT/'vscode/extension')))
        if not args.no_network:
            run(cli+['--install-extension','PKief.material-icon-theme','--force'])
        if app:
            command = ['python3',str(base/'vscode_wallpaper.py'),'--app-dir',str(app),'--image',str(image),
                       '--backup-dir',str(base/'code-backups')]
            # Store a command with proper shell escaping; only the application write is elevated.
            prefix = ['sudo'] if not all(os.access(p,os.W_OK) for p in [app, app/'out/vs/workbench']) else []
            wrapper = '#!/bin/sh\nexec '+shlex.join(prefix+command)+' "$@"\n'
            writer.write('.local/bin/orbite-vscode-wallpaper',wrapper,0o755)
            if not args.skip_wallpaper: run(prefix+command)
        elif not args.skip_wallpaper: raise RuntimeError('Application Code introuvable : préciser --code-app.')
    # A launcher is safer than changing the login shell or the system default terminal.
    desktop = '[Desktop Entry]\nType=Application\nName=Orbite Terminal\nExec=terminator\nIcon=utilities-terminal\nCategories=System;TerminalEmulator;\nTerminal=false\n'
    writer.write('.local/share/applications/orbite-terminal.desktop',desktop)
    print('Orbite installé. Lance terminator ; ouvre une nouvelle fenêtre VS Code.')
    print('Sauvegarde :',writer.backup if writer.entries else 'aucune modification nécessaire')
    print('Restauration : ./install.sh --restore <chemin-de-sauvegarde>')
    if args.no_network: print('Mode hors ligne : polices et Material Icon Theme existants conservés.')
    print('Shell de connexion (optionnel) : chsh -s /usr/bin/zsh')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=Path.home(),help='Dossier utilisateur cible (tests/migration).')
    for name in ('no-packages','no-network','no-fonts','skip-vscode','skip-wallpaper','dry-run','force'):
        parser.add_argument('--'+name,action='store_true')
    parser.add_argument('--code-app',help='Dossier resources/app de VS Code.')
    parser.add_argument('--code-bin',help='Exécutable code.')
    parser.add_argument('--restore',type=Path,help='Restaurer une sauvegarde de configuration.')
    args = parser.parse_args()
    try:
        if args.restore: restore(args.restore.expanduser().resolve(),args.force)
        else: install(args)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print('Erreur :',error,file=sys.stderr)
        print('Les fichiers déjà modifiés disposent d’une sauvegarde dans ~/.local/state/orbite/backups.',file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
