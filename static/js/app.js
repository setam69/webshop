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

  // --- هشدار پرداخت بیشتر از مانده طلب نیرو ---
  document.querySelectorAll("form.payment-form[data-balance]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      var balance = parseInt(form.getAttribute("data-balance") || "0", 10);
      var amountInp = form.querySelector("input[name=amount]");
      var confirmInp = form.querySelector("input[name=confirm_overpay]");
      var amount = parseInt((amountInp && amountInp.value || "").replace(/[^0-9]/g, "") || "0", 10);
      if (amount > balance) {
        var ok = window.confirm(
          "مبلغ پرداخت بیشتر از مانده طلب نیرو است (" + balance.toLocaleString() +
          " تومان). آیا مطمئن هستید؟"
        );
        if (!ok) { e.preventDefault(); return; }
        if (confirmInp) confirmInp.value = "1";
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

  // --- محاسبه زنده سهم نیروها در فرم پروژه (حالت درصد یا مبلغ ثابت) ---
  var laborInput = document.getElementById("labor_amount");
  var calcRoot = document.getElementById("worker-rows");
  if (laborInput && calcRoot) {
    function num(s) { return parseInt(digits(s) || "0", 10); }

    function applyRowMode(row) {
      var modeSel = row.querySelector("select.worker-mode");
      var percentWrap = row.querySelector(".percent-wrap");
      var amountWrap = row.querySelector(".amount-wrap");
      if (!modeSel) return;
      var isFixed = modeSel.value === "fixed";
      if (percentWrap) percentWrap.style.display = isFixed ? "none" : "";
      if (amountWrap) amountWrap.style.display = isFixed ? "" : "none";
    }

    calcRoot.querySelectorAll("select.worker-mode").forEach(function (sel) {
      applyRowMode(sel.closest(".worker-row"));
      sel.addEventListener("change", function () {
        applyRowMode(sel.closest(".worker-row"));
        recalc();
      });
    });

    function recalc() {
      var labor = num(laborInput.value);
      var totalShare = 0;
      calcRoot.querySelectorAll(".worker-row").forEach(function (row) {
        var check = row.querySelector("input[type=checkbox]");
        var modeSel = row.querySelector("select.worker-mode");
        var percentInp = row.querySelector("input.percent");
        var amountInp = row.querySelector("input.worker-amount");
        var shareCell = row.querySelector(".share-cell");
        var active = check && check.checked;
        var isFixed = modeSel && modeSel.value === "fixed";
        var share = 0;
        if (active) {
          if (isFixed) {
            share = num(amountInp ? amountInp.value : "0");
          } else {
            var p = parseFloat((percentInp && percentInp.value || "0").replace(/[^\d.]/g, "")) || 0;
            share = Math.round(labor * p / 100);
          }
        }
        if (active) totalShare += share;
        if (shareCell) shareCell.textContent = active ? group(String(share)) : "—";
        row.style.opacity = active ? "1" : ".55";
      });
      var shop = labor - totalShare;
      setText("sum-share", group(String(totalShare)));
      setText("shop-share", group(String(shop)));

      var warn = document.getElementById("percent-warning");
      if (warn) {
        if (totalShare > labor) {
          warn.style.display = "block";
          warn.textContent = "⚠ مجموع سهم نیروها (" + group(String(totalShare)) +
            ") از مبلغ کل پروژه (" + group(String(labor)) + ") بیشتر است؛ امکان ثبت وجود ندارد.";
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
