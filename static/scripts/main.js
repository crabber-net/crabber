// AJAX Form Submit
function SubForm(form, url=null, success=null, error=null) {
    if (url == null) {
        url = document.location.pathname;
        if (!url.endsWith('/'))
            url += '/'
    }
    $.ajax({
        url: url,
        type: 'post',
        data: $(form).serialize(),
        success: success,
        error: function () {
            console.warn("Failed to submit form to server;");
            if (error != null) {
                error();
            }
        },
    });
}

function GetData(request_type, data, callback, error_callback=null) {
    // Create deep copy
    var request_data = JSON.parse(JSON.stringify(data));

    // Timestamp asking for substitution
    if (request_data.timestamp == -1) {
        request_data.timestamp = $("meta[name='last-refresh']").attr("content");
    }

    $.ajax({
        url: "/ajax_request/" + request_type + "/",
        type: 'get',
        data: request_data,
        success: function (response) {
            callback(response);
        },
        error: error_callback
    });
}

function changeContent(el, newText) {
    $(el).text(newText);
}

function toggleLike(e) {
    let empty_heart = $(e).children("svg")[0];
    let filled_heart = $(e).children("svg")[1];
    let counter = $(e).children("span").get(0);

    let updateLikeCounter = function(amount) {
        likesCounter = $(e).parents('.mini-molt').find('[data-target="#molt_likes_modal"]');
        likesNum = parseInt(likesCounter.children('#likes-number').text());
        likesNum += amount;
        likesCounter.children('#likes-number').text(likesNum);
        likesCounter.children('#likes-text').text((likesNum == 1) ? 'Like' : 'Likes');
    };

    // was liked, needs to be unliked
    if (empty_heart.classList.contains("d-none")) {
        $(empty_heart).removeClass("d-none");
        $(filled_heart).addClass("d-none");
        if (counter != undefined) {
            $(counter).removeClass("text-primary");
            counter.textContent = parseInt(counter.textContent) - 1;
        } else {
            updateLikeCounter(-1)
        }
    }
    // was unliked, needs to be liked
    else {
        $(filled_heart).removeClass("d-none");
        $(empty_heart).addClass("d-none");
        if (counter != undefined) {
            $(counter).addClass("text-primary");
            counter.textContent = parseInt(counter.textContent) + 1;
        } else {
            updateLikeCounter(1)
        }
    }
}

function toggleFollow(e) {
    if (e.form.user_action.value == "unfollow") {
        e.form.user_action.value = "follow";
        $(e).find('strong').text('Follow');
        $(e).removeClass('btn-primary');
        $(e).addClass('btn-outline-primary');
    } else {
        e.form.user_action.value = "unfollow";
        $(e).find('strong.default-text').text('Following');
        $(e).find('strong.hover-text').text('Unfollow');
        $(e).removeClass('btn-outline-primary');
        $(e).addClass('btn-primary');
    }
}

function clearModal() {
    // Clear text
    $("#compose_modal textarea").val("")
    // Hide modal
    $("#compose_modal").modal("hide")
}

function openNewTab(url) {
    let win = window.open(url, '_blank');
    win.focus();
}

function prepareQuote(molt_id, author_username, author_name) {
    // Update "replying to" link
    $("#quote-to").text(author_name)
    $("#quote-to").attr("href", "/user/" + author_username)
    // Update form quote-to ID
    $("#quote-molt-id").val(molt_id)

    // Show quote modal
    $('#compose_quote_modal').modal('show');
}

function prepareReply(molt_id, author_username, author_name) {
    // Update "replying to" link
    $("#reply-to").text(author_name)
    $("#reply-to").attr("href", "/user/" + author_username)
    // Update form reply-to ID
    $("#reply-molt-id").val(molt_id)

    // Show reply modal
    $('#compose_reply_modal').modal('show');
}

function prepareEdit(molt_id) {
    // Update form edit-molt content
    $("#edit-content").val($("#molt-content-" + molt_id).attr("data-content"))
    // Update form edit-molt ID
    $("#edit-molt-id").val(molt_id)
    // Update character counter
    updateCounter.call($('#edit_molt_modal textarea'));

    // Show edit modal
    $('#edit_molt_modal').modal('show');
}

