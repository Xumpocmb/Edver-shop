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
            // disabled не спасает от синхронных повторных кликов и вызовов
            // .click() — держим собственный флаг занятости.
            if (btn.hasAttribute('data-busy')) return;
            lock(btn);
            requestInvoice(btn, url, 0);
        });
    }

    var checkButtons = document.querySelectorAll('[data-check-url]');
    for (var j = 0; j < checkButtons.length; j++) {
        checkButtons[j].addEventListener('click', function () {
            var btn = this;
            var url = btn.getAttribute('data-check-url');
            if (!url) return;
            if (btn.hasAttribute('data-busy')) return;
            lock(btn);
            post(url, function (data) {
                showToast(data.message || 'Оплата подтверждена.', 'success');
                if (data.status === 'paid') {
                    setTimeout(function () { window.location.reload(); }, 1200);
                } else {
                    unlock(btn);
                }
            }, function (data) {
                unlock(btn);
                showToast(data.message || 'Заказ ещё не оплачен.', 'error');
            });
        });
    }

    function lock(btn) {
        var pending = btn.getAttribute('data-pending-label');
        btn.setAttribute('data-idle-label', btn.textContent.trim());
        btn.setAttribute('data-busy', '');
        btn.setAttribute('aria-busy', 'true');
        btn.disabled = true;
        if (pending) btn.textContent = pending;
    }

    function unlock(btn) {
        var idle = btn.getAttribute('data-idle-label');
        btn.removeAttribute('data-busy');
        btn.removeAttribute('aria-busy');
        btn.disabled = false;
        if (idle !== null) btn.textContent = idle;
    }

    var PAY_RETRY_DELAYS = [1500, 3000, 6000];

    function requestInvoice(btn, url, attempt) {
        post(url, function (data) {
            var result = data.result || {};
            if (result.payment_url) {
                window.location.href = result.payment_url;
                return;
            }
            // Счёт выставляет параллельный запрос — ждём и берём его ссылку.
            if (result.in_progress && attempt < PAY_RETRY_DELAYS.length) {
                setTimeout(function () {
                    requestInvoice(btn, url, attempt + 1);
                }, PAY_RETRY_DELAYS[attempt]);
                return;
            }
            unlock(btn);
            showToast(result.message || data.message || 'Не удалось создать ссылку на оплату.', 'error');
        }, function (data) {
            unlock(btn);
            showToast(data.message || 'Не удалось создать ссылку на оплату.', 'error');
        });
    }
})();
