(function () {
    var presets = window.LOTUS_ROLE_PRESETS || {};

    function applyRolePreset(form, role) {
        var preset = presets[role];
        if (!preset || !form) return;

        var permFields = [
            "can_view_reports",
            "can_export_excel",
            "can_manage_users",
            "can_edit_functions",
        ];
        permFields.forEach(function (name) {
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
})();
