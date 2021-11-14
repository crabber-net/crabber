let date = new Date();
let [day, month] = [date.getDate(), date.getMonth() + 1];

// Halloween
if ([30, 31].includes(day) && month == 10) {
    if (document.getElementById('light-mode-css').disabled) {
        document.getElementById('halloween-mode-css').disabled = false;
    }
}
// Christmas
else if ([24, 25].includes(day) && month == 12) {
    document.getElementById('christmas-mode-css').disabled = false;
}
