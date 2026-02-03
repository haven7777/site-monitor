import json
import os

CONFIG_FILE = "sites.json"

def load_sites():
    """Load sites from config file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default sites
        default_sites = [
            "https://google.com",
            "https://github.com",
            "https://stackoverflow.com",
        ]
        save_sites(default_sites)
        return default_sites

def save_sites(sites):
    """Save sites to config file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(sites, f, indent=2)

def add_site(url):
    """Add a new site to monitor"""
    sites = load_sites()
    if url not in sites:
        sites.append(url)
        save_sites(sites)
        return True
    return False

def remove_site(url):
    """Remove a site from monitoring"""
    sites = load_sites()
    if url in sites:
        sites.remove(url)
        save_sites(sites)
        return True
    return False