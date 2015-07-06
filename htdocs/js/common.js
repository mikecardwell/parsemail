/*
    Scroll-to-top icon appears at the bottom right of the page, below a certain scroll threshold
*/
window.addEventListener('DOMContentLoaded', function(){
    var threshold = 300;

    var el = document.createElement('span');
    el.id        = 'totop';
    el.title     = 'Take me back to the top of the page';
    el.className = 'hide';

    el.addEventListener('click', function(){
        window.scroll(0, 0);
        window.location.hash = 'top';
    });

    var shown = false,
        toggler = function (){
            var ypos = window.pageYOffset || document.body.scrollTop || document.documentElement.scrollTop || 0;
            var show = ypos > threshold;
            if (show !== shown) {
                el.className = show ? 'show' : 'hide';
                shown = show;
            }
        };

    toggler();
    document.body.appendChild(el);
    window.addEventListener('scroll', toggler)
})

window.addEventListener('beforeunload', function(){
    document.body.className += ' busy'
})

/*
    In order to make wrapping nice, in various parts of the code I replace breaking
    hyphen characters with non-breaking hyphen characters. I also add zero-width
    breaking characters in long strings of characters which don't contain breaking
    spaces so wouldn't naturally wrap. Unfortunately, when somebody copies text from
    the page they get these unusual characters. This bit of JavaScript fixes that.
*/
document.addEventListener('copy', function(e){
    var selection = window.getSelection();

    var orig_text = new_text = selection.toString();
    new_text = new_text.split('\u200b').join('');  // Remove zero-width word breaking characters
    new_text = new_text.split('\u2011').join('-'); // Replace non-breaking hyphens with normal hyphens

    if (new_text === orig_text) return; // No change

    // Remember what text is selected so we can re-select it afterwards
    var range = selection.getRangeAt(0);

    // Stick the dummy text in a hidden div
    var div  = document.createElement('div');
    div.style.position = 'absolute';
    div.style.left     = '-99999px';
    div.innerHTML      = new_text;

    // Select the text in the dummy div
    document.body.appendChild(div);
    selection.selectAllChildren(div);

    // Sleep for a moment so the copy function can complete and the dummy
    // text is copied
    window.setTimeout(function(){
        // Remove the dummy text container
        document.body.removeChild(div);

        // Reselect originally selected text
        selection.addRange(range);
    }, 1);

});


/*
    Convert "^/path/#top$" or "^/path/#$" to "/path/". I hate having unnecessary
    hash tags in the URL
*/
(function(){

    var process = function () {
        var hash = window.location.hash.replace('#', '');
        if (hash === '' || hash === 'top')
            window.history.replaceState({}, document.title, document.location.pathname);
    };
    process();
    window.addEventListener('hashchange', process, false);
    
})();

/* Self Promotion */
console.log('Hi, my name is Mike and I made this website. I\'m currently seeking employment. Please see my hireme page - https://hireme.grepular.com');

