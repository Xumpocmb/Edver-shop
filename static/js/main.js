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

    function setPrice(el, value) {
        if (!el) return;
        el.textContent = value + ' ';
        var icon = document.createElement('span');
        icon.className = 'nbrb-icon nbrb-icon-byn';
        el.appendChild(icon);
    }

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

    window.toast = toast;

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

    function addToCart(variantId, productName, qty) {
        var fd = new FormData();
        fd.append('variant_id', variantId);
        fd.append('quantity', qty || 1);

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

    function updateCartSummary(data) {
        // Обновляем счётчик товаров
        var itemsRow = document.querySelector('.cart-summary__row');
        if (itemsRow) {
            itemsRow.innerHTML = '<span>Товаров:</span><span>' + data.total_items + ' шт.</span>';
        }

        // Итоговая сумма
        var grandTotalEl = document.getElementById('grandTotal');
        if (grandTotalEl) {
            var price = Number(data.grand_total || 0);
            grandTotalEl.innerHTML = price.toLocaleString('ru-RU') + ' <span class="nbrb-icon nbrb-icon-byn"></span>';
        }

        // Промокод
        var promoRow = document.querySelector('.cart-summary__row--discount');
        var promoInputRow = document.querySelector('.promo-row');
        var removePromoBtn = document.querySelector('.js-remove-promo');

        if (data.has_promo) {
            // Промокод есть — показываем строку скидки, скрываем инпут
            if (promoRow) {
                promoRow.innerHTML = '<span>Промокод (' + data.promo_code + '):</span><span>-' + Number(data.promo_discount || 0).toLocaleString('ru-RU') + ' <span class="nbrb-icon nbrb-icon-byn"></span></span>';
                promoRow.style.display = '';
            }
            if (promoInputRow) promoInputRow.style.display = 'none';
            if (removePromoBtn) removePromoBtn.style.display = '';
        } else {
            // Промокода нет — скрываем строку скидки, показываем инпут
            if (promoRow) promoRow.style.display = 'none';
            if (promoInputRow) promoInputRow.style.display = 'flex';
            if (removePromoBtn) removePromoBtn.style.display = 'none';
        }
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
            updateCartSummary(data);
            // Обновляем сумму строки
            var lineTotalEl = document.querySelector('[data-item-id="' + itemId + '"] .cart-item__total');
            var lineItem = data.items.find(function(i) { return i.id == itemId; });
            if (lineTotalEl && lineItem) {
                var price = Number(lineItem.line_total);
                lineTotalEl.textContent = price.toLocaleString('ru-RU') + ' ';
                var nbrbIcon = document.createElement('span');
                nbrbIcon.className = 'nbrb-icon nbrb-icon-byn';
                lineTotalEl.appendChild(nbrbIcon);
            }
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
            updateCartSummary(data);

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
        var backdrop = $('#menu-backdrop');
        var closeBtn = $('#menu-close');
        if (!burger || !nav) return;

        var lastFocus = null;
        function openMenu() {
            lastFocus = document.activeElement;
            nav.classList.add('open');
            backdrop && backdrop.classList.add('open');
            burger.classList.add('active');
            burger.setAttribute('aria-expanded', 'true');
            if (closeBtn) closeBtn.focus();
        }
        function closeMenu() {
            if (!nav.classList.contains('open')) return;
            nav.classList.remove('open');
            backdrop && backdrop.classList.remove('open');
            burger.classList.remove('active');
            burger.setAttribute('aria-expanded', 'false');
            if (lastFocus && lastFocus.focus) lastFocus.focus();
        }
        function isOpen() {
            return nav.classList.contains('open');
        }

        burger.addEventListener('click', function () {
            isOpen() ? closeMenu() : openMenu();
        });
        closeBtn && closeBtn.addEventListener('click', closeMenu);
        backdrop && backdrop.addEventListener('click', closeMenu);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && isOpen()) closeMenu();
        });
        nav.addEventListener('click', function (e) {
            var btn = e.target.closest('.header-menu-toggle');
            if (btn) {
                e.stopPropagation();
                var targetId = btn.getAttribute('data-target');
                var target = document.getElementById(targetId);
                if (!target) return;
                var isOpenSub = target.classList.toggle('open');
                btn.classList.toggle('open', isOpenSub);
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
    function bindGalleryThumbs() {
        var thumbs = $$('#galleryThumbs .thumb');
        var mainImg = $('#mainImage');
        if (!thumbs.length || !mainImg) return;

        thumbs.forEach(function (t) {
            t.addEventListener('click', function () {
                var url = t.getAttribute('data-image');
                var alt = t.getAttribute('data-alt') || '';
                thumbs.forEach(function (x) { x.classList.remove('is-active'); });
                t.classList.add('is-active');
                if (!mainImg.parentNode) return;
                if (mainImg.getAttribute('src') === url) return;
                var next = document.createElement('img');
                next.src = url;
                next.alt = alt;
                var old = mainImg;
                old.classList.remove('is-active');
                old.id = '';
                old.parentNode.insertBefore(next, old.nextSibling);
                next.id = 'mainImage';
                requestAnimationFrame(function () { next.classList.add('is-active'); });
                setTimeout(function () {
                    if (old.parentNode) old.parentNode.removeChild(old);
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

// ====== Variant Selector (свотчи цвета) ======
    function initVariantSelector() {
        var swatches = $$('.js-variant-swatch');
        var variantsEl = $('#product-variants');
        if (!swatches.length || !variantsEl) return;

        var byId = {};
        try {
            (JSON.parse(variantsEl.textContent) || []).forEach(function (v) { byId[v.id] = v; });
        } catch (e) {}
        if (Object.keys(byId).length === 0) return;

        var thumbsWrap = $('#galleryThumbs');
        var priceEl = $('#currentPrice');
        var basePriceEl = $('#basePrice');
        var discountEl = $('#discountBadge');
        var galleryDiscount = $('#galleryBadgeDiscount');
        var stockEl = $('#stockStatus');
        var qtyInput = $('#qtyInput');
        var addBtn = $('#addToCartBtn');
        var specColor = $('#specColor');
        var specStock = $('#specStock');
        var specStatus = $('#specStatus');
        var specBasePrice = $('#specBasePrice');
        var specPrice = $('#specPrice');
        var specDisc = $('#specDiscount');

        var STATUS_LABELS = {
            'in_stock': 'В наличии',
            'out_of_stock': 'Нет в наличии',
            'preorder': 'Предзаказ',
        };

        function statusClass(status) {
            if (status === 'preorder') return 'status--warn';
            return status === 'in_stock' ? 'status--ok' : 'status--bad';
        }

        function render(v) {
            if (!v) return;
            swatches.forEach(function (s) {
                s.classList.toggle('is-current', s.getAttribute('data-variant-id') === String(v.id));
            });

            // Галерея: обновляем главное фото и пересобираем миниатюры
            var mainImgTmp = $('#mainImage');
            var gallery = $('#galleryMain');
            if (thumbsWrap && gallery && v.images.length) {
                if (mainImgTmp) {
                    var url0 = v.images[0];
                    if (mainImgTmp.getAttribute('src') !== url0) {
                        var next = document.createElement('img');
                        next.src = url0;
                        next.alt = v.name || '';
                        var oldImg = mainImgTmp;
                        oldImg.classList.remove('is-active');
                        oldImg.id = '';
                        oldImg.parentNode.insertBefore(next, oldImg.nextSibling);
                        next.id = 'mainImage';
                        requestAnimationFrame(function () { next.classList.add('is-active'); });
                        setTimeout(function () {
                            if (oldImg.parentNode) oldImg.parentNode.removeChild(oldImg);
                        }, 350);
                    }
                }

                thumbsWrap.innerHTML = '';
                v.images.forEach(function (src, i) {
                    var b = document.createElement('button');
                    b.type = 'button';
                    b.className = 'thumb' + (i === 0 ? ' is-active' : '');
                    b.setAttribute('data-image', src);
                    b.setAttribute('data-alt', v.name || '');
                    b.setAttribute('role', 'option');
                    b.setAttribute('aria-label', 'Фото ' + (i + 1));
                    var im = document.createElement('img');
                    im.src = src;
                    im.alt = '';
                    im.setAttribute('loading', 'lazy');
                    b.appendChild(im);
                    thumbsWrap.appendChild(b);
                });
                thumbsWrap.style.display = v.images.length > 1 ? '' : 'none';
                bindGalleryThumbs();
            }

            if (priceEl) setPrice(priceEl, v.sale_price);
            if (basePriceEl) {
                if (v.discount > 0) {
                    setPrice(basePriceEl, v.price);
                    basePriceEl.style.display = '';
                } else {
                    basePriceEl.style.display = 'none';
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
            if (galleryDiscount) {
                if (v.discount > 0) {
                    galleryDiscount.textContent = '-' + v.discount + '%';
                    galleryDiscount.style.display = '';
                } else {
                    galleryDiscount.style.display = 'none';
                }
            }
            if (stockEl) {
                stockEl.className = 'status ' + statusClass(v.status);
                if (v.status === 'preorder') {
                    stockEl.textContent = '● Предзаказ';
                } else if (v.stock > 0) {
                    stockEl.textContent = '● В наличии (' + v.stock + ' шт.)';
                } else {
                    stockEl.textContent = '● Нет в наличии';
                }
            }
            if (qtyInput) qtyInput.max = Math.max(v.stock, 1) || 999;
            if (addBtn) {
                addBtn.setAttribute('data-variant-id', String(v.id));
                addBtn.setAttribute('data-product-name', v.name || 'Товар');
            }

            if (specBasePrice) setPrice(specBasePrice, v.price);
            if (specPrice) setPrice(specPrice, v.sale_price);
            if (specDisc) specDisc.textContent = v.discount ? v.discount + '%' : '—';
            if (specColor) specColor.textContent = v.color;
            if (specStock) specStock.textContent = v.stock + ' шт.';
            if (specStatus) specStatus.textContent = STATUS_LABELS[v.status] || v.status || '—';
        }

        swatches.forEach(function (s) {
            s.addEventListener('click', function () {
                render(byId[s.getAttribute('data-variant-id')]);
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
                var id = addBtn.getAttribute('data-variant-id');
                var name = addBtn.getAttribute('data-product-name') || 'Товар';
                var qty = 1;
                var qInput = $('#qtyInput');
                if (qInput) qty = Math.max(1, parseInt(qInput.value, 10) || 1);
                if (!id) return;
                addToCart(id, name, qty);
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

    // ====== Header user dropdown ======
    function initUserDropdown() {
        var btn = $('#header-user-btn') || document.querySelector('.header-user-btn');
        if (!btn) return;
        var dropdown = btn.closest('.header-user-dropdown');
        if (!dropdown) return;

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            dropdown.classList.toggle('open');
            btn.setAttribute('aria-expanded', dropdown.classList.contains('open') ? 'true' : 'false');
        });

        document.addEventListener('click', function (e) {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('open');
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // ====== Phone link handler (prevent tel: on desktop) ======
    function initPhoneLink() {
        var phoneLink = document.querySelector('.header-phone-link');
        if (!phoneLink) return;

        // Check if we're on a mobile device or have a tel handler
        var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

        if (!isMobile) {
            phoneLink.addEventListener('click', function (e) {
                e.preventDefault();
                // Copy phone number to clipboard or show tooltip
                var phone = phoneLink.getAttribute('href').replace('tel:', '');
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(phone).then(function() {
                        // Show tooltip
                        phoneLink.setAttribute('title', 'Номер скопирован: ' + phone);
                        setTimeout(function() { phoneLink.removeAttribute('title'); }, 2000);
                    });
                }
            });
        }
    }

    // ====== Cookie consent ======
    var COOKIE_NAME = 'cookie_consent';

    function showCookieBanner() {
        var banner = $('#cookie-banner');
        if (!banner) return;
        banner.hidden = false;
        banner.style.display = 'block';
        requestAnimationFrame(function () { banner.classList.add('is-visible'); });
    }

    function hideCookieBanner() {
        var banner = $('#cookie-banner');
        if (!banner) return;
        banner.classList.remove('is-visible');
        setTimeout(function () {
            banner.hidden = true;
            banner.style.display = '';
        }, 300);
    }

    function setConsent(value) {
        var expires = new Date();
        expires.setFullYear(expires.getFullYear() + 1);
        document.cookie = COOKIE_NAME + '=' + value + ';expires=' + expires.toUTCString() + ';path=/;SameSite=Lax';
        hideCookieBanner();
    }

    function initCookieConsent() {
        if (!getCookie(COOKIE_NAME)) {
            showCookieBanner();
        }

        var acceptBtn = $('#cookie-accept');
        var rejectBtn = $('#cookie-reject');
        var settingsBtn = $('#cookie-settings-btn');

        if (acceptBtn) {
            acceptBtn.addEventListener('click', function () { setConsent('accepted'); });
        }
        if (rejectBtn) {
            rejectBtn.addEventListener('click', function () { setConsent('necessary'); });
        }
        if (settingsBtn) {
            settingsBtn.addEventListener('click', function (e) {
                e.preventDefault();
                showCookieBanner();
            });
        }
    }

    // ====== Инициализация ======
    document.addEventListener('DOMContentLoaded', function () {
        try { initCookieConsent(); } catch (e) { console.error('cookie consent init failed', e); }
        try { initBurger(); } catch (e) {}
        try { initSlider(); } catch (e) {}
        try { bindGalleryThumbs(); } catch (e) {}
        try { initQtyCounter(); } catch (e) {}
        try { initRatingPicker(); } catch (e) {}
        try { initFilters(); } catch (e) {}
        try { initFiltersToggle(); } catch (e) {}
        try { initVariantSelector(); } catch (e) {}
        try { initCartPage(); } catch (e) {}
        try { bindCatalogClicks(); } catch (e) {}
        try { fetchCartCount(); } catch (e) {}
        try { initAlerts(); } catch (e) {}
        try { initUserDropdown(); } catch (e) {}
        try { initPhoneLink(); } catch (e) {}
    });

})();
