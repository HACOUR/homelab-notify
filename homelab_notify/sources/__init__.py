"""Source parsers: turn a webhook payload into an Event."""
from . import generic, proxmox, synology, uptimekuma

PARSERS = {
    "proxmox": proxmox.parse,
    "uptimekuma": uptimekuma.parse,
    "synology": synology.parse,
    "generic": generic.parse,
}
