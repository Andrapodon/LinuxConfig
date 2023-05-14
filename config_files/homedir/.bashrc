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
export PATH="/home/marc/.local/bin:$PATH"

