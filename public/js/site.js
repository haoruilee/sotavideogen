(function () {
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
})();