// Set notification badge to 'unread_count'
function updateNotifBadge(unread_count) {
    var badge = $(".notif-badge");

    if (unread_count > 0) {
        badge.removeClass("d-none");
        badge.text(unread_count);
    }
    else {
        badge.addClass("d-none");
    }
}

// Set new molt indicator to 'molt_count'
function updateNewMoltIndicator(molt_count) {
    if (molt_count > 0) {
        // Update counter
        $("#new-molt-counter").text(molt_count);
        // Update the s in 'new molts'
        $("#new-molt-s").text((molt_count == 1) ? "" : "s");
        // Made indicator visible
        $("#new-molt-indicator").removeClass("d-none");
    }
}


function updateImgPreview(imgInput) {
    var imgPreview = $(imgInput.form).find(".img-preview");
    var closeButton = $(imgInput.form).find(".close-file-btn");
    var file = imgInput.files[0];
    var reader = new FileReader();

    reader.onloadend = function() {
        // Update image preview
        $(imgPreview).parent().removeClass("d-none");
        // DEBUG: What was this for???
        // imgPreview.css("background-image", `url('${reader.result}')`);
        imgPreview.attr("src", reader.result);

        // Show remove image button
        closeButton.removeClass("d-none");
        $(imgInput).parent().addClass("d-none");
    }

    if (file) {
        reader.readAsDataURL(file);
    }
}

function removeImg(closeBtn) {
    var form = $(closeBtn.parentElement.parentElement)
    var imgPreview = form.find(".img-preview").parent();
    var imgInput = form.find(".attach-image");

    // Clear image input
    form.find('.custom-file-input').val("");

    // Re-evaluate submit button status
    updateCounter.call(form.find('textarea'));

    // Hide image preview, hide close button, and show image picker
    imgPreview.addClass("d-none");
    $(closeBtn).addClass("d-none");
    imgInput.removeClass("d-none");
}

function subMolt(form) {
    if (form['molt_content'].value || form['molt-media'].value) {
        $(form).find('button strong').text('Posting...');
        $(form).attr("disabled", "");
        return true;
    }
    alert("Molt cannot be devoid of text.");
    return false;
}

function loadingIcon(e) {
    $(e).find(".btn-icon:not(.d-none)").addClass("d-none");
    $(e).find(".loading-icon").removeClass("d-none");
    // Notification badge handling
    $(e).find(".notif-badge").addClass("d-none");
    // Profile link handling
    $(e).find(".profile-picture").find(".loading-icon").removeClass("d-none");
}

// Character counter stuff ///////////////////////////////////////////////////////////
function updateCounter() {
    var form = $(this).parents('form');
    var charLimit = 280;
    let textarea = form.find('textarea');
    let counter = form.find(".mini-character-counter");

    let currentLen = textarea.val().length;
    counter.text(charLimit - currentLen);

    // Enable/disable submit button
    let submitEnabled = moltFormHasContent(form) && currentLen <= charLimit;
    form.find("button").attr("disabled", !submitEnabled);
}

function moltFormHasContent(form) {
    let textarea = form.find('textarea');
    let imageForm = form.find("input[type=file]");

    return !(textarea.val().length == 0 && imageForm.get(0) ? imageForm.val().length == 0 : false);
}

// Scroll-back button stuff //////////////////////////////////////////////////////////
var scrollBackActive = false;
function hideScrollback() {
    let scrollBack = $(".scroll-back");
    scrollBackActive = false;
    scrollBack.removeClass("active");
}
function showScrollback() {
    let scrollBack = $(".scroll-back");
    scrollBackActive = true;
    scrollBack.addClass("active");
}
function updateScrollback(scroll) {
    // The point at which the scrollback button appears
    const magicNumber = 1000;
    let contentBody = $("#content-body");
    var scroll = contentBody.scrollTop();

    if (scroll > magicNumber && scrollBackActive == false)
        showScrollback();
    else if (scroll <= magicNumber && scrollBackActive == true)
        hideScrollback();
}
function scrollToTop() {
    let contentBody = $("#content-body");
    contentBody.get(0).scroll({top: 0, behavior: 'smooth'});
}

