document.addEventListener('DOMContentLoaded', function() {
    var navbar = document.querySelector('.navbar-container');
    var showAfter = 90;

    // Initially hide the navbar by adding the 'hide' class
    navbar.classList.add('hide');

    window.addEventListener('scroll', function() {
        var scrollPosition = window.scrollY || document.documentElement.scrollTop;

        if (scrollPosition > showAfter) {
            navbar.classList.add('show');
        } else {
            navbar.classList.remove('show');
        }
    });
});