(function () {
    'use strict';

    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }

    function getCookie(name) {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(c.substring(name.length + 1));
            }
        }
        return null;
    }

    var CSRF_TOKEN = getCookie('csrftoken') || '';

    // ====== Toast ======
    var toastContainer = null;
    function toast(message, type) {
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast';
            toastContainer.setAttribute('aria-live', 'polite');
            document.body.appendChild(toastContainer);
        }
        var el = document.createElement('div');
        el.className = 'toast__item' + (type ? ' toast__item--' + type : '');
        el.textContent = message;
        toastContainer.appendChild(el);
        requestAnimationFrame(function () { el.classList.add('is-show'); });
        setTimeout(function () {
            el.classList.remove('is-show');
            setTimeout(function () {
                if (el.parentNode) el.parentNode.removeChild(el);
            }, 300);
        }, 3200);
    }

    // ====== Server-side Cart ======
    var CART_BADGE = null;

    function updateCartBadge(count) {
        if (!CART_BADGE) CART_BADGE = $('#cart-badge');
        if (!CART_BADGE) return;
        var n = typeof count === 'number' ? count : 0;
        CART_BADGE.textContent = String(n);
        CART_BADGE.hidden = n <= 0;
    }

    function fetchCartCount() {
        fetch('/cart/count/', {
            headers: { 'Accept': 'application/json', 'X-CSRFToken': CSRF_TOKEN }
        })
        .then(function (r) { return r.json(); })
        .then(function (data) { updateCartBadge(data.total_items); })
        .catch(function () {});
    }

    function addToCart(productId, productName, qty, variantId) {
        var fd = new FormData();
        fd.append('product_id', productId);
        fd.append('quantity', qty || 1);
        if (variantId) fd.append('variant_id', variantId);

        fetch('/cart/add/', {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' },
            body: fd
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            updateCartBadge(data.total_items);
            toast(data.message || (productName + ' добавлен в корзину'), 'success');
        })
        .catch(function () { toast('Ошибка добавления в корзину', 'error'); });
    }

    function updateCartItem(itemId, quantity) {
        var fd = new FormData();
        fd.append('quantity', quantity);

        fetch('/cart/item/' + itemId + '/update/', {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' },
            body: fd
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            updateCartBadge(data.total_items);
            location.reload();
        })
        .catch(function () { toast('Ошибка обновления корзины', 'error'); });
    }

    function removeCartItem(itemId) {
        var fd = new FormData();

        fetch('/cart/item/' + itemId + '/remove/', {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' },
            body: fd
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            updateCartBadge(data.total_items);
            var el = document.querySelector('[data-item-id="' + itemId + '"]');
            if (el) el.remove();
            toast(data.message || 'Товар удалён', 'success');
            if (data.total_items === 0) location.reload();
        })
        .catch(function () { toast('Ошибка удаления', 'error'); });
    }

    // ====== Бургер-меню ======
    function initBurger() {
        var burger = $('#burger');
        var nav = $('#main-nav');
        if (!burger || !nav) return;
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
        nav.addEventListener('click', function (e) {
            var btn = e.target.closest('.header-menu-toggle');
            if (btn) {
                e.stopPropagation();
                var targetId = btn.getAttribute('data-target');
                var target = document.getElementById(targetId);
                if (!target) return;
                var isOpen = target.classList.toggle('open');
                btn.classList.toggle('open', isOpen);
                return;
            }
            if (e.target.closest('a')) closeMenu();
        });
    }

    // ====== Слайдер (главная) ======
    function initSlider() {
        var slider = $('#heroSlider');
        if (!slider) return;
        var slides = $$('.slide', slider);
        if (!slides.length) return;
        var dots = $$('.slider-dot', $('#heroDots') || document.body);
        var prev = $('#heroPrev');
        var next = $('#heroNext');
        var current = 0;
        var timer = null;

        function show(idx) {
            current = (idx + slides.length) % slides.length;
            slides.forEach(function (s, i) { s.classList.toggle('is-active', i === current); });
            dots.forEach(function (d, i) { d.classList.toggle('is-active', i === current); });
        }
        function start() { stop(); timer = setInterval(function () { show(current + 1); }, 6500); }
        function stop() { if (timer) { clearInterval(timer); timer = null; } }

        prev && prev.addEventListener('click', function () { show(current - 1); start(); });
        next && next.addEventListener('click', function () { show(current + 1); start(); });
        dots.forEach(function (d, i) {
            d.addEventListener('click', function () { show(i); start(); });
        });
        slider.addEventListener('mouseenter', stop);
        slider.addEventListener('mouseleave', start);
        start();
    }

    // ====== Галерея карточки товара ======
    function initGallery() {
        var thumbs = $$('#galleryThumbs .thumb');
        var mainImg = $('#mainImage');
        if (!thumbs.length || !mainImg) return;

        thumbs.forEach(function (t) {
            t.addEventListener('click', function () {
                var url = t.getAttribute('data-image');
                var alt = t.getAttribute('data-alt') || '';
                thumbs.forEach(function (x) { x.classList.remove('is-active'); });
                t.classList.add('is-active');
                if (mainImg.getAttribute('src') === url) return;
                mainImg.classList.remove('is-active');
                var next = document.createElement('img');
                next.src = url;
                next.alt = alt;
                mainImg.parentNode.insertBefore(next, mainImg.nextSibling);
                requestAnimationFrame(function () { next.classList.add('is-active'); });
                setTimeout(function () {
                    if (mainImg.parentNode) mainImg.parentNode.removeChild(mainImg);
                    next.id = 'mainImage';
                }, 350);
                mainImg = next;
            });
        });
    }

    // ====== Счётчик количества (карточка товара) ======
    function initQtyCounter() {
        var block = $('#qtyCounter');
        if (!block) return;
        var minus = $('.qty-btn--minus', block);
        var plus = $('.qty-btn--plus', block);
        var input = $('.qty-input', block);
        if (!minus || !plus || !input) return;
        var max = parseInt(input.getAttribute('max'), 10);
        function clamp(v) {
            v = Math.max(1, Math.floor(Number(v) || 1));
            if (max && max > 0) v = Math.min(max, v);
            input.value = String(v);
        }
        minus.addEventListener('click', function () { clamp(Number(input.value) - 1); });
        plus.addEventListener('click', function () { clamp(Number(input.value) + 1); });
        input.addEventListener('change', function () { clamp(input.value); });
    }

    // ====== Рейтинг picker ======
    function initRatingPicker() {
        var picker = $('#ratingPicker');
        var hidden = $('#ratingValue');
        if (!picker || !hidden) return;
        var stars = $$('.rating-picker__star', picker);
        var current = Number(picker.getAttribute('data-value')) || 0;
        function render(n) {
            stars.forEach(function (s, i) {
                var on = i < n;
                s.setAttribute('aria-pressed', on ? 'true' : 'false');
            });
        }
        render(current);
        stars.forEach(function (s) {
            var val = Number(s.getAttribute('data-value')) || 0;
            s.addEventListener('click', function (e) {
                e.preventDefault();
                current = val;
                hidden.value = String(current);
                picker.setAttribute('data-value', String(current));
                render(current);
            });
            s.addEventListener('mouseenter', function () { render(val); });
        });
        picker.addEventListener('mouseleave', function () { render(current); });
    }

    // ====== Сортировка / фильтры ======
    function initFilters() {
        var form = $('#filtersForm');
        var sort = $('#sortSelect');
        var resetBtn = $('#resetFiltersBtn');
        if (form && sort) {
            sort.setAttribute('form', 'filtersForm');
            sort.addEventListener('change', function () {
                form.submit();
            });
        }
        if (resetBtn && form) {
            resetBtn.addEventListener('click', function () {
                var inputs = $$('input, select', form);
                inputs.forEach(function (el) {
                    if (el.name === 'sort' || el.type === 'hidden') return;
                    if (el.type === 'checkbox' || el.type === 'radio') el.checked = false;
                    else el.value = '';
                });
                form.submit();
            });
        }
    }

