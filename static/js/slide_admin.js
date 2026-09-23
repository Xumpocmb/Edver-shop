(function () {
    'use strict';

    var targetRow = document.querySelector('.form-row.field-link_target');
    if (!targetRow) return;

    var select = document.getElementById('id_link_target');
    if (!select) return;

    var rows = {
        category: document.querySelector('.form-row.field-category'),
        product: document.querySelector('.form-row.field-product'),
        page: document.querySelector('.form-row.field-page'),
        href: document.querySelector('.form-row.field-href')
    };

    function sync() {
        var value = select.value;
        Object.keys(rows).forEach(function (key) {
            var row = rows[key];
            if (!row) return;
            row.style.display = (value === key) ? '' : 'none';
        });
    }

    select.addEventListener('change', sync);
    sync();
})();