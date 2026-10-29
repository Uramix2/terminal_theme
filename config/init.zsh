# Orbite loads after existing user settings and leaves unrelated aliases intact.
typeset -U path PATH
path=("$HOME/.local/bin" $path)
typeset -g _orbite_root="$HOME/.local/share/orbite"
if (( ! ${+functions[omz]} )); then
    export ZSH="$_orbite_root/vendor/ohmyzsh"
    export ZSH_CUSTOM="$_orbite_root/custom"
    ZSH_THEME=orbite
    plugins=(git sudo)
    ZSH_CACHE_DIR="$HOME/.cache/orbite/ohmyzsh"
    ZSH_COMPDUMP="$HOME/.cache/orbite/zcompdump-$ZSH_VERSION"
    zstyle ':omz:update' mode disabled
    source "$ZSH/oh-my-zsh.sh"
else
    source "$_orbite_root/custom/themes/orbite.zsh-theme"
    if (( ! ${+functions[sudo-command-line]} )); then
        source "$_orbite_root/vendor/ohmyzsh/plugins/sudo/sudo.plugin.zsh"
    fi
fi
if (( ! ${+functions[_zsh_autosuggest_start]} )); then
    source "$_orbite_root/vendor/zsh-autosuggestions/zsh-autosuggestions.zsh"
fi
ZSH_AUTOSUGGEST_STRATEGY=(history)
if (( ! ${+functions[_zsh_highlight]} )); then
    source "$_orbite_root/vendor/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
fi
alias ls='ls --color=auto --group-directories-first'
alias ll='ls -lah --color=auto --group-directories-first'
alias la='ls -a --color=auto --group-directories-first'
if (( ! ${+functions[cd]} )); then
    cd() { builtin cd "$@" && ls; }
fi
mkcd() { mkdir -p -- "$1" && cd -- "$1"; }
alias c=cd
alias reload='source ~/.zshrc'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias back='cd -'
setopt AUTO_MENU AUTO_PARAM_SLASH NO_LIST_AMBIGUOUS COMPLETE_IN_WORD
unsetopt MENU_COMPLETE REC_EXACT
zstyle ':completion:*' menu select
zstyle ':completion:*' list-dirs-first true
zstyle ':completion:*' expand no
zstyle ':completion:*' squeeze-slashes yes
PROMPT_EOL_MARK=''
export VIRTUAL_ENV_DISABLE_PROMPT=1
source "$HOME/.config/orbite/shell.zsh"
