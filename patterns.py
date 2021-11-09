import re

muted_words = re.compile(r"[^a-z0-9, ]+")
mention = re.compile(r"(?:^|\s|<br>)(?<!\\)@([\w]{1,32})(?!\w)")
tag = re.compile(r"(?:^|\s|<br>)(?<!\\)%([\w]{1,})(?!\w)")
username = re.compile(r"^[a-zA-Z0-9_]+$")
only_underscores = re.compile(r"^_+$")
youtube = re.compile(
    r"(?:https?://)?(?:www.)?(?:youtube\.com/watch\?(?:[^&]+&)*v=|youtu\.be/|youtube\.com/shorts/)(\S{11})(?:[?&]\w+=\w+)?"
)
giphy = re.compile(r"https://(?:media\.)?giphy\.com/\S+[-/](\w{13,21})(?:\S*)")
ext_img = re.compile(r"(https://\S+\.(gif|jpe?g|png))(?:\s|$)")
ext_link = re.compile(
    r'(?<!href=[\'"])('
    r"(?:https?://)\S+"
    r")"
)
ext_md_link = re.compile(rf"\[([^\]\(\)]+)\]\(({ext_link.pattern})" r"\)")
timezone = re.compile(r"^-?(1[0-2]|0[0-9]).\d{2}$")
pretty_url = re.compile(r"(?:https?://)?(?:www\.)?((?:(?:[\w_-]+\.?)+/?)+)")
# Captures root of url (e.g. reddit.com or crabber.net)
url_root = re.compile(r"(?:https?://)?([^\s/]+)(?:\S*)")
# Captures essential part of URL (e.g. reddit.com/u/jaik_ or
# crabber.net/timeline)
url_essence = re.compile(r"(?:https?://)?(?:www\.)?((?:(?:[\w_-]+\.?)+/?)+)")
