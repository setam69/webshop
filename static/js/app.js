// اسکریپت‌های سبک سمت کاربر — منوی موبایل، جداکننده هزارگان و محاسبه زنده سهم‌ها

(function () {
  "use strict";

  // --- منوی کناری موبایل ---
  var toggle = document.querySelector(".menu-toggle");
  var sidebar = document.querySelector(".sidebar");
  var backdrop = document.querySelector(".backdrop");
  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      if (backdrop) backdrop.classList.toggle("open");
    });
    if (backdrop) backdrop.addEventListener("click", function () {
      sidebar.classList.remove("open");
      backdrop.classList.remove("open");
    });
  }

  // --- تأیید پیش از حذف ---
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });

  // --- جداکننده هزارگان زنده برای ورودی مبلغ ---
  function digits(s) { return (s || "").replace(/[^0-9]/g, ""); }
  function group(s) { return s.replace(/\B(?=(\d{3})+(?!\d))/g, ","); }

  document.querySelectorAll("input.money").forEach(function (inp) {
    function fmt() {
      var d = digits(inp.value);
      inp.value = d ? group(d) : "";
    }
    inp.addEventListener("input", fmt);
    fmt();
  });

  // --- محاسبه زنده سهم نیروها در فرم پروژه ---
  var laborInput = document.getElementById("labor_amount");
  var calcRoot = document.getElementById("worker-rows");
  if (laborInput && calcRoot) {
    function num(s) { return parseInt(digits(s) || "0", 10); }

    function recalc() {
      var labor = num(laborInput.value);
      var totalPercent = 0, totalShare = 0;
      calcRoot.querySelectorAll(".worker-row").forEach(function (row) {
        var check = row.querySelector("input[type=checkbox]");
        var percentInp = row.querySelector("input.percent");
        var shareCell = row.querySelector(".share-cell");
        var active = check && check.checked;
        var p = parseFloat((percentInp.value || "0").replace(/[^\d.]/g, "")) || 0;
        var share = active ? Math.round(labor * p / 100) : 0;
        if (active) { totalPercent += p; totalShare += share; }
        if (shareCell) shareCell.textContent = active ? group(String(share)) : "—";
        row.style.opacity = active ? "1" : ".55";
      });
      var shop = labor - totalShare;
      setText("sum-percent", totalPercent);
      setText("sum-share", group(String(totalShare)));
      setText("shop-share", group(String(shop)));

      var warn = document.getElementById("percent-warning");
      if (warn) {
        if (totalPercent > 100) {
          warn.style.display = "block";
          warn.textContent = "⚠ مجموع درصدها (" + totalPercent + "٪) بیشتر از ۱۰۰٪ است؛ امکان ثبت وجود ندارد.";
        } else {
          warn.style.display = "none";
        }
      }
    }
    function setText(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }

    laborInput.addEventListener("input", recalc);
    calcRoot.addEventListener("input", recalc);
    calcRoot.addEventListener("change", recalc);
    recalc();
  }
})();
