
def commands_to_cisco():
    result = [
        # validación inicial
        {"prompt": "\#", "command": "terminal length 0"},
        {"prompt": "\#", "command": "show running-config interface GigabitEthernet0/0"},
        {"prompt": "\#", "command": "show running-config policy-map Shape4096"},
        {"prompt": "\#", "command": "show running-config policy-map wan_upgrade"},
        # Configuración
        {"prompt": "\#", "command": "configure terminal"},
        {"prompt": "\#", "command": "policy-map wan_upgrade"},
        {"prompt": "\#", "command": " class qos5"},
        {"prompt": "\#", "command": "  priority 768"},
        {"prompt": "\#", "command": "  police 768000 144000 288000 conform-action transmit  exceed-action drop  violate-action drop"},
        {"prompt": "\#", "command": "   exit"},
        {"prompt": "\#", "command": "  exit"},
        {"prompt": "\#", "command": " class qos4"},
        {"prompt": "\#", "command": "  bandwidth 1280"},
        {"prompt": "\#", "command": "  police 1280000 240000 480000 conform-action transmit  exceed-action drop  violate-action drop"},
        {"prompt": "\#", "command": "   exit"},
        {"prompt": "\#", "command": "  exit"},
        {"prompt": "\#", "command": " class qos2"},
        {"prompt": "\#", "command": "  bandwidth 1792"},
        {"prompt": "\#", "command": "  police 1792000 336000 672000 conform-action transmit  exceed-action set-dscp-transmit default"},
        {"prompt": "\#", "command": "   exit"},
        {"prompt": "\#", "command": "  exit"},
        {"prompt": "\#", "command": " class class-default"},
        {"prompt": "\#", "command": "  bandwidth 256"},
        {"prompt": "\#", "command": "  random-detect"},
        {"prompt": "\#", "command": "  exit"},
        {"prompt": "\#", "command": " exit"},
        {"prompt": "\#", "command": "policy-map Shape4096"},
        {"prompt": "\#", "command": " class class-default"},
        {"prompt": "\#", "command": "  shape average 4097000"},
        {"prompt": "\#", "command": "  service-policy wan_upgrade"},
        {"prompt": "\#", "command": "  exit"},
        {"prompt": "\#", "command": " exit"},
        {"prompt": "\#", "command": "interface GigabitEthernet0/0"},
        #{"prompt": "\#", "command": " bandwidth 4097"},
        #{"prompt": "\#", "command": " no service-policy output Shape2048"},
        {"prompt": "\#", "command": " no service-policy output Shape1024"},
        {"prompt": "\#", "command": " service-policy output Shape4096"},
        {"prompt": "\#", "command": " exit"},
        {"prompt": "\#", "command": "exit"},
        {"prompt": "\#", "command": "write memory"},
        # Validation final
        {"prompt": "\#", "command": "terminal length 0"},
        {"prompt": "\#", "command": "show running-config interface GigabitEthernet0/0"},
        {"prompt": "\#", "command": "show running-config policy-map Shape4096"},
        {"prompt": "\#", "command": "show running-config policy-map wan_upgrade"},
    ]

    return result


def commands_to_teldat():
    result = [
        {"prompt": "\s\*", "command": "p 5"},
        {"prompt": "\$", "command": "feature bandwidth-reservation"},
        {"prompt": "\$", "command": "show config"},
        {"prompt": "\$", "command": "network ethernet0/1"},
        {"prompt": "\$", "command": "show config"},
        {"prompt": "\$", "command": "class qos5 rate-limit 768 1152 2304"},
        {"prompt": "\$", "command": "class qos4 rate-limit 1280 1920 3840"},
        {"prompt": "\$", "command": "class qos2 rate-limit 1792 2688 5376"},
        {"prompt": "\$", "command": "rate-limit 4096"},
        {"prompt": "\$", "command": "show config"},
        {"prompt": "\$", "command": "exit"},
        {"prompt": "\$", "command": "exit"},
        {"prompt": "\$", "command": "save"},
        {"prompt": "\?", "command": "yes"},
        {"prompt": "\$", "command": "end"},
    ]
    return result