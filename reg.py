import re

# Regex stuff
mention_pattern = re.compile(r'(?<!\\)@([\w]{1,32})(?!\w)')
tag_pattern = re.compile(r'(?<!\\)%([\w]{1,16})(?!\w)')
username_pattern = re.compile(r'^\w+$')

# Tweet
tweet = "This is a test mention of @jake and @mezrah too!"


def label_mentions(content):
    output = content
    match = mention_pattern.search(output)
    if match:
        start, end = match.span()
        output = "".join([output[:start],
                          f'<a href="/user/{match.group(1)}" class="mention">',
                          output[start:end],
                          '</a>',
                          label_mentions(output[end:])])
    return output
