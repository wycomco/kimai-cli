_kimai_completion() {
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _KIMAI_COMPLETE=complete $1 ) )
    return 0
}

complete -F _kimai_completion -o default kimai;
