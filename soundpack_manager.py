import os
import json
import requests
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from logger import log

VERIFY_SSL = True
HASH_CACHE_FILE = 'local_hashes.json'

def get_remote_tree_fast(repo_api_url, cancellation_event):
    try:
        sanitized_repo_url = repo_api_url.rstrip('/').replace('/contents', '')
        parts = sanitized_repo_url.split('/api/v1/repos/')
        server_base, repo_full_name = parts[0], parts[1]

        branches_url = f"{sanitized_repo_url}/branches"
        branches_list = requests.get(branches_url, verify=VERIFY_SSL, timeout=15).json()

        if not isinstance(branches_list, list) or not branches_list:
            raise RuntimeError("Server API Error: Could not find any branches for this repository.")

        branch_names = [b.get('name') for b in branches_list]
        default_branch_details = None
        if 'main' in branch_names: default_branch_details = next(b for b in branches_list if b.get('name') == 'main')
        elif 'master' in branch_names: default_branch_details = next(b for b in branches_list if b.get('name') == 'master')
        else: default_branch_details = branches_list[0]

        default_branch_name = default_branch_details.get('name')
        commit_sha = default_branch_details.get('commit', {}).get('id')
        if not commit_sha or cancellation_event.is_set(): return {}

        tree_url = f"{sanitized_repo_url}/git/trees/{commit_sha}?recursive=1"
        tree_response = requests.get(tree_url, verify=VERIFY_SSL, timeout=20).json()
        if 'tree' not in tree_response: return {}

        file_list = {}
        base_download_url = f"{server_base}/{repo_full_name}/raw/branch/{default_branch_name}"
        for item in tree_response['tree']:
            if item.get('type') == 'blob':
                file_list[item['path']] = {'sha': item['sha'], 'url': f"{base_download_url}/{item['path']}"}
        return file_list
    except requests.exceptions.RequestException as e:
        log.critical(f"FATAL NETWORK ERROR in get_remote_tree_fast: {e}", exc_info=True)
        return None
    except Exception as e:
        log.critical(f"FATAL UNEXPECTED ERROR in get_remote_tree_fast: {e}", exc_info=True)
        return None

def calculate_sha1(filepath):
    try:
        with open(filepath, 'rb') as f: return hashlib.sha1(f.read()).hexdigest()
    except IOError: return None

def is_excluded(filepath, exclusions):
    for exclusion in exclusions:
        if exclusion.endswith('/') and filepath.startswith(exclusion): return True
        elif filepath == exclusion: return True
    return False

