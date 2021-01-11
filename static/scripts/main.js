// AJAX Form Submit
function SubForm(form, url=null) {
    if (url == null) {
        url = document.location.pathname;
        if (!url.endsWith('/'))
            url += '/'
    }
    $.ajax({
        url: url,
        type: 'post',
        data: $(form).serialize(),
        error: function () {
            console.warn("Failed to submit form to server;");
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
        url: "/ajax_request/" + request_type,
        type: 'get',
        data: request_data,
        success: function (response) {
            callback(response);
        },
        error: error_callback
    });
}

function toggleLike(e) {
    let empty_heart = $(e).children(".jam")[0];
    let filled_heart = $(e).children(".jam")[1];
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
    } else {
        e.form.user_action.value = "unfollow";
        $(e).find('strong').text('Unfollow');
    }
}

function clearModal() {
    // Clear text
    $("#compose_modal textarea").val("")
    // Hide modal
    $("#compose_modal").modal("hide")
}

function prepareReply(molt_id, author_username, author_name) {
    // Update "replying to" link
    $("#reply-to").text(author_name)
    $("#reply-to").attr("href", "/user/" + author_username)
    // Update form reply-to ID
    $("#reply-molt-id").val(molt_id)
}

function prepareEdit(molt_id) {
    // Update form edit-molt content
    $("#edit-content").val($("#molt-content-" + molt_id).attr("data-content"))
    // Update form edit-molt ID
    $("#edit-molt-id").val(molt_id)
    // Update character counter
    updateCounter.call($('#edit_molt_modal textarea'));
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
        imgPreview.css("background-image", `url('${reader.result}')`);
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
    var imgInput = form.find(".custom-file");

    // Clear image input
    form.find('.custom-file-input').val("");

    // Hide image preview, hide close button, and show image picker
    imgPreview.addClass("d-none");
    $(closeBtn).addClass("d-none");
    imgInput.removeClass("d-none");
}

function subMolt(form) {
    if (form['molt_content'].value) {
        $(form).find('button strong').text('Uploading...');
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
    var charLimit = 240; 
    let textarea = $(this);
    let counter = textarea.parents("form").find(".mini-character-counter");
    counter.text(charLimit - textarea.val().length);

    // Enable/disable submit button
    textarea.parents("form").find("button").attr("disabled", textarea.val().length == 0);
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

function toggleDropdown(dropdownID) {
    $(`#${dropdownID}`).dropdown('toggle');
}

function replaceMolt(elem, text) {
    $(elem).parents('.mini-molt').html(
        `<div class="molt-message text-muted">${text}</div>`
    );
}
