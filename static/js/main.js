document.addEventListener('DOMContentLoaded', function () {
    var burger = document.getElementById('burger');
    var nav = document.getElementById('main-nav');

    if (!burger || !nav) {
        return;
    }

    function closeMenu() {
        nav.classList.remove('open');
        burger.classList.remove('active');
        burger.setAttribute('aria-expanded', 'false');
    }

    burger.addEventListener('click', function () {
        var isOpen = nav.classList.toggle('open');
        burger.classList.toggle('active', isOpen);
        burger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    nav.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', closeMenu);
    });
});