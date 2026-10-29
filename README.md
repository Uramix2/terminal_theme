# Orbite — terminal et VS Code

Ma configuration portable pour **Debian 12 et 13**, avec les images incluses.

- Terminator : fond de paysage, onglets numérotés, séparateurs discrets, fenêtre sans décoration.
- tmux : sessions indépendantes par onglet, panneaux, souris, barre d’état et aide intégrée.
- Zsh : prompt Cerisier, chemin lisible, couleurs des commandes/fichiers, complétion, suggestions, double Échap pour `sudo`.
- VS Code : thème Orbite, Material Icon Theme, police MesloLGS NF et trou noir orange très assombri sous le code.

| Terminal | VS Code |
| --- | --- |
| ![Fond terminal](assets/images/terminal.jpg) | ![Fond VS Code](assets/images/vscode.png) |

## Installer

Sur une session Debian avec interface graphique et accès à `sudo` :

```sh
sudo apt install git python3
git clone https://github.com/Uramix2/terminal_theme.git
cd terminal_theme
./install.sh
```

Lancer le script **avec son utilisateur habituel**, sans `sudo` devant `./install.sh`. Il demande les droits uniquement pour APT et le fond de VS Code installé dans les fichiers système.

Il installe les dépendances, Code si absent, les polices et les icônes. Il vérifie que Fontconfig sélectionne bien MesloLGS NF pour afficher correctement le badge Debian et ses contours. Puis ouvrir **Orbite Terminal** dans les applications, ou lancer `terminator`, et ouvrir une nouvelle fenêtre VS Code. Le terminal intégré de Code utilise aussi Zsh. Le shell de connexion du système reste au choix : `chsh -s /usr/bin/zsh` si souhaité.

Les fichiers installés et les images se trouvent dans `~/.config/orbite`, `~/.config/terminator` et `~/.local/share/orbite`. Le clone peut ensuite être déplacé. Aucun chemin ni nom d’utilisateur n’est fixé dans le thème.

## Commandes et raccourcis

| Action | Commande / touche |
| --- | --- |
| Nouvelle session / retrouver les sessions | `t` ou `t nom` |
| Panneau à droite / dessous | `droite` / `bas` |
| Grille de panneaux | `grille` ou `grille 6` |
| Nouveau panneau avec une commande | `droite 'htop'` |
| Aide tmux | `t aide` ou `Ctrl-b`, puis `?` |
| Nouveau panneau à droite / dessous | `Ctrl-b`, puis `v` / `-` |
| Zoom / détacher la session | `Ctrl-b`, puis `z` / `d` |
| Nouvel onglet Terminator | `Ctrl-Maj-T` |
| Onglet numéroté | `Alt-1` à `Alt-9`, pavé numérique compris |
| Onglet suivant / précédent | `Ctrl-Tab` / `Ctrl-Maj-Tab` |
| Fermer l’onglet **le plus à droite et arrêter sa session avec toutes ses commandes** | `Ctrl-Maj-Suppr` |
| Recherche historique / fichier / dossier | `Ctrl-R` / `Ctrl-T` / `Alt-C` |
| Ajouter ou retirer `sudo` sans exécuter | `Échap`, `Échap` |
| Changer de dossier / créer puis entrer | `c chemin` / `mkcd chemin` |
| Liste détaillée / arbre sur deux niveaux | `ll` / `lt` |

La touche Windows/Super continue de fonctionner : la fenêtre est maximisée et sans bordure, sans capture du clavier.

## Sauvegarde et restauration

Chaque fichier remplacé est sauvegardé dans :

```text
~/.local/state/orbite/backups/<date>/
```

Le chemin exact s’affiche à la fin de l’installation. Les fichiers `.zshrc` et `.tmux.conf` reçoivent un bloc Orbite ; leur contenu personnel est conservé. Les préférences VS Code sans rapport avec le thème restent présentes ; leur fichier d’origine, commentaires compris, est sauvegardé.

Pour revenir en arrière, **retirer d’abord le fond de Code**, puis restaurer la sauvegarde choisie :

```sh
~/.local/bin/orbite-vscode-wallpaper --remove
./install.sh --restore "$HOME/.local/state/orbite/backups/<date>"
```

La restauration s’arrête si un fichier a été modifié depuis l’installation ; `--force` permet de confirmer son écrasement. Elle restaure les fichiers de configuration et les fichiers du thème. Les paquets APT, les extensions téléchargées via le Marketplace et les dossiers devenus vides ne sont pas désinstallés.

Le fond VS Code modifie sa feuille de style et actualise son empreinte interne. Les fichiers de l’application sont également sauvegardés par version/contenu dans `~/.local/share/orbite/code-backups`. **Après une mise à jour de Code**, réappliquer le fond avec :

```sh
~/.local/bin/orbite-vscode-wallpaper
```

Les installations Code APT/deb sont prises en charge. Snap et Flatpak ne sont pas ciblés. Pour conserver les fichiers de l’application intacts : `./install.sh --skip-wallpaper`.

## Options

```sh
./install.sh --dry-run                         # aperçu sans écriture
./install.sh --no-packages                     # dépendances déjà installées
./install.sh --skip-vscode                     # terminal uniquement
./install.sh --no-fonts                        # police déjà disponible
./install.sh --no-packages --no-network        # réutiliser les dépendances locales
./install.sh --home '/tmp/essai orbite' --no-packages --no-network --skip-vscode
```

Le mode hors ligne installe les sources Zsh et les images fournies. Il conserve les polices/icônes déjà disponibles et utilise `ls` si `eza` manque. Les dépendances graphiques, Zsh et tmux doivent être présentes. Le mode `--home` sert aux tests ; il ne change pas le compte de connexion.

## Vérifications

```sh
python3 -m unittest discover -s tests -v
python3 tests/gtk_smoke.py                      # fenêtre temporaire, HOME et serveur tmux isolés
# Ou, sans interface graphique sur la machine hôte :
docker run --rm -v "$PWD:/workspace:ro" debian:bookworm sh /workspace/tests/container-test.sh
```

Le test graphique hors ligne reprend les polices Meslo déjà installées sur la machine. Pour vérifier aussi leur téléchargement dans un conteneur neuf, ajouter `-e ORBITE_TEST_FONTS=1` à la commande Docker.

Les tests couvrent l’installation répétée, les chemins avec espaces, la préservation des réglages, la restauration, Zsh, les panneaux tmux, le fond et son empreinte Code, les onglets GTK et la fermeture de la bonne session. La CI exécute ces vérifications sous Debian 12 et 13. Elle ne modifie pas le dossier personnel de la machine hôte.

## Sources et fichiers inclus

Les archives Oh My Zsh, zsh-autosuggestions et zsh-syntax-highlighting contiennent leurs licences. Leurs versions et empreintes sont dans [`vendor/sources.json`](vendor/sources.json). Les téléchargements de MesloLGS NF et du binaire `eza` sont fixés par URL/version et SHA256 dans [`vendor/downloads.json`](vendor/downloads.json).

Le thème VS Code conserve la [licence MIT de son thème d’origine](vscode/extension/LICENSE). Les deux images sont les fonds choisis pour cette configuration ; aucune licence libre supplémentaire n’est attribuée aux images par ce dépôt.

Seuls les réglages nécessaires au thème sont exportés : aucun historique, identifiant, coffre, write-up ou configuration de projet personnel.
