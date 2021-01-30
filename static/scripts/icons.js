iterations = 0;
function loadIcons() {
    // Finds and replaces all jam-icon <span> elements with SVG images.

    $('span[data-jam]').each(function() {
        let iconSpan = $(this);
        iconID = iconSpan.data('jam');

        $.ajax({
            url: `/static/img/jam-icons/${iconID}.svg`,
            success: function(data) {
                iterations += 1;
                let svg = $(data.children);
                svg.attr('width', iconSpan.data('width'));
                svg.attr('height', iconSpan.data('height'));
                svg.attr('class', iconSpan.attr('class'));
                svg.attr('id', iconSpan.attr('id'));
                iconSpan.replaceWith(svg);
            }
        });
    });
    console.log('Iterations', iterations);
}
