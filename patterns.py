import re

muted_words = re.compile(r"[^a-z0-9, ]+")
mention = re.compile(r"(?:^|\s|<br>|&nbsp;)(?<!\\)@([\w]{1,32})(?!\w)")
tag = re.compile(r"(?:^|\s|<br>|&nbsp;)(?<!\\)%([\w]{1,})(?!\w)")
username = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
only_underscores = re.compile(r"^_+$")
spoiler_tag = re.compile(r"&gt;!((?:.|\n)+?)&lt;")  # Only works after HTML escaping
youtube = re.compile(
    r"(?:https?://)?"
    r"(?:www.)?"
    r"(?:youtube\.com/watch\?(?:[^&]+&)*v=|youtu\.be/|youtube\.com/shorts/)"
    r"(\S{11})(?:[?&]\w+=\w+)?"
)
giphy = re.compile(r"https://(?:media\d?\.)?giphy\.com/\S+[-/](\w{13,21})(?:\S*)")
ext_img = re.compile(r"(https?://\S+\.(gif|jpe?g|png))(?:\?(?:\w+=\w+&?))?(?:\s|$)")
# fmt: off
link_basic = (
    r"(?:https?://)\S+"
    r"|"
    r"(?:www\.)?\w{3,}\.(?i:com|net|org|gov|io)"
)
ext_link = re.compile(
    r"(?<!href=['\"])(\s|^|>)\b"
    r"(" + link_basic + r")"
)
# fmt: on
ext_md_link = re.compile(rf"\[([^\]\(\)]+)\]\(({link_basic})\)")
timezone = re.compile(r"^-?(1[0-2]|0[0-9]).\d{2}$")
pretty_url = re.compile(r"(?:https?://)?(?:www\.)?((?:(?:[\w_-]+\.?)+/?)+)")
# Captures root of url (e.g. reddit.com or crabber.net)
url_root = re.compile(r"(?:https?://)?([^\s/]+)(?:\S*)")
# Captures essential part of URL (e.g. reddit.com/u/jaik_ or
# crabber.net/timeline)
url_essence = re.compile(r"(?:https?://)?(?:www\.)?((?:(?:[\w_-]+\.?)+/?)+)")

# Social links
social_discord = re.compile(r"^[^@#:`\"]{2,32}#\d{4}$")
social_spacehey = re.compile(
    r"^(?:https://)?spacehey\.com/(?:profile\?id=\d+|(\w{2,}))$"
)
social_spotify = re.compile(
    r"^(?:https://)?open\.spotify\.com/user/([\w]+)/?(?:\?(?:\w+=\w+&?))?$"
)
social_twitch = re.compile(r"^(?:https://)?(?:www\.)?twitch\.tv/([\w]+)/?$")
social_youtube = re.compile(
    r"^(?:https://)?(?:www\.)?youtube\.com/(?:c|channel)/([\w]+)/?$"
)
# Matches generic usernames
social_misc = re.compile(r"^\w{2,128}$")
social_nintendo = re.compile(r"^SW(?:-\d{4}){3}$")

protocol_identifier = re.compile(r"^\w+://.*$")
