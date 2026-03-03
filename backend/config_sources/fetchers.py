"""Config source fetch dispatch and transport implementations."""

import logging
import os
import stat
import tempfile

from django.utils import timezone
from netmiko import ConnectHandler

logger = logging.getLogger(__name__)


def fetch_config(device):
    """Fetch config for a device from its configured source.

    Dispatches to the appropriate transport handler based on source_type.
    Updates device.last_fetched_config and device.config_fetched_at.

    Returns the config text.
    """
    source = device.config_source
    if source is None:
        raise ValueError(
            f"Device '{device.name}' has no config source configured"
        )

    match source.source_type:
        case "ssh":
            text = _fetch_ssh(source.sshconfigsource, device)
        case _:
            raise ValueError(
                f"Unsupported config source type: {source.source_type}"
            )

    device.last_fetched_config = text
    device.config_fetched_at = timezone.now()
    device.save(update_fields=["last_fetched_config", "config_fetched_at"])
    return text


def _fetch_ssh(ssh_source, device):
    """Connect via netmiko and run the config dump command."""
    ndt = ssh_source.netmiko_device_type
    command = ssh_source.command_override or ndt.default_command

    connect_params = {
        "device_type": ndt.driver,
        "host": ssh_source.hostname or device.hostname,
        "port": ssh_source.port,
        "username": ssh_source.username,
        "password": ssh_source.password,
        "timeout": ssh_source.timeout,
    }

    key_path = None
    if ssh_source.ssh_key:
        key_path = _write_temp_key(ssh_source.ssh_key)
        connect_params["use_keys"] = True
        connect_params["key_file"] = key_path

    try:
        with ConnectHandler(**connect_params) as conn:
            send_kwargs = {}
            if ssh_source.prompt_overrides:
                send_kwargs.update(ssh_source.prompt_overrides)
            output = conn.send_command(command, **send_kwargs)
        return output
    finally:
        if key_path:
            _cleanup_temp_key(key_path)


def _write_temp_key(key_text):
    """Write SSH key to a temp file with restrictive permissions."""
    fd, path = tempfile.mkstemp(prefix="netaudit_ssh_", suffix=".key")
    try:
        os.write(fd, key_text.encode())
    finally:
        os.close(fd)
    os.chmod(path, stat.S_IRUSR)
    return path


def _cleanup_temp_key(path):
    """Remove a temporary SSH key file."""
    try:
        os.unlink(path)
    except OSError:
        logger.warning("Failed to clean up temp SSH key: %s", path)
