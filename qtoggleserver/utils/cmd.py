
import logging
import subprocess


logger = logging.getLogger(__name__)


def run_get_cmd(get_cmd, cmd_name=None, log_values=True, exc_class=None, required_fields=None):
    exc_class = exc_class or Exception

    try:
        config = subprocess.check_output(get_cmd, stderr=subprocess.STDOUT, shell=True)

    except Exception as e:
        raise exc_class('{} get command failed: {}'.format(cmd_name or get_cmd, e)) from e

    config = config.strip().decode()
    config_lines = config.split('\n')
    config_dict = {}
    for line in config_lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split('=', 1)
        if len(parts) == 1:
            parts.append('')

        key, value = parts
        key = key.lower()[3:]  # strip leading "QS_"
        if value.startswith('"'):
            value = value[1:]
        if value.endswith('"') and not value.endswith('\\"'):
            value = value[:-1]

        config_dict[key] = value

    if cmd_name:
        if log_values:
            values_str = ', '.join(['{} = "{}"'.format(k, v) for k, v in sorted(config_dict.items())])
            logger.debug('got %s: %s', cmd_name, values_str)

        else:
            logger.debug('got %s', cmd_name)

    for field in required_fields or []:
        if field not in config_dict:
            msg = 'missing {} field'.format(field)
            if cmd_name:
                msg = 'invalid {}: {}'.format(cmd_name, msg)

            raise exc_class(msg)

    return config_dict


def run_set_cmd(set_cmd, cmd_name=None, log_values=True, exc_class=None, **config):
    env = {'QS_{}'.format(k.upper()): v for k, v in config.items()}

    exc_class = exc_class or Exception

    try:
        subprocess.check_output(set_cmd, env=env, stderr=subprocess.STDOUT, shell=True)

    except Exception as e:
        raise exc_class('{} set command failed: {}'.format(cmd_name or set_cmd, e)) from e

    if cmd_name:
        if log_values:
            values_str = ', '.join(['{} = "{}"'.format(k, v) for k, v in sorted(config.items())])
            logger.debug('%s set to: %s', cmd_name, values_str)

        else:
            logger.debug('%s set', cmd_name)
