window.addEventListener('DOMContentLoaded', function(){
    var submitting = false;

    var form      = document.querySelector('body > main form');
    var button    = form.querySelector('button');
    var container = form.querySelector('#email-source');

    button.disabled = false;
    container.className = container.className.replace(/\bsubmitting\b/, '');

    form.addEventListener('submit', function(e){
        if (submitting) return e.preventDefault();
        button.disabled = true;
        container.className += ' submitting';
    });

    // Store/retrieve users "delete_after" probable preference in localStorage
    if ('localStorage' in window)
        (function(select){
            default_delete_after = localStorage.getItem('default_delete_after');
            if (default_delete_after) select.value = default_delete_after;
            select.addEventListener('change', function(){
                localStorage.setItem('default_delete_after', select.value);
            })
        })(document.querySelector('select[name="delete_after"]'))
})
