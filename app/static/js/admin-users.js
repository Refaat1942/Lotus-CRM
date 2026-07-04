(function () {
    var presets = window.LOTUS_ROLE_PRESETS || {};

    function applyRolePreset(form, role) {
        var preset = presets[role];
        if (!preset || !form) return;

        [
            "can_view_reports",
            "can_export_excel",
            "can_manage_users",
            "can_edit_functions",
        ].forEach(function (name) {
            var input = form.querySelector('input[name="' + name + '"]');
            if (input) {
                input.checked = Boolean(preset.permissions && preset.permissions[name]);
            }
        });

        form.querySelectorAll('input[name^="func_"]').forEach(function (input) {
            input.checked = false;
        });
        (preset.functions || []).forEach(function (id) {
            var input = form.querySelector('input[name="func_' + id + '"]');
            if (input) input.checked = true;
        });
    }

    document.querySelectorAll(".btn-apply-role").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var form = btn.closest("[data-user-form]");
            var roleSelect = form && form.querySelector(".user-role-select");
            if (!roleSelect) return;
            applyRolePreset(form, roleSelect.value);
        });
    });

    document.querySelectorAll(".btn-select-group").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var group = btn.closest(".perm-screen-group");
            if (!group) return;
            var inputs = group.querySelectorAll('.perm-screen-items input[type="checkbox"]');
            var allChecked = Array.prototype.every.call(inputs, function (input) {
                return input.checked;
            });
            inputs.forEach(function (input) {
                input.checked = !allChecked;
            });
        });
    });
})();
