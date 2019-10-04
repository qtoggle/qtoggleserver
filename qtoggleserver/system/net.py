
import logging
import re
import subprocess


logger = logging.getLogger(__name__)


def get_ip_config(iface):
    config = {}
    output = subprocess.check_output('ip addr show dev {}'.format(iface), shell=True).split('\n')
    for line in output:
        match = re.match(r'^\s*inet (\d+\.\d+\.\d+\.\d+)/(\d+)', line)
        if not match:
            continue

        config['ip'] = match.group(1)
        config['mask'] = match.group(2)

    output = subprocess.check_output('ip route', shell=True).split('\n')
    for line in output:
        match = re.match(r'^\s*default via (\d+\.\d+\.\d+\.\d+)', line)
        if not match:
            continue

        config['gw'] = match.group(1)

    with open('/etc/resolv.conf', 'r') as f:
        lines = f.readlines()
        for line in lines:
            match = re.match(r'^\s*nameserver (\d+\.\d+\.\d+\.\d+)', line)
            if not match:
                continue

            config['dns'] = match.group(1)

    return config


def set_ip_config(iface, ip, mask, gw, dns):
    # TODO detect /etc/network/interfaces and /data/etc/static_ip.conf format
    pass


def get_wifi(wpa_supplicant_conf):
    # TODO add support for BSSID
    logger.debug('reading wifi settings from %s', wpa_supplicant_conf)

    try:
        conf_file = open(wpa_supplicant_conf, 'r')

    except Exception as e:
        logger.error('could open wifi settings file %s: %s', wpa_supplicant_conf, e)

        return {
            'ssid': '',
            'psk': ''
        }

    lines = conf_file.readlines()
    conf_file.close()

    ssid = psk = ''
    in_section = False
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            continue

        if '{' in line:
            in_section = True

        elif '}' in line:
            in_section = False
            break

        elif in_section:
            m = re.search(r'ssid\s*=\s*"(.*?)"', line)
            if m:
                ssid = m.group(1)

            m = re.search(r'psk\s*=\s*"(.*?)"', line)
            if m:
                psk = m.group(1)

    if ssid:
        logger.debug('wifi is enabled (ssid = "%s")', ssid)

        return {
            'ssid': ssid,
            'psk': psk,
            'bssid': ''
        }

    else:
        logger.debug('wifi is disabled')

        return {
            'ssid': '',
            'psk': '',
            'bssid': ''
        }


def set_wifi(wpa_supplicant_conf, ssid, psk, bssid):
    # TODO add support for BSSID
    logger.debug('writing wifi settings to %s: ssid="%s", bssid="%s"', wpa_supplicant_conf, ssid, bssid)

    key_mgmt = 'WPA-PSK WPA-EAP' if psk else 'NONE'

    # will update the first configured network
    try:
        conf_file = open(wpa_supplicant_conf, 'r')

    except Exception as e:
        logger.error('could open wifi settings file %s: %s', wpa_supplicant_conf, e)

        return False

    lines = conf_file.readlines()
    conf_file.close()

    in_section = False
    found_ssid = False
    found_psk = False
    found_key_mgmt = False
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#'):
            i += 1
            continue

        if '{' in line:
            in_section = True

        elif '}' in line:
            in_section = False
            if ssid and not found_ssid:
                lines.insert(i, '    ssid="' + ssid + '"\n')
            if psk and not found_psk:
                lines.insert(i, '    psk="' + psk + '"\n')
            if not found_key_mgmt:
                lines.insert(i, '    key_mgmt=' + key_mgmt + '\n')

            found_psk = found_ssid = found_key_mgmt = True

            break

        elif in_section:
            if ssid:
                if re.match(r'ssid\s*=\s*".*?"', line):
                    lines[i] = '    ssid="' + ssid + '"\n'
                    found_ssid = True

                elif re.match(r'psk\s*=\s*".*?"', line):
                    if psk:
                        lines[i] = '    psk="' + psk + '"\n'
                        found_psk = True

                    else:
                        lines.pop(i)
                        i -= 1

                elif re.match(r'key_mgmt\s*=\s*.*?', line):
                    lines[i] = '    key_mgmt=' + key_mgmt + '\n'
                    found_key_mgmt = True

            else:  # wifi disabled
                if re.match(r'ssid\s*=\s*".*?"', line) or re.match(r'psk\s*=\s*".*?"', line):
                    lines.pop(i)
                    i -= 1

        i += 1

    if ssid and not found_ssid:
        lines.append('network={\n')
        lines.append('    scan_ssid=1\n')
        lines.append('    ssid="' + ssid + '"\n')
        lines.append('    psk="' + psk + '"\n')
        lines.append('    key_mgmt=' + key_mgmt + '\n')
        lines.append('}\n\n')

    try:
        conf_file = open(wpa_supplicant_conf, 'w')

    except Exception as e:
        logger.error('could open wifi settings file %s: %s', wpa_supplicant_conf, e)

        return False

    for line in lines:
        conf_file.write(line)

    conf_file.close()

    return True
