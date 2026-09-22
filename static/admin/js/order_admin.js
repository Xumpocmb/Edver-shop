(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        var branchSelect = document.getElementById('id_branch_select');
        var branchIdInput = document.getElementById('id_evropochta_branch_id');
        var branchNameInput = document.getElementById('id_evropochta_branch_name');
        var deliveryTypeSelect = document.getElementById('id_delivery_type');

        if (!branchSelect) return;

        function toggleBranchField() {
            if (deliveryTypeSelect && deliveryTypeSelect.value === 'evropochta') {
                branchSelect.closest('.form-row').style.display = '';
            } else {
                branchSelect.closest('.form-row').style.display = 'none';
            }
        }

        branchSelect.addEventListener('change', function () {
            var selected = branchSelect.options[branchSelect.selectedIndex];
            if (branchIdInput) branchIdInput.value = branchSelect.value;
            if (branchNameInput && selected && selected.value) {
                branchNameInput.value = selected.text;
            } else if (branchNameInput) {
                branchNameInput.value = '';
            }
        });

        if (deliveryTypeSelect) {
            deliveryTypeSelect.addEventListener('change', toggleBranchField);
            toggleBranchField();
        }
    });
})();
