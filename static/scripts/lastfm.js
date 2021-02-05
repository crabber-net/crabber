function getNowPlaying(username) {
    let api_key = "7d46cfc3d2c68c0f50504b7a09516898";
    $.ajax({
        url: "https://ws.audioscrobbler.com/2.0/",
        data: {
            'method': 'user.getrecenttracks',
            'user': username,
            'limit': 1,
            'api_key': api_key,
            'format': 'json'
        },
        success: updateLastfm,
        error: function(data) {
            $(".lastfm-loading em").text("failed to load last.fm");
            console.warn(data);
        }
    })
    $.ajax({
        url: "https://ws.audioscrobbler.com/2.0/",
        data: {
            'method': 'user.getLovedTracks',
            'user': username,
            'limit': 1,
            'api_key': api_key,
            'format': 'json'
        },
        success: updateLastfmLoved,
        error: function(data) {
            $("#loved-loading em").text("failed to load loved tracks");
            console.warn(data);
        }
    })
}

function updateLastfm(data) {
    var currentTrack = data.recenttracks.track[0];
    var totalScrobbles = parseInt(data.recenttracks['@attr'].total).toLocaleString();

    // Currently playing or last played
    if (!(currentTrack["@attr"] && currentTrack["@attr"].nowplaying)) {
        $("#lastfm-status").text("last played");
    }
    // Hide loading message
    $(".lastfm-loading").addClass("d-none");

    // Update track info
    // append ' em' to selector to make it italic
    $("#lastfm-artist").text(currentTrack.artist["#text"]);
    $("#lastfm-track").text(currentTrack.name);

    // Update scrobble count
    $("#lastfm-scrobble-count").text(totalScrobbles);

    // Reveal last played/currently playing
    $("#lastfm-now-playing").removeClass("d-none");
    // Reveal scrobble count
    $("#lastfm-scrobbles").removeClass("d-none");
}

function updateLastfmLoved(data) {
    var lovedTracks = parseInt(data.lovedtracks['@attr'].total).toLocaleString();

    // Hide loading message
    $("#loved-loading").addClass("d-none");

    // Update loved count
    $("#lastfm-loved-count").text(lovedTracks);

    // Reveal loved count
    $("#lastfm-loved").removeClass("d-none");
}


