import re

mention = re.compile(
    r'(?:^|\s|<br>)(?<!\\)@([\w]{1,32})(?!\w)')
tag = re.compile(
    r'(?:^|\s|<br>)(?<!\\)%([\w]{1,16})(?!\w)')
username = re.compile(
    r'^\w+$')
youtube = re.compile(
    r'(?:https?://)?(?:www.)?(?:youtube\.com/watch\?(?:[^&]+&)*v=|youtu\.be/)(\S{11})')
giphy = re.compile(
    r'https://(?:media\.)?giphy\.com/\S+[-/](\w{13,21})(?:\S*)')
ext_img = re.compile(
    r'(https://\S+\.(gif|jpe?g|png))(?:\s|$)')
ext_link = re.compile(
    r'(?<!href=[\'"])(https?://\S+)')
ext_md_link = re.compile(
    r'\[([^\]\(\)]+)\]\((http[^\]\(\)]+)\)')
timezone = re.compile(
    r'^-?(1[0-2]|0[0-9]).\d{2}$')
pretty_url = re.compile(
    r'(?:https?://)?(?:www\.)?((?:(?:[\w_-]+\.?)+/?)+)'
)
# Captures root of url (e.g. reddit.com or crabber.net)
url_root = re.compile(
    r'(?:https?://)?([^\s/]+)(?:\S*)'
)
# Captures essential part of URL (e.g. reddit.com/u/jaik_ or
# crabber.net/timeline)
url_essence = re.compile(
    r'(?:https?://)?(?:www\.)?((?:(?:[\w_-]+\.?)+/?)+)'
)
