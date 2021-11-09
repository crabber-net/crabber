import patterns
import pytest


def assert_positive(pattern, samples):
    """Checks pattern against each sample and asserts all have matches."""
    assert all([pattern.search(sample) for sample in samples])


def assert_negative(pattern, samples):
    """Checks pattern against each sample and asserts no matches."""
    assert not any([pattern.search(sample) for sample in samples])


def test_ext_link():
    positive_samples = [
        "https://crabber.net",
        "https://crabber.net/moderation/?molt_id=1&viewing=molt" "http://reddit.com",
        "https://www.discogs.com/user/jakeledoux/collection",
        "element.io",
        "google.com",
    ]

    assert_positive(patterns.ext_link, positive_samples)

    negative_samples = [
        "i'm so done.lol",
        "This is just a regular sentence. this bad gram gram.",
        "I saw Santa Clause shooting up in the Family Video bathroom.",
        "umm.... what did you say?",
        "http was deprecated in favor of https, which means you can't use "
        "android apps that steal people's facebook logins with man in the "
        "middle attacks like the good old days. I miss 2012.",
        "ftp://bezos's bank account and grab me a few million",
        "www.lol",
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
