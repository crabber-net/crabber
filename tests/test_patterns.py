from collections.abc import Sequence
from flask import escape
import patterns


def check_pattern(pattern, sample, exact=False, strip=False):
    """Returns whether the pattern matched anywhere in the sample.

       If the sample is a sequence then the first value will be treated as the sample and
       the rest will be treated as validation groups.
    """
    if isinstance(sample, str):
        validation_groups = None
    elif isinstance(sample, Sequence):
        sample, *validation_groups = sample
    else:
        raise TypeError('value must be str or recursive collection or str')

    match = pattern.search(sample)
    if match:
        if validation_groups:
            return all([
                a.strip() if strip else a == b
                for a, b in zip(match.groups(), validation_groups)
            ])
        return True
    return False


def assert_positive(pattern, samples, map_func=None, strip=False):
    """Checks pattern against each sample and asserts all have matches."""
    if map_func:
        samples = deep_map(map_func, samples)
    assert all([check_pattern(pattern, sample, strip=strip) for sample in samples])


def assert_negative(pattern, samples, map_func=None, strip=False):
    """Checks pattern against each sample and asserts no matches."""
    if map_func:
        samples = deep_map(map_func, samples)
    assert not any([check_pattern(pattern, sample, strip=strip) for sample in samples])


def deep_map(func, value):
    """Maps `func` to str or str collection recursively."""
    if isinstance(value, str):
        return func(value)
    elif isinstance(value, Sequence):
        return [deep_map(func, elem) for elem in value]
    else:
        raise TypeError('value must be str or recursive collection or str')


def test_ext_link():
    positive_samples = [
        "https://crabber.net",
        "https://crabber.net/moderation/?molt_id=1&viewing=molt",
        "http://reddit.com",
        "https://www.discogs.com/user/jakeledoux/collection",
        "element.io",
        "google.com",
        "www.google.com",
    ]

    assert_positive(patterns.ext_link, positive_samples)

    negative_samples = [
        "i'm so done.lol",
        "This is just a regular sentence. this bad gram gram.",
        "I saw Santa Claus shooting up in the Family Video restroom.",
        "umm.... what did you say?",
        "http was deprecated in favor of https, which means you can't use "
        "android apps that steal people's facebook logins with man in the "
        "middle attacks like the good old days. I miss 2012.",
        "ftp://bezos's bank account and grab me a few million",
        "www.lol",
        '<a href="https://tumblr.com">',
    ]

    assert_negative(patterns.ext_link, negative_samples)


def test_ext_md_link():
    positive_samples = [
        "[crabber](https://crabber.net)",
        "[this molt](https://crabber.net/moderation/?molt_id=1&viewing=molt)"
        "[reddit: the front page of the internet](http://reddit.com)",
        "[my CD collection on discogs]"
        "(https://www.discogs.com/user/jakeledoux/collection)",
        "[Element, a Matrix client](element.io)",
        "Why don't you [google](google.com) it?",
        "[caps are allowed](gOoGlE.cOm)",
    ]

    assert_positive(patterns.ext_md_link, positive_samples)

    negative_samples = [
        "[I'M SPAMBOY AND I (IF YOU DIDN'T KNOW) TALK IN BRACKETS]"
        "[brackets then] (parentheses.gov)"
        "empty: []()"
        "partial empty: [](google.com)"
    ]

    assert_negative(patterns.ext_md_link, negative_samples)


def test_spoiler_tag():
    positive_samples = [
        (">!spoiler?<", "spoiler?"),
        ("this is a spoiler --> >!boo!< <-- that was a spoiler!", "boo!"),
        ("""
        multiline spiler
        >!

        the cake is the truth

        <
        """, "the cake is the truth"),
    ]

    # Spoiler tag operates on HTML-escaped strings
    def escape_string(s):
        return str(escape(s))

    assert_positive(patterns.spoiler_tag, positive_samples, map_func=escape_string,
                    strip=True)

    negative_samples = [">> ! << !< >!< wowah!"]

    assert_negative(patterns.spoiler_tag, negative_samples, map_func=escape_string)
