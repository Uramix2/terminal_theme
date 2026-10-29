# Orbite Cerisier: slate blue, blossom rose and restrained lava/coral accents.
# Static colours only: no image processing or external command at shell startup.
export LS_COLORS='rs=0:fi=38;5;255:di=1;38;5;153:ln=38;5;111:or=1;38;5;210:ex=1;38;5;151:pi=38;5;223:so=38;5;218:bd=38;5;223:cd=38;5;223:su=1;38;5;210:sg=1;38;5;210:tw=1;38;5;153:ow=1;38;5;153:st=1;38;5;153:*.py=38;5;147:*.js=38;5;147:*.ts=38;5;147:*.go=38;5;147:*.rs=38;5;147:*.c=38;5;147:*.cpp=38;5;147:*.h=38;5;147:*.sh=38;5;151:*.zsh=38;5;151:*.md=38;5;189:*.pdf=38;5;189:*.txt=38;5;255:*.json=38;5;223:*.yaml=38;5;223:*.yml=38;5;223:*.toml=38;5;223:*.ini=38;5;223:*.conf=38;5;223:*.png=38;5;218:*.jpg=38;5;218:*.jpeg=38;5;218:*.svg=38;5;218:*.webp=38;5;218:*.zip=38;5;216:*.gz=38;5;216:*.tar=38;5;216:*.7z=38;5;216:*.xz=38;5;216:*.swp=38;5;103:*.bak=38;5;103'
export EZA_COLORS="reset:${LS_COLORS}:sc=38;5;147:im=38;5;218:vi=38;5;218:mu=38;5;218:lo=38;5;218:do=38;5;189:co=38;5;216:bu=38;5;223:cr=38;5;111:cm=38;5;103:tm=38;5;103:ur=38;5;153:uw=38;5;223:ux=38;5;151:ue=38;5;151:gr=38;5;110:gw=38;5;180:gx=38;5;115:tr=38;5;109:tw=38;5;180:tx=38;5;108:uu=38;5;181:gu=38;5;110:un=38;5;255:gn=38;5;110:da=38;5;146:sn=38;5;153:sb=38;5;110:hd=1;38;5;181:xx=38;5;103:lp=38;5;111:ga=38;5;151:gm=38;5;223:gd=38;5;210:gv=38;5;147"

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#8e98ad'
if (( ${+ZSH_HIGHLIGHT_STYLES} )); then
    ZSH_HIGHLIGHT_STYLES[default]='fg=#e8edf5'
    for style in command builtin alias function arg0; do
        ZSH_HIGHLIGHT_STYLES[$style]='fg=#8df0c7,bold'
    done
    unset style
    ZSH_HIGHLIGHT_STYLES[path]='fg=#a8cdea,underline'
    ZSH_HIGHLIGHT_STYLES[path_prefix]='fg=#a8cdea'
    ZSH_HIGHLIGHT_STYLES[path_pathseparator]='fg=#a8cdea'
    ZSH_HIGHLIGHT_STYLES[path_prefix_pathseparator]='fg=#a8cdea'
    ZSH_HIGHLIGHT_STYLES[single-hyphen-option]='fg=#b9c9f1'
    ZSH_HIGHLIGHT_STYLES[double-hyphen-option]='fg=#b9c9f1'
    ZSH_HIGHLIGHT_STYLES[single-quoted-argument]='fg=#ead5cb'
    ZSH_HIGHLIGHT_STYLES[double-quoted-argument]='fg=#ead5cb'
    ZSH_HIGHLIGHT_STYLES[dollar-quoted-argument]='fg=#ead5cb'
    ZSH_HIGHLIGHT_STYLES[dollar-double-quoted-argument]='fg=#b7d9cb'
    ZSH_HIGHLIGHT_STYLES[assign]='fg=#b7d9cb'
    ZSH_HIGHLIGHT_STYLES[globbing]='fg=#d3b3df'
    ZSH_HIGHLIGHT_STYLES[history-expansion]='fg=#d3b3df'
    ZSH_HIGHLIGHT_STYLES[comment]='fg=#8e98ad'
    ZSH_HIGHLIGHT_STYLES[unknown-token]='fg=#f38d95,bold'
    ZSH_HIGHLIGHT_STYLES[redirection]='fg=#d3b3df'
    ZSH_HIGHLIGHT_STYLES[commandseparator]='fg=#c5b8dc,bold'
fi

# Exact matching first; ignore case only when exact matching finds nothing.
zstyle ':completion:*' matcher-list '' 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path "$HOME/.cache/zsh/completion"
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*:descriptions' format '%F{153}%B%d%b%f'
# Highlight the completion heading, independently of directory entries.
zstyle ':completion:*:local-directories' format '%F{#edb4cd}%B%d%b%f'
zstyle ':completion:*:warnings' format '%F{210}Aucun résultat : %d%f'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' verbose yes
[[ -d "$HOME/.cache/zsh/completion" ]] || mkdir -p "$HOME/.cache/zsh/completion"

# Static integration generated once at install time: no fzf process at startup.
if [[ -t 0 && -t 1 && -t 2 && -r "$HOME/.config/orbite/fzf.zsh" ]] && (( $+commands[fzf] )); then
    export FZF_DEFAULT_OPTS='--height=45% --layout=reverse --border=rounded --info=inline --color=bg:#111521,bg+:#293047,fg:#e8edf5,fg+:#f8f5fa,hl:#edb4cd,hl+:#c4d8f5,pointer:#edb4cd,marker:#e6c79c,border:#65748e,prompt:#a8cdea,info:#9aa6ba,header:#d1b1e5'
    export FZF_CTRL_T_OPTS='--walker-skip .git,node_modules,.venv,venv,__pycache__,miniconda3,.cache --prompt="Fichier ❯ "'
    export FZF_ALT_C_OPTS='--walker-skip .git,node_modules,.venv,venv,__pycache__,miniconda3,.cache --prompt="Dossier ❯ "'
    export FZF_CTRL_R_OPTS='--prompt="Historique ❯ " --no-multi'
    source "$HOME/.config/orbite/fzf.zsh"
fi

# Tab remains predictable: complete one path segment, without accepting suggestions.
bindkey '^I' expand-or-complete
# Right arrow accepts the full ghost suggestion at end of line; Alt+Right one word.
bindkey '^[[1;3C' forward-word
bindkey '^[[1;5C' forward-word
bindkey '^[f' forward-word
bindkey '^[.' insert-last-word

# Use lsg only when Git metadata is useful; ll stays fast in large repositories.
if (( $+commands[eza] )); then
    alias ls='eza --icons=auto --group-directories-first --color=auto'
    alias ll='eza -lah --icons=auto --group-directories-first --color=auto'
    alias la='eza -a --icons=auto --group-directories-first --color=auto'
    alias lsg='eza -lah --icons=auto --git --group-directories-first --color=auto'
    alias lt='eza --tree --level=2 --icons=auto --group-directories-first --color=auto'
fi
