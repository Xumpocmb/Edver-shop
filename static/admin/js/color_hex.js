/* Пипетка для hex цвета варианта товара: нативный <input type="color"> рядом
   с текстовым полем. Работает и в инлайне вариантов, где строки добавляются
   динамически, поэтому слушатели висят на document.
*/
(function () {
    "use strict";

    const HEX = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i;

    function normalizeHex(value) {
        const match = HEX.exec((value || "").trim());
        if (!match) {
            return null;
        }
        let hex = match[1].toLowerCase();
        if (hex.length === 3) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }
        return "#" + hex;
    }

    function fieldIn(wrapper) {
        return wrapper.querySelector("input[type=text]");
    }

    function syncPickerToField(field) {
        const picker = field.parentElement.querySelector("[data-color-hex-picker]");
        const hex = normalizeHex(field.value);
        if (picker && hex) {
            picker.value = hex;
        }
    }

    function syncAll() {
        document.querySelectorAll(".color-hex input[type=text]").forEach(syncPickerToField);
    }

    document.addEventListener("input", function (event) {
        const target = event.target;
        if (!target.matches) {
            return;
        }
        if (target.matches("[data-color-hex-picker]")) {
            const field = fieldIn(target.closest(".color-hex"));
            if (field) {
                field.value = target.value;
            }
        } else if (target.matches(".color-hex input[type=text]")) {
            syncPickerToField(target);
        }
    });

    document.addEventListener("click", function (event) {
        const target = event.target;
        if (!target.matches || !target.matches("[data-color-hex-clear]")) {
            return;
        }
        const field = fieldIn(target.closest(".color-hex"));
        if (!field) {
            return;
        }
        field.value = "";
        field.focus();
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", syncAll);
    } else {
        syncAll();
    }
    window.addEventListener("load", syncAll);
})();