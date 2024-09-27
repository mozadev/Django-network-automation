

def commands_to_huawei(sub_interface, vrf_new, vrf_old, ip_interface, ip_vrf, cid_cliente, cliente, asnumber, password, new_grupo, commit):
    vrf_new_str = convert_num_to_str(vrf_new, 5)
    vrf_old_str = convert_num_to_str(vrf_old, 5)

    result = [
        # Configuración
        {"prompt": "\>", "command": f"system-view"},
        # NUEVA VRF 
        {"prompt": "\]", "command": f"ip vpn-instance {vrf_new_str}"},
        {"prompt": "\]", "command": f" description RPVFM_{cliente}"},
        {"prompt": "\]", "command": f"  ipv4-family"},
        {"prompt": "\]", "command": f"  route-distinguisher 12252:{vrf_new}"},
        {"prompt": "\]", "command": f"  export route-policy loopback_Serv_Extranet_MRA_CLARO"},
        {"prompt": "\]", "command": f"  apply-label per-instance"},
        {"prompt": "\]", "command": f"  vpn-target 12252:10000{vrf_new_str} import-extcommunity"},
        {"prompt": "\]", "command": f"  vpn-target 12252:1100000001 import-extcommunity"},
        {"prompt": "\]", "command": f"  vpn-target 12252:10000{vrf_new_str} export-extcommunity"},
        {"prompt": "\]", "command": f"  vpn-target 12252:10074 import-extcommunity"},
        {"prompt": "\]", "command": f"  quit"},
        {"prompt": "\]", "command": f" quit"},
        {"prompt": "\]", "command": f""},
        # INTERFACE
        {"prompt": "\]", "command": f"interface {sub_interface}"},
        #{"prompt": "\]", "command": f" display this"},
        {"prompt": "\]", "command": f" undo ip binding vpn-instance {vrf_old_str}"},
        {"prompt": "\]", "command": f" ip binding vpn-instance {vrf_new_str}"},
        {"prompt": "\]", "command": f" ip address {ip_interface} 30 "},
        {"prompt": "\]", "command": f" quit"},
        {"prompt": "\]", "command": f""},
    ]

    bgp_group_not_found = [
        # CONFIGURAR NUEVO GROUP AL VPN-INSTANCE
        {"prompt": "\]", "command": f"bgp 12252"},
        {"prompt": "\]", "command": f" ipv4-family vpn-instance {vrf_new_str}"},
        {"prompt": "\]", "command": f"  preference 20 200 200"},
        {"prompt": "\]", "command": f"  import-route direct"},  
        {"prompt": "\]", "command": f"  import-route static"},  
        {"prompt": "\]", "command": f"  group RPVFM_{cliente} external"},  
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} as-number {asnumber}"},  
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} timer keepalive 10 hold 30"},  
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} password cipher {password}"},  
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} substitute-as"},  
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} route-policy default_policy_pass_all import"},  
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} route-policy default_policy_pass_all export"},
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} advertise-community"},
        {"prompt": "\]", "command": f"  peer RPVFM_{cliente} keep-all-routes"},
        {"prompt": "\]", "command": f"  peer {ip_vrf} group RPVFM_{cliente}"},
        {"prompt": "\]", "command": f"  peer {ip_vrf} description CID {cid_cliente} RPVFM {cliente}"},
        {"prompt": "\]", "command": f"  peer {ip_vrf} as-number {asnumber}"},
        {"prompt": "\]", "command": f"  quit"},
        {"prompt": "\]", "command": f" quit"},
        {"prompt": "\]", "command": f""},
        {"prompt": "\]", "command": f"bgp 12252"},
        {"prompt": "\]", "command": f" ipv4-family vpn-instance {vrf_old_str}"},
        {"prompt": "\]", "command": f"  undo peer {ip_vrf}"},
        {"prompt": "N\]:", "command": commit},
        {"prompt": "\]", "command": f"  quit"},
        {"prompt": "\]", "command": f" quit"},
    ]

    bgp_group_found = [
        # CONFIGURAR NUEVO PEER AL GROUP DE LA VPN-INSTANCE
        {"prompt": "\]", "command": f"bgp 12252"},
        {"prompt": "\]", "command": f" ipv4-family vpn-instance {vrf_new_str}"},
        {"prompt": "\]", "command": f"  peer {ip_vrf} group RPVFM_{cliente}"},
        {"prompt": "\]", "command": f"  peer {ip_vrf} description CID {cid_cliente} RPVFM {cliente}"},
        {"prompt": "\]", "command": f"  peer {ip_vrf} as-number {asnumber}"},
        {"prompt": "\]", "command": f"  quit"},
        {"prompt": "\]", "command": f" quit"},
        {"prompt": "\]", "command": f""},
        {"prompt": "\]", "command": f"bgp 12252"},
        {"prompt": "\]", "command": f" ipv4-family vpn-instance {vrf_old_str}"},
        {"prompt": "\]", "command": f"  undo peer {ip_vrf}"},
        {"prompt": "N\]:", "command": commit},
        {"prompt": "\]", "command": f"  quit"},
        {"prompt": "\]", "command": f" quit"},
    ]

    commitear = [
        # Commitear
        {"prompt": "\]", "command": f"quit"},
        {"prompt": "\[Y\(yes\)\/N\(no\)\/C\(cancel\)\]:", "command": commit},

        # Validación final
        {"prompt": "\>", "command": f"dis curr int {sub_interface}"},
    ]

    if new_grupo:
        result.extend(bgp_group_not_found)
    else:
        result.extend(bgp_group_found)

    result.extend(commitear)

    return result


def convert_num_to_str(number, digit):
    num = str(number)
    len_num = len(num)
    if len_num < digit:
        new_txt = str(number + 10**(digit))[1:]
    else:
        new_txt = num
    return new_txt
