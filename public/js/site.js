(function () {
  var DEMO_QUEUE_KEY = "svg_demo_queue";

  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector("[data-nav]");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  var localeSelect = document.querySelector("[data-locale-switcher]");
  if (localeSelect) {
    localeSelect.addEventListener("change", function () {
      var v = localeSelect.value;
      if (v) window.location.href = v;
    });
  }

  function readQueue() {
    try {
      var raw = window.localStorage.getItem(DEMO_QUEUE_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }

  function writeQueue(queue) {
    window.localStorage.setItem(DEMO_QUEUE_KEY, JSON.stringify(queue));
  }

  function collectFormData(form) {
    var values = [];
    var fields = form.querySelectorAll("textarea, select, input");
    fields.forEach(function (field) {
      var tag = field.tagName.toLowerCase();
      var type = (field.getAttribute("type") || "").toLowerCase();
      var value = "";
      if (type === "file") {
        var files = field.files;
        value = files && files.length ? files[0].name : "";
      } else if (tag === "textarea" || tag === "select" || type) {
        value = (field.value || "").trim();
      }
      if (!value) return;
      var labelNode = field.closest(".field");
      var label = "";
      if (labelNode) {
        var labelEl = labelNode.querySelector(".field-label");
        label = labelEl ? labelEl.textContent.trim() : "";
      }
      values.push({ label: label || field.name || "参数", value: value });
    });
    return values;
  }

  function hasRequiredInput(form) {
    var requiredFields = form.querySelectorAll("[data-required-input]");
    if (!requiredFields.length) return true;
    return Array.prototype.some.call(requiredFields, function (field) {
      var type = (field.getAttribute("type") || "").toLowerCase();
      if (type === "file") {
        return Boolean(field.files && field.files.length);
      }
      return Boolean((field.value || "").trim());
    });
  }

  function mountStudioForms() {
    var forms = document.querySelectorAll("[data-studio-form]");
    forms.forEach(function (form) {
      var submitBtn = form.querySelector("[data-queue-submit]");
      var note = form.querySelector("[data-form-note]");
      if (!submitBtn || !note) return;

      var defaultNote = note.textContent.trim();
      var setNote = function (msg, tone) {
        note.textContent = msg;
        note.classList.remove("is-error", "is-success");
        if (tone) note.classList.add(tone);
      };

      submitBtn.addEventListener("click", function () {
        if (!hasRequiredInput(form)) {
          setNote("请先填写提示词或选择待处理文件后再加入队列。", "is-error");
          return;
        }

        var queue = readQueue();
        var taskId = "demo_" + Math.random().toString(36).slice(2, 8);
        var payload = {
          id: taskId,
          mode: form.dataset.mode || "video",
          title: form.dataset.title || document.title,
          createdAt: new Date().toISOString(),
          path: window.location.pathname,
          fields: collectFormData(form),
        };
        queue.unshift(payload);
        writeQueue(queue.slice(0, 20));
        setNote(
          "已加入本地队列，任务 ID：" +
            taskId +
            "（共 " +
            Math.min(queue.length, 20) +
            " 条）。",
          "is-success"
        );
      });

      form.addEventListener("reset", function () {
        window.setTimeout(function () {
          setNote(defaultNote);
        }, 0);
      });
    });
  }

  mountStudioForms();
})();
