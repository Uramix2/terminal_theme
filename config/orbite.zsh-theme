# Orbite: prompt rendered entirely with Zsh builtins; no Git status, Python or network.
autoload -Uz add-zsh-hook
unsetopt PROMPT_SUBST
setopt PROMPT_PERCENT
typeset -g _orbite_started=-1

_orbite_preexec() { _orbite_started=$SECONDS; }

# Read only Git's HEAD. No scan of tracked/untracked files, including in worktrees.
_orbite_git() {
    local dir=$PWD gitdir='' head='' line=''
    REPLY=''
    while true; do
        if [[ -d "$dir/.git" ]]; then
            gitdir="$dir/.git"
            break
        elif [[ -f "$dir/.git" ]]; then
            IFS= read -r line < "$dir/.git"
            [[ $line == 'gitdir: '* ]] || return 0
            gitdir=${line#gitdir: }
            [[ $gitdir == /* ]] || gitdir="$dir/$gitdir"
            break
        fi
        [[ $dir == / ]] && return 0
        dir=${dir:h}
    done
    [[ -r "$gitdir/HEAD" ]] || return 0
    IFS= read -r head < "$gitdir/HEAD"
    if [[ $head == 'ref: refs/heads/'* ]]; then
        REPLY=${head#ref: refs/heads/}
    else
        REPLY="@${head[1,8]}"
    fi
    REPLY=${REPLY//\%/%%}
}

_orbite_precmd() {
    local exit_code=$? elapsed=0 env_name='' git_label='' extras='' display_dir=''
    (( _orbite_started >= 0 )) && elapsed=$(( SECONDS - _orbite_started ))
    _orbite_started=-1
    _orbite_git
    [[ -n $REPLY ]] && git_label="  %F{#919bb3}%f %F{#c8badb}${REPLY}%f"
    if [[ -n $VIRTUAL_ENV ]]; then
        env_name=${VIRTUAL_ENV:t}
    elif [[ -n $CONDA_DEFAULT_ENV && $CONDA_DEFAULT_ENV != base ]]; then
        env_name=$CONDA_DEFAULT_ENV
    fi
    [[ -n $env_name ]] && extras+="  %F{#b7d9cb}⌁ ${env_name//\%/%%}%f"
    (( elapsed >= 2 )) && extras+="  %F{#e6c79c}${elapsed}s%f"
    (( exit_code )) && extras+="  %F{#f38d95}× ${exit_code}%f"
    [[ -n $SSH_CONNECTION ]] && extras+=' %F{#e6c79c}ssh:%m%f'
    # Full path, without truncation, in one bright uniform sky blue.
    display_dir='%B%F{#a8cdea}%~%b%f'
    PROMPT=$'\n''%F{#3b2638}%K{#3b2638}%F{#eab1cd}  %B%F{#f6e1ed}%n%b %k%F{#3b2638}%f  '"${display_dir}${git_label}${extras}"$'\n''%F{#65718a}╰─%f %(?.%F{#add5bc}.%F{#f38d95})❯%f '
    RPROMPT=''
}

add-zsh-hook -d preexec _orbite_preexec
add-zsh-hook -d precmd _orbite_precmd
add-zsh-hook preexec _orbite_preexec
add-zsh-hook precmd _orbite_precmd
PROMPT=$'\n''%F{#3b2638}%K{#3b2638}%F{#eab1cd}  %B%F{#f6e1ed}%n%b %k%F{#3b2638}%f  %B%F{#a8cdea}%~%b%f'$'\n%F{#65718a}╰─%f %F{#add5bc}❯%f '
