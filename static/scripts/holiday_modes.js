let date = new Date();
let [day, month] = [date.getDate(), date.getMonth() + 1];
console.log(day, month);

// TODO: Inject this sometime
function halloweenReplace() {
    document.body.innerHTML = document.body.innerHTML
        .replace(/How are you feeling\?/g, 'Trick or treat?')
        .replace(/Wild West/g, 'Haunted House')
        .replace(/🌵 This here page shows every single public Molt, pardner. 🤠/g, 'Listen to the wailing of the ghosts... 👻')
        .replace(/Stats/g, 'Spooky Scary Stats')
        .replace(/Trending/g, 'Haunting')
        .replace(/server restart/g, 'jump scare');
}

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
