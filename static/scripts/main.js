// AJAX Form Submit
function SubForm(form, url=null) {
    if (url == null) {
        url = document.location.pathname;
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
    $.ajax({
        url: "/ajax_request/" + request_type,
        type: 'get',
        data: data,
        success: function (response) {
            callback(response);
        },
        error: error_callback
    });
}

function toggleLike(e) {
    let empty_heart = $(e).children(".jam")[0];
    let filled_heart = $(e).children(".jam")[1];
    let counter = $(e).children("span")[0]

    // was liked, needs to be unliked
    if (empty_heart.classList.contains("d-none")) {
        $(empty_heart).removeClass("d-none");
        $(filled_heart).addClass("d-none");
        $(counter).removeClass("text-primary");
        counter.textContent = parseInt(counter.textContent) - 1
    }
    // was unliked, needs to be liked
    else {
        $(filled_heart).removeClass("d-none");
        $(empty_heart).addClass("d-none");
        $(counter).addClass("text-primary");
        counter.textContent = parseInt(counter.textContent) + 1
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
    $(e).find(".btn-icon").toggleClass("d-none");
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