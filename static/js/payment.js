(function () {
    'use strict';

    function getCookie(name) {
        if (!document.cookie) return null;
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(c.substring(name.length + 1));
            }
        }
        return null;
    }

    function post(url, onOk, onFail) {
        var fd = new FormData();
        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') || '',
                'Accept': 'application/json'
            },
            body: fd
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.ok) {
                onOk(data);
            } else {
                onFail(data || {});
            }
        })
        .catch(function () {
            onFail({ message: 'Сервер временно недоступен. Попробуйте ещё раз.' });
        });
    }

    function showToast(message, type) {
        if (typeof window.toast === 'function') {
            window.toast(message, type);
        } else if (message) {
            alert(message);
        }
    }

    var payButtons = document.querySelectorAll('[data-pay-url]');
    for (var i = 0; i < payButtons.length; i++) {
        payButtons[i].addEventListener('click', function () {
            var btn = this;
            var url = btn.getAttribute('data-pay-url');
            if (!url) return;
            btn.disabled = true;
            post(url, function (data) {
                var result = data.result || {};
                if (result.payment_url) {
                    window.location.href = result.payment_url;
                } else {
                    btn.disabled = false;
                    showToast(data.message || 'Не удалось создать ссылку на оплату.', 'error');
                }
            }, function (data) {
                btn.disabled = false;
                showToast(data.message || 'Не удалось создать ссылку на оплату.', 'error');
            });
        });
    }

    var checkButtons = document.querySelectorAll('[data-check-url]');
    for (var j = 0; j < checkButtons.length; j++) {
        checkButtons[j].addEventListener('click', function () {
            var btn = this;
            var url = btn.getAttribute('data-check-url');
            if (!url) return;
            btn.disabled = true;
            post(url, function (data) {
                showToast(data.message || 'Оплата подтверждена.', 'success');
                if (data.status === 'paid') {
                    setTimeout(function () { window.location.reload(); }, 1200);
                } else {
                    btn.disabled = false;
                }
            }, function (data) {
                btn.disabled = false;
                showToast(data.message || 'Заказ ещё не оплачен.', 'error');
            });
        });
    }
})();