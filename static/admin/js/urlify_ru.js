/* Транслитерация кириллицы для автогенерации slug в админке (prepopulated_fields).

Загружается независимо от порядка скриптов: переопределяет window.URLify,
как только он доступен (нативного urlify.js может ещё не быть в момент
выполнения этого файла, если он в DOM идёт раньше).
*/
(function () {
    "use strict";

    const TRANSLIT = {
        а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e",
        ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l", м: "m",
        н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u",
        ф: "f", х: "h", ц: "ts", ч: "ch", ш: "sh", щ: "shch",
        ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
    };

    function transliterate(s) {
        return s.replace(/[^\u0000-\u007F]/g, function (ch) {
            const low = ch.toLowerCase();
            const t = TRANSLIT[low];
            if (t === undefined) {
                return "";
            }
            return low === ch ? t : t.charAt(0).toUpperCase() + t.slice(1);
        });
    }

    let installed = false;

    function install() {
        const nativeURLify = window.URLify;
        if (installed || typeof nativeURLify !== "function") {
            return;
        }
        installed = true;
        window.URLify = function (s, num_chars, allow_unicode) {
            return nativeURLify(transliterate(s), num_chars, allow_unicode);
        };
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install);
    } else {
        install();
    }
    window.addEventListener("load", install);
})();