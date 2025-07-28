import json
import os
from logger import log

# This file remains mostly the same, just adding log messages
# ... (DEFAULT_CONFIGS is the same as the previous step) ...
CONFIG_FILE = 'configs.json'
DEFAULT_CONFIGS = {
    # Same as previous step, with corrected base URLs
    "last_selected_client":"MUSHclient","clients":{"MUSHclient":{"name":"MUSHclient","soundpack_path":"","scripts_repo_url":"http://nathantech.net:3000/api/v1/repos/CosmicRage/Mush-Soundpack","sounds_repo_url":"http://nathantech.net:3000/api/v1/repos/CosmicRage/CosmicRageSounds","scripts_target_subdir":"","sounds_target_subdir":"cosmic rage/worlds/cosmic rage/sounds","sounds_subfolder":"ogg","exclusions":["cosmic rage/worlds/cosmic rage/cosmic rage.mcl"],"advanced_settings":{"scan_workers":4,"download_workers":8,"advanced_enabled":False}},"VIP Mud":{"name":"VIP Mud","soundpack_path":"","scripts_repo_url":"http://nathantech.net:3000/api/v1/repos/CosmicRage/VIPMudCosmicRageScripts","sounds_repo_url":"http://nathantech.net:3000/api/v1/repos/CosmicRage/CosmicRageSounds","scripts_target_subdir":"","sounds_target_subdir":"sounds","sounds_subfolder":"wav","exclusions":["settings.set","gags/"],"advanced_settings":{"scan_workers":4,"download_workers":8,"advanced_enabled":False}}}
}

def load_configs():
    log.debug(f"Attempting to load configs from {CONFIG_FILE}")
    if not os.path.exists(CONFIG_FILE):
        log.warning(f"Config file not found. Creating a new one with defaults.")
        save_configs(DEFAULT_CONFIGS)
    with open(CONFIG_FILE, 'r') as f:
        configs = json.load(f)
        for name, client in configs.get("clients", {}).items():
            if "scripts_target_subdir" not in client:
                client["scripts_target_subdir"] = DEFAULT_CONFIGS["clients"][name].get("scripts_target_subdir", "")
            if "sounds_target_subdir" not in client:
                client["sounds_target_subdir"] = DEFAULT_CONFIGS["clients"][name].get("sounds_target_subdir", "")
        return configs

def save_configs(configs):
    log.debug(f"Saving configs to {CONFIG_FILE}")
    with open(CONFIG_FILE, 'w') as f:
        json.dump(configs, f, indent=4)

def reset_to_defaults():
    log.warning("Resetting config file to factory defaults.")
    save_configs(DEFAULT_CONFIGS)
    return DEFAULT_CONFIGS

def get_client_config(client_name):
    configs = load_configs()
    return configs.get('clients', {}).get(client_name, {})

def update_config_value(client_name, key, value):
    log.debug(f"Updating config for '{client_name}': Set '{key}' to '{value}'")
    configs = load_configs()
    if 'clients' not in configs: configs['clients'] = {}
    if client_name not in configs['clients']:
        configs['clients'][client_name] = DEFAULT_CONFIGS['clients'].get(client_name, {})
    configs['clients'][client_name][key] = value
    save_configs(configs)

def set_last_selected_client(client_name):
    log.debug(f"Setting last selected client to: {client_name}")
    configs = load_configs()
    configs['last_selected_client'] = client_name
    save_configs(configs)