function toggleDropdown(el) {
    let moltDropdown = $(el).siblings('.molt-dropdown');

    // Dropdown is active
    if (moltDropdown.hasClass('show')) {
        // jQuery hide dropdown
        moltDropdown.dropdown('hide');
        // Trigger custom hide event
        moltDropdown.trigger('hide');
    }
    // Dropdown is hidden
    else {
        moltDropdown.dropdown('show');
        let popper = new Popper(el, moltDropdown, {placement: 'bottom'});

        // Close dropdown when elsewhere is clicked
        var clickHandler = function(event) {
            if (!$(event.target).closest(moltDropdown).length
                && !$(event.target).closest(el).length) {
                // jQuery hide dropdown
                moltDropdown.dropdown('hide');
                // Trigger custom hide event
                moltDropdown.trigger('hide');
            }
        }

        $(document).bind('click', clickHandler);

        // Destroy popper when done
        $(moltDropdown).one('hide', function() {
            popper.destroy();
            popper = null;
            $(document).unbind('click', clickHandler);
        })
    }
}

function replaceMolt(elem, text) {
    $(elem).parents('.mini-molt').html(
        `<div class="molt-message text-muted">${text}</div>`
    );
}

function getImageSrc(el) {
    return $(el).find('img[src], div[src]').attr('src');
}

function getImageAlt(el) {
    return $(el).find('img[src], div[src]').attr('alt');
}

function editImageDescription(src, alt) {
    const modal = $('#image_description_modal');
    modal.find('input[name=img_src]').attr('value', src);
    if (alt != undefined) {
        modal.find('input[name=img_description]').attr('value', alt);
    }
    modal.modal('show');
}

function expandImage(src, alt) {
    const modal = $('#image_modal');
    const body = modal.children('.image-modal-body')[0];
    var image = document.createElement('img');
    image.setAttribute("src", src);
    image.setAttribute("alt", alt);
    image.setAttribute('onclick', 'toggleModal("#image_modal")');
    if (body.children[0])
        body.removeChild(body.children[0]);
    body.appendChild(image);
    modal.modal('show');
    delete image;
}

function expandMoltBox() {
    $('.mini-compose-box').addClass('focused');
}
function collapseMoltBox() {
    composeBox = $('.mini-compose-box')
    if (composeBox.get(0) == undefined)
        $(document).off('click');
    else {
        if (!moltFormHasContent(composeBox.find('form')))
            composeBox.removeClass('focused');
    }
}

function attachCharacterCounters() {
    // Counter is hidden by default so if Javascript breaks or is blocked the user doesn't see it in a broken state
    $(".mini-character-counter").each(function(index, el) {
        $(el).removeClass("d-none");
    })

    // Update character count
    $(".mini-compose-textarea textarea, .mini-compose-reply-textarea textarea, .mini-molt-text-box input[type=file]").each(function(index, el) {
        // Bind change event to function
        $(el).on("input propertychange", updateCounter);
        // Run on init (in case of text being previously filled)
        updateCounter.call(el);
    })
}

function updateStylePreferences(form) {
    // Submit form to server for saving
    SubForm(form);

    // Handle changes locally
    let lightMode = $(form.light_mode).is(':checked');
    let spookyMode = $(form.spooky_mode).is(':checked');
    let dyslexicMode = $(form.dyslexic_mode).is(':checked');
    let comicsansMode = $(form.comicsans_mode).is(':checked');

    if (spookyMode) {
        $('#light-mode-css').attr('disabled', true);
        $('#halloween-mode-css').attr('disabled', lightMode);
        $('#halloween-light-mode-css').attr('disabled', !lightMode);
    } else {
        $('#light-mode-css').attr('disabled', !lightMode);
        $('#halloween-mode-css').attr('disabled', true);
        $('#halloween-light-mode-css').attr('disabled', true);
    }

    $('#comicsans-mode-css').attr('disabled', !comicsansMode);
    $('#dyslexic-mode-css').attr('disabled', !dyslexicMode);
}

function toggleModal(selector) {
    $(selector).modal('toggle');
}

