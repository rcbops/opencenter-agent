function return_fact {
    echo -ne "facts\0$1\0$2\0">&3
}

function return_attr {
    echo -ne "attrs\0$1\0$2\0">&3
}

function return_consequence {
    echo -ne "consequences\0\0$1\0">&3
}