// ====== Сворачивание фильтров (мобильные) ======
    function initFiltersToggle() {
        var toggle = $('#filtersToggle');
        var card = toggle ? toggle.closest('.filters-card') : null;
        if (!toggle || !card) return;
        toggle.addEventListener('click', function () {
            var isOpen = card.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    }

// ====== Variant Selector ======
    function initVariantSelector() {
        var container = $('#variantSelector');
        if (!container || !window.__productVariants) return;

        var options = $$('.js-variant-option', container);
        var hiddenInput = $('#selectedVariantId');
        var selectedAttrs = {};
        var allVariants = window.__productVariants;

        function getMatchingVariants() {
            return allVariants.filter(function (v) {
                for (var attr in selectedAttrs) {
                    if (selectedAttrs[attr] && v.attrs[attr] !== selectedAttrs[attr]) return false;
                }
                return true;
            });
        }

        function updateUI() {
            var matching = getMatchingVariants();

            options.forEach(function (btn) {
                var attr = btn.closest('.mod__options').getAttribute('data-attribute');
                var val = btn.getAttribute('data-value');
                var variantIds = (btn.getAttribute('data-variant-ids') || '').split(',').filter(Boolean);

                var isAvailable = matching.some(function (v) {
                    return v.attrs[attr] === val && v.stock > 0;
                });

                btn.classList.toggle('is-disabled', !isAvailable);

                if (selectedAttrs[attr] === val) {
                    btn.classList.add('is-active');
                } else {
                    btn.classList.remove('is-active');
                }
            });

            if (matching.length === 1) {
                var v = matching[0];
                hiddenInput.value = v.id;

                var priceEl = $('#currentPrice');
                var oldPriceEl = $('#oldPrice');
                var discountEl = $('#discountBadge');
                var stockEl = $('#stockStatus');
                var qtyInput = $('#qtyInput');

                if (priceEl) priceEl.textContent = v.price + ' ₽';
                if (oldPriceEl) {
                    if (v.old_price) {
                        oldPriceEl.textContent = v.old_price + ' ₽';
                        oldPriceEl.style.display = '';
                    } else {
                        oldPriceEl.style.display = 'none';
                    }
                }
                if (discountEl) {
                    if (v.discount > 0) {
                        discountEl.textContent = '-' + v.discount + '%';
                        discountEl.style.display = '';
                    } else {
                        discountEl.style.display = 'none';
                    }
                }
                if (stockEl) {
                    if (v.stock > 0) {
                        stockEl.className = 'status status--ok';
                        stockEl.textContent = '● В наличии (' + v.stock + ' шт.)';
                    } else {
                        stockEl.className = 'status status--bad';
                        stockEl.textContent = '● Нет в наличии';
                    }
                }
                if (qtyInput) {
                    qtyInput.max = v.stock || 999;
                }
            }
        }

        options.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var attr = btn.closest('.mod__options').getAttribute('data-attribute');
                var val = btn.getAttribute('data-value');

                if (selectedAttrs[attr] === val) {
                    delete selectedAttrs[attr];
                } else {
                    selectedAttrs[attr] = val;
                }
                updateUI();
            });
        });
    }

    // ====== Cart page: quantity controls ======
    function initCartPage() {
        $$('.js-cart-qty-minus').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var itemId = btn.getAttribute('data-item-id');
                var input = document.querySelector('.js-cart-qty-input[data-item-id="' + itemId + '"]');
                if (!input) return;
                var val = Math.max(1, parseInt(input.value, 10) - 1);
                input.value = val;
                updateCartItem(itemId, val);
            });
        });

        $$('.js-cart-qty-plus').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var itemId = btn.getAttribute('data-item-id');
                var input = document.querySelector('.js-cart-qty-input[data-item-id="' + itemId + '"]');
                if (!input) return;
                var max = parseInt(input.getAttribute('max'), 10) || 999;
                var val = Math.min(max, parseInt(input.value, 10) + 1);
                input.value = val;
                updateCartItem(itemId, val);
            });
        });

        $$('.js-cart-qty-input').forEach(function (input) {
            input.addEventListener('change', function () {
                var itemId = input.getAttribute('data-item-id');
                var val = Math.max(1, parseInt(input.value, 10) || 1);
                input.value = val;
                updateCartItem(itemId, val);
            });
        });

        $$('.js-cart-remove').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var itemId = btn.getAttribute('data-item-id');
                removeCartItem(itemId);
            });
        });
    }

    // ====== Делегат: корзина по data-* ======
    function bindCatalogClicks() {
        document.addEventListener('click', function (e) {
            var target = e.target;
            if (!target) return;

            var addBtn = target.closest('.js-add-to-cart');
            if (addBtn) {
                e.preventDefault();
                var id = addBtn.getAttribute('data-product-id');
                var name = addBtn.getAttribute('data-product-name') || 'Товар';
                var qty = 1;
                var qInput = $('#qtyInput');
                if (qInput) qty = Math.max(1, parseInt(qInput.value, 10) || 1);
                var variantId = null;
                var variantInput = $('#selectedVariantId');
                if (variantInput && variantInput.value) variantId = variantInput.value;
                addToCart(id, name, qty, variantId);
                return;
            }
        });
    }

    // ====== Автоскрытие сообщений ======
    function initAlerts() {
        $$('.alert').forEach(function (el) {
            setTimeout(function () {
                el.style.transition = 'opacity .4s';
                el.style.opacity = '0';
                setTimeout(function () { el.remove(); }, 400);
            }, 5000);
        });
    }

    // ====== Инициализация ======
    document.addEventListener('DOMContentLoaded', function () {
        initBurger();
        initSlider();
        initGallery();
        initQtyCounter();
        initRatingPicker();
        initFilters();
        initFiltersToggle();
        initVariantSelector();
        initCartPage();
        bindCatalogClicks();
        fetchCartCount();
        initAlerts();
    });

})();
