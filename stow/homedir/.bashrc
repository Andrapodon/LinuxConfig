#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
PS1='[\u@\h \W]\$ '
[ -r /home/marc/.byobu/prompt ] && . /home/marc/.byobu/prompt   #byobu-prompt#

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/home/marc/anaconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/home/marc/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/home/marc/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/home/marc/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

alias r=~/.local/bin/radian
alias Server1="ssh andrapodon@194.56.189.204"
alias ll='ls -a'
alias Server2="ssh andrapodon@andrapodon.ch"
export PATH="/home/marc/scripts:/home/marc/.local/bin:$PATH"
alias ETH-VPN="sudo openconnect -u marcpe@student-net.ethz.ch --useragent=AnyConnect -g student-net sslvpn.ethz.ch"
alias r="radian"

# Quarto completion
_quarto_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local commands="render preview serve create use add update remove convert pandoc typst run list install uninstall tools publish check help"
    COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
}
complete -o default -F _quarto_completions quarto

# OSC 52 Network Clipboard
clip() {
    local input
    if [ $# -eq 0 ]; then
        input=$(cat)
    else
        input=$(cat "$@")
    fi
    printf "\033]52;c;%s\a" "$(printf "%s" "$input" | base64 | tr -d '\n')"
}

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
