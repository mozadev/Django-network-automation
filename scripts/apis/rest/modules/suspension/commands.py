def commands_to_huawei(sub_interface, suspension, commit):
    result = [
        # validación inicial
        {"prompt": "\>", "command": f"dis curr int {sub_interface}"},
        # Configuración
        {"prompt": "\>", "command": f"system-view"},
        {"prompt": "\]", "command": f"interface {sub_interface}"},
        {"prompt": "\]", "command": f"shutdown"} if suspension else {"prompt": "\]", "command": f"undo shutdown"},
        {"prompt": "\]", "command": f""},
        {"prompt": "\]", "command": f"quit"},
        {"prompt": "\]", "command": f"quit"},
        {"prompt": "\[Y\(yes\)\/N\(no\)\/C\(cancel\)\]:", "command": commit},
        # Validación final
        {"prompt": "\>", "command": f"dis curr int {sub_interface}"},
    ]

    return result
