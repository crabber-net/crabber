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
        raise TypeError("value must be str or recursive collection or str")

    match = pattern.search(sample)
    if match:
        if validation_groups:
            return all(
                [
                    a.strip() if strip else a == b
                    for a, b in zip(match.groups(), validation_groups)
                ]
            )
        return True
    return False


def assert_positive(pattern, samples, map_func=None, strip=False):
    """Checks pattern against each sample and asserts all have matches."""
    if map_func:
        samples = deep_map(map_func, samples)
    for sample in samples:
        assert check_pattern(pattern, sample, strip=strip)


def assert_negative(pattern, samples, map_func=None, strip=False):
    """Checks pattern against each sample and asserts no matches."""
    if map_func:
        samples = deep_map(map_func, samples)
    for sample in samples:
        print(f"Checking: {sample!r}")
        assert not check_pattern(pattern, sample, strip=strip)


def deep_map(func, value):
    """Maps `func` to str or str collection recursively."""
    if isinstance(value, str):
        return func(value)
    elif isinstance(value, Sequence):
        return [deep_map(func, elem) for elem in value]
    else:
        raise TypeError("value must be str or recursive collection or str")


def test_ext_link():
    positive_samples = [
        "https://crabber.net",
        "https://crabber.net/moderation/?molt_id=1&viewing=molt",
        "http://reddit.com",
        "https://www.discogs.com/user/jakeledoux/collection",
        "element.io",
        "google.com",
        "www.google.com",
        "<span class=\"molt-content-spoiler spoiler-revealed\">doodoo.net</span>"
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
        "[this molt](https://crabber.net/moderation/?molt_id=1&viewing=molt)",
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


def test_giphy():
    positive_samples = [
        (
            "https://media1.giphy.com/media/l1Ku8UGWpTlyHuD0A/giphy.gif"
            "?cid=5e21488638475200d85aaa60946db16d7ac6cd66a43061e3&rid=giphy.gif&ct=g"
        ),
        "https://media1.giphy.com/media/l1Ku8UGWpTlyHuD0A/giphy.gif",
        "https://media.giphy.com/media/l1Ku8UGWpTlyHuD0A/giphy.gif",
        (
            "https://giphy.com/gifs/starwars-star-wars-the-empire-strikes-back-"
            "l1Ku8UGWpTlyHuD0A"
        ),
    ]

    assert_positive(patterns.giphy, positive_samples)

    negative_samples = [
        "https://crabber.net",
        "https://crabber.net/moderation/?molt_id=1&viewing=molt",
        "http://reddit.com",
        "https://www.discogs.com/user/jakeledoux/collection",
        "element.io",
        "google.com",
        "www.google.com",
    ]

    assert_negative(patterns.giphy, negative_samples)


def test_spoiler_tag():
    positive_samples = [
        (">!spoiler?<", "spoiler?"),
        ("this is a spoiler --> >!boo!< <-- that was a spoiler!", "boo!"),
        (
            """
        multiline spiler
        >!

        the cake is the truth

        <
        """,
            "the cake is the truth",
        ),
    ]

    # Spoiler tag operates on HTML-escaped strings
    def escape_string(s):
        return str(escape(s))

    assert_positive(
        patterns.spoiler_tag, positive_samples, map_func=escape_string, strip=True
    )

    negative_samples = [">> ! << !< >!< wowah!"]

    assert_negative(patterns.spoiler_tag, negative_samples, map_func=escape_string)


def test_social_discord():
    positive_samples = [
        "myspacetom#7777",
        "pixelator#2000",
        "nostone48#5523",
    ]

    assert_positive(patterns.social_discord, positive_samples)

    negative_samples = [
        "myspacetom#7777237",
        "pixelator#2000#7234",
        "no@stone48#5523",
    ]

    assert_negative(patterns.social_discord, negative_samples)


def test_social_spacehey():
    positive_samples = [
        "https://spacehey.com/jsl",
        "https://spacehey.com/an",
        "https://spacehey.com/profile?id=544334",
        "spacehey.com/profile?id=544334",
    ]

    assert_positive(patterns.social_spacehey, positive_samples)

    negative_samples = [
        "an",
        "jsl",
        "https://spacehey.com/",
        "https://spacehey.com/bulletin?id=100883",
        "crabber.net",
    ]

    assert_negative(patterns.social_spacehey, negative_samples)


def test_social_spotify():
    positive_samples = [
        "https://open.spotify.com/user/nyanjaik?si=20c10e5787124dc1",
        "open.spotify.com/user/12174615111",
    ]

    assert_positive(patterns.social_spotify, positive_samples)

    negative_samples = [
        "https://open.spotify.com/track/1SM0W2SbObwBgCIQtyX0JC?si=11681010247c40e3",
        "https://open.spotify.com/artist/126FigDBtqwS2YsOYMTPQe?si=8dcc603644204870"
        "https://www.spotify.com/us/",
    ]

    assert_negative(patterns.social_spotify, negative_samples)


def test_social_twitch():
    positive_samples = [
        "https://www.twitch.tv/jakefromspace",
        "twitch.tv/szyzyg",
    ]

    assert_positive(patterns.social_twitch, positive_samples)

    negative_samples = [
        "https://www.twitch.tv/videos/1201229591",
        "https://www.twitch.tv/settings/profile",
        "https://www.twitch.tv/abney317/schedule",
    ]

    assert_negative(patterns.social_twitch, negative_samples)


def test_social_youtube():
    positive_samples = [
        "https://www.youtube.com/channel/UCthIWSlSuCp93LF_7GR0Qpg",
        "https://www.youtube.com/c/TomScottGo",
        "https://www.youtube.com/c/Corridor",
    ]

    assert_positive(patterns.social_youtube, positive_samples)

    negative_samples = [
        "https://spacehey.com/",
        "https://spacehey.com/bulletin?id=100883",
        "https://www.youtube.com/playlist?list=FLthIWSlSuCp93LF_7GR0Qpg",
        (
            "https://www.youtube.com/watch?v=QDGlgH_ZsrY"
            "&list=FLthIWSlSuCp93LF_7GR0Qpg&index=8"
        ),
        "https://www.youtube.com/watch?v=aW2LvQUcwqc",
    ]

    assert_negative(patterns.social_youtube, negative_samples)


def test_social_nintendo():
    positive_samples = [
        "SW-8496-9128-4205",
        "SW-1234-5678-9012",
        "SW-2357-9512-2746",
    ]

    assert_positive(patterns.social_nintendo, positive_samples)

    negative_samples = [
        "8496-9128-4205",
        "SW-8496-9128-4205-1572",
    ]

    assert_negative(patterns.social_nintendo, negative_samples)


def test_protocol_identifier():
    positive_samples = [
        "http://localhost",
        "https://myspace.com",
        "ftp://crabstorage.net",
    ]

    assert_positive(patterns.protocol_identifier, positive_samples)

    negative_samples = [
        "localhost",
        "www.myspace.com",
        "crabstorage.net",
    ]

    assert_negative(patterns.protocol_identifier, negative_samples)