class SoundpackManager:
    def __init__(self, config, cancellation_event, progress_callback=None):
        self.config = config
        self.cancellation_event = cancellation_event
        self.progress_callback = progress_callback
        self.hash_cache = self.load_hash_cache()

    def send_progress(self, message, value=None, total=None):
        if self.progress_callback and not self.cancellation_event.is_set():
            self.progress_callback({'message': message, 'value': value, 'total': total})

    def load_hash_cache(self):
        try:
            if os.path.exists(HASH_CACHE_FILE):
                with open(HASH_CACHE_FILE, 'r') as f: return json.load(f)
        except (IOError, json.JSONDecodeError): pass
        return {}

    def save_hash_cache(self):
        try:
            with open(HASH_CACHE_FILE, 'w') as f: json.dump(self.hash_cache, f, indent=4)
        except IOError: pass

    def get_local_file_hashes(self, directory, num_workers):
        self.send_progress(f"Scanning local files in '{os.path.basename(directory) or 'main folder'}'...")
        if not os.path.exists(directory):
            self.send_progress(None, 1, 1); return {}

        current_hashes, files_to_hash = {}, []
        for root, _, files in os.walk(directory):
            for name in files:
                full_path, rel_path = os.path.join(root, name), os.path.relpath(os.path.join(root, name), directory).replace('\\', '/')
                try:
                    mtime, cached_data = os.path.getmtime(full_path), self.hash_cache.get(full_path)
                    if cached_data and cached_data.get('mtime') == mtime: current_hashes[rel_path] = cached_data['sha']
                    else: files_to_hash.append((full_path, rel_path, mtime))
                except OSError: continue

        if not files_to_hash:
            self.send_progress(None, 1, 1); return current_hashes

        with ThreadPoolExecutor(max_workers=num_workers) as ex:
            future_map = {ex.submit(calculate_sha1, f[0]): f for f in files_to_hash}
            for future in future_map:
                if self.cancellation_event.is_set(): return {}
                full_path, rel_path, mtime = future_map[future]
                sha1 = future.result()
                if sha1: current_hashes[rel_path], self.hash_cache[full_path] = sha1, {'mtime': mtime, 'sha': sha1}

        self.send_progress(None, 1, 1)
        return current_hashes

    def download_files_in_parallel(self, files, num_workers):
        if not files: self.send_progress(None, 1, 1); return
        self.send_progress(f"Downloading {len(files)} new or updated files...", 0, len(files))
        with ThreadPoolExecutor(max_workers=num_workers) as ex:
            future_map = {ex.submit(self.download_file, f['url'], f['dest']): f for f in files}
            for i, _ in enumerate(future_map):
                if self.cancellation_event.is_set(): break; self.send_progress(None, i + 1, len(files))

    def download_file(self, url, dest_path):
        if self.cancellation_event.is_set(): return
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with requests.get(url, stream=True, verify=VERIFY_SSL, timeout=30) as r:
                r.raise_for_status()
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self.cancellation_event.is_set(): return
                        f.write(chunk)
            sha1 = calculate_sha1(dest_path)
            if sha1: self.hash_cache[dest_path] = {'mtime': os.path.getmtime(dest_path), 'sha': sha1}
        except Exception: pass

    def update_component(self, repo_url, target_dir, scan_workers, dl_workers, comp_name, repo_subfolder_filter=None):
        self.send_progress(f"Fetching {comp_name} file list from server...")

        remote_files = get_remote_tree_fast(repo_url, self.cancellation_event)
        if remote_files is None:
            self.send_progress(f"ERROR: Failed to get {comp_name} file list. Check log.log for details.")
            return
        if self.cancellation_event.is_set(): return

        local_files = self.get_local_file_hashes(target_dir, scan_workers)
        if self.cancellation_event.is_set(): return

        self.send_progress(f"Comparing {comp_name} files...")
        files_to_dl, exclusions = [], self.config.get('exclusions', [])

        for path_from_repo, data in remote_files.items():
            if repo_subfolder_filter and not path_from_repo.startswith(repo_subfolder_filter + '/'): continue
            if is_excluded(path_from_repo, exclusions): continue

            if path_from_repo not in local_files or local_files[path_from_repo] != data['sha']:
                files_to_dl.append({'url': data['url'], 'dest': os.path.join(target_dir, path_from_repo)})

        if self.cancellation_event.is_set(): return
        self.download_files_in_parallel(files_to_dl, dl_workers)

    def run_update_or_install(self):
        try:
            adv_settings, base_path = self.config.get("advanced_settings", {}), self.config.get('soundpack_path', '')
            scan_workers, dl_workers = adv_settings.get("scan_workers", 4), adv_settings.get("download_workers", 8)

            if not base_path: self.send_progress("ERROR: Soundpack path is not set."); return

            log.info("--- Preparing to update SCRIPTS component ---")
            scripts_target_dir = os.path.join(base_path, self.config.get('scripts_target_subdir', ''))
            scripts_repo_url = self.config.get('scripts_repo_url')
            if scripts_repo_url: self.update_component(scripts_repo_url, scripts_target_dir, scan_workers, dl_workers, "scripts")
            else: log.warning("Skipping scripts: 'scripts_repo_url' not defined.")
            if self.cancellation_event.is_set(): return

            log.info("--- Preparing to update SOUNDS component ---")

            # --- THIS IS THE FIX ---
            # Correctly use 'sounds_target_subdir' for the sounds component.
            sounds_target_dir = os.path.join(base_path, self.config.get('sounds_target_subdir', ''))
            sounds_repo_url = self.config.get('sounds_repo_url')

            log.debug(f"Sounds component target directory calculated as: {sounds_target_dir}")

            if sounds_repo_url:
                self.update_component(
                    sounds_repo_url,
                    sounds_target_dir,
                    scan_workers,
                    dl_workers,
                    "sounds",
                    self.config.get('sounds_subfolder')
                )
            else: log.warning("Skipping sounds: 'sounds_repo_url' not defined.")
            if self.cancellation_event.is_set(): return

        except Exception as e:
            log.critical(f"A FATAL UNHANDLED ERROR occurred in the main update process: {e}", exc_info=True)
            self.send_progress(f"FATAL ERROR: {e}. Check log.log for details.")

        finally:
            self.save_hash_cache()
            if not self.cancellation_event.is_set():
                self.send_progress("Process finished.")
            else:
                self.send_progress("Process cancelled.")