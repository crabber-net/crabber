const DEFAULT_IMG = '/static/img/icon.jpg';
const DEFAULT_HIDE = true;
const DEFAULT_DELAY = 5000;

const Toast = ({title, body, img, autohide, delay}) => `
<div class="toast" role="alert" aria-live="assertive" aria-atomic="true"
    data-autohide="${autohide}" data-delay="${delay}"
>
  <div class="toast-header">
    <img src="${img}" class="rounded mr-2" alt="notification icon">
    <strong class="mr-auto">${title}</strong>
    <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>
  </div>
  <div class="toast-body">
    ${body}
  </div>
</div>
`;

// Initialize toasts on page load
$(document).ready(function() {
    $('.toast').toast({});
});

function makeToast(title, body) {
    let toast = Toast({
        title: title,
        body: body,
        img: DEFAULT_IMG,
        autohide: DEFAULT_HIDE,
        delay: DEFAULT_DELAY
    });
    toast = $(toast).appendTo($('#toaster-coaster'));
    toast.toast('show');
}