function highlightKeyword(keyword, selector) {
    /* Highlights all instances of `keyword` in elements matching `selector`.
    */

    // Unescape keyword
    keyword = $("<div/>").html(keyword).text();

    $(selector).highlight(keyword, {className: 'search-highlight'});
}

function submitRemolt(elem) {
    let form = $(elem).closest('form');
    // Hide dropdown
    setTimeout(function() {
        $(document).trigger('click')

        // Swap dropdown buttons
        form.addClass('hidden');
        form.siblings('#dd-undo-remolt')
            .removeClass('hidden');
    }, 20);


    // Visually activate remolt button
    let remoltBtn = $(elem)
        .closest('.mini-molt-actions')
        .find('.mini-molt-action.remolt');
    remoltBtn.addClass('active-remolt');

    // Increment remolt count
    let remoltCounter = remoltBtn.find('.mini-molt-action-counter');
    let remoltCount = parseInt(remoltCounter.text()) + 1;
    remoltCounter.text(remoltCount);

    // Ajax submit form
    SubForm(form, url=null,
        success = function() {
            // Maybe not necessary?
            //
            // makeToast(
            //     'Remolt Submitted',
            //     'Your remolt has been posted successfully.'
            // );
        },
        error = function() {
            makeToast(
                'Failed to remolt',
                'Sorry! Try again in a few seconds.'
            );
            //
                // Swap dropdown buttons
            form.removeClass('hidden');
            form.siblings('#dd-undo-remolt')
                .addClass('hidden');

            // Visually deactivate remolt button
            remoltBtn.removeClass('active-remolt');

            // Increment remolt count
            let remoltCounter = remoltBtn.find('.mini-molt-action-counter');
            let remoltCount = parseInt(remoltCounter.text()) - 1;
            remoltCounter.text(remoltCount);
        },
    );
}

function deleteRemolt(elem) {
    let form = $(elem).closest('form');
    // Hide dropdown
    setTimeout(function() {
        $(document).trigger('click')

        // Swap dropdown buttons
        form.addClass('hidden');
        form.siblings('#dd-remolt')
            .removeClass('hidden');
    }, 20);


    // Visually activate remolt button
    let remoltBtn = $(elem)
        .closest('.mini-molt-actions')
        .find('.mini-molt-action.remolt');
    remoltBtn.removeClass('active-remolt');

    // Increment remolt count
    let remoltCounter = remoltBtn.find('.mini-molt-action-counter');
    let remoltCount = parseInt(remoltCounter.text()) - 1;
    remoltCounter.text(remoltCount);

    // Ajax submit form
    SubForm(form, url=null,
        success = function() {
            let molt = form.parents('.regular-molt');
            if (molt.hasClass('is-remolt')) {
                molt.remove()
            }

            // Maybe not necessary?
            //
            // makeToast(
            //     'Remolt deleted',
            //     'Your remolt has been deleted successfully.'
            // );
        },
        error = function() {
            makeToast(
                'Failed to delete remolt',
                'Sorry! Try again in a few seconds.'
            );
            //
                // Swap dropdown buttons
            form.removeClass('hidden');
            form.siblings('#dd-remolt')
                .addClass('hidden');

            // Visually deactivate remolt button
            remoltBtn.addClass('active-remolt');

            // Increment remolt count
            let remoltCounter = remoltBtn.find('.mini-molt-action-counter');
            let remoltCount = parseInt(remoltCounter.text()) + 1;
            remoltCounter.text(remoltCount);
        },
    );
}

function submitImageDescription(elem) {
    let form = $(elem).closest('form');
    // Hide modal
    toggleModal('#image_description_modal')


    // Ajax submit form
    SubForm(form, url=null,
        success = function() {
            makeToast(
                'Success',
                'The image\'s description was updated successfully.'
            );
        },
        error = function() {
            makeToast(
                'Failed to update image description',
                'Sorry! Try again in a few seconds.'
            );
        },
    );
}

function openActionInNewTab(elem) {
    let form = $(elem).closest('form');
    let url = form.attr('action');
    let handle = window.open(url, '_blank');
    handle.blur();
    window.focus();
}

function checkboxToggle(elem) {
    elem.value = elem.checked;
}
