/* Vanilla JS: menu mobile, pratinjau file, tampilkan/sembunyikan password, overlay loading. */
(function () {
  var toggle = document.getElementById("nav-toggle");
  var links = document.getElementById("nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Pratinjau gambar yang dipilih (hanya di browser, file belum diunggah)
  document.querySelectorAll("input[type=file][data-preview]").forEach(function (input) {
    var box = document.getElementById(input.getAttribute("data-preview"));
    input.addEventListener("change", function () {
      if (!box) return;
      box.innerHTML = "";
      var file = input.files && input.files[0];
      if (!file || !file.type.startsWith("image/")) return;
      var frame = document.createElement("div");
      frame.className = "image-frame";
      var img = document.createElement("img");
      img.alt = "Pratinjau " + file.name;
      img.src = URL.createObjectURL(file);
      frame.appendChild(img);
      box.appendChild(frame);
    });
  });

  // Tombol lihat/sembunyikan secret key
  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    var field = document.getElementById(button.getAttribute("data-toggle-password"));
    button.addEventListener("click", function () {
      if (!field) return;
      var show = field.type === "password";
      field.type = show ? "text" : "password";
      button.textContent = show ? "Sembunyikan key" : "Tampilkan key";
    });
  });

  // Overlay loading untuk proses yang memakan waktu
  document.querySelectorAll("form[data-loading]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var overlay = document.getElementById("loading");
      if (!overlay) return;
      var text = overlay.querySelector("[data-loading-text]");
      if (text) text.textContent = form.getAttribute("data-loading");
      overlay.classList.add("show");
    });
  });
})();
