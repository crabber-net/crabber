function loadHTML(url) {
    return false;

    if (url.match(/logout\/?$/)) {
        window.location.href = url;
        return false;
    }

    // Make request
    $.ajax({
        url: url,
        type: 'GET',
        data: {'ajax_json': true},
        success: function(data) {
            if (!url.match(/\/(?:$|\?)/))
                url += '/';

            window.history.pushState(data.body, `${data.title} | Crabber`, url);

            // Insert HTML
            $("title").html(`${data.title} | Crabber`);
            $("#content-heading strong").html(data.heading);
            $("#content-body").html(data.body);

            $("#content-body").scrollTop(0, {behaviour: 'auto'});

            // Update navbar icons
            let oldPageButton = $('#nav-active');
            oldPageButton.attr('id', null);
            oldPageButton.children('.btn-icon-f').addClass('d-none');

            let loadingIcon = $('.loading-icon:not(.d-none)');
            loadingIcon.addClass('d-none');
            let newPageButton = loadingIcon.parents('button');
            newPageButton.attr('id', 'nav-active');
            newPageButton.blur();
            loadingIcon.siblings('.btn-icon-f').removeClass('d-none');

            if (!oldPageButton.is(loadingIcon.parent())) {
                oldPageButton.children('.btn-icon:not(.btn-icon-f):not(.loading-icon)').removeClass('d-none');
            }

            // Update last-refresh meta tag (for new molt indicators)
            $(`meta[name='last-refresh']`).attr('content', Date.now().toString().substr(0, 10));
        },
        error: function() {
            // Failed to load page, navigating directly.
            console.error('AJAX ERROR: Failed to load page.')
            window.location.href = url;
        }
    });
}

$(function() {
    $('#nav-panel form:not(.no-ajax)').submit(function() {
        loadHTML(this.action);
        return false;
    });
})
