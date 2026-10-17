// Small progressive enhancements. Everything works without this file.
(function () {
  "use strict";

  // --- Point rows: "+ Add point" and ✕ (activity form) ------------------------
  document.addEventListener("click", function (e) {
    var add = e.target.closest("[data-add-point]");
    if (add) {
      var rows = add.closest("fieldset").querySelector(".point-rows");
      var last = rows.lastElementChild;
      var row = last.cloneNode(true);
      row.querySelectorAll("input").forEach(function (i) { i.value = ""; });
      rows.appendChild(row);
      row.querySelector("input[type=text]").focus();
      return;
    }
    var remove = e.target.closest("[data-remove-row]");
    if (remove) {
      var row = remove.closest(".point-row");
      var list = row.parentElement;
      if (list.children.length > 1) row.remove();
      else row.querySelectorAll("input").forEach(function (i) { i.value = ""; });
    }
  });

  // --- Tag picker (D22): chips of chosen tags, type to filter, Enter to add -----
  function initTagInput(input) {
    if (input.dataset.enhanced) return;
    input.dataset.enhanced = "1";
    var options = Array.prototype.map.call(
      document.querySelectorAll("#" + input.getAttribute("list") + " option"),
      function (o) { return o.value; }
    );
    var tags = input.value.split(",").map(clean).filter(Boolean);

    var box = document.createElement("div");
    box.className = "tag-picker";
    var chips = document.createElement("span");
    chips.className = "tag-chips";
    var typer = document.createElement("input");
    typer.type = "text";
    typer.className = "tag-typer";
    typer.placeholder = input.placeholder;
    typer.setAttribute("list", input.getAttribute("list"));
    typer.setAttribute("autocomplete", "off");
    typer.setAttribute("aria-label", "Add a tag");
    box.appendChild(chips);
    box.appendChild(typer);
    input.type = "hidden";
    input.removeAttribute("list");
    input.parentNode.insertBefore(box, input.nextSibling);

    function clean(t) { return t.trim().toLowerCase().replace(/\s+/g, " "); }
    function sync() {
      input.value = tags.join(",");
      chips.innerHTML = "";
      tags.forEach(function (t, i) {
        var chip = document.createElement("span");
        chip.className = "chip is-on";
        chip.textContent = t + " ";
        var x = document.createElement("button");
        x.type = "button";
        x.className = "chip-x";
        x.textContent = "×";
        x.setAttribute("aria-label", "Remove " + t);
        x.addEventListener("click", function () { tags.splice(i, 1); sync(); typer.focus(); });
        chip.appendChild(x);
        chips.appendChild(chip);
      });
    }
    function addTyped() {
      var t = clean(typer.value.replace(/,/g, " "));
      if (t && tags.indexOf(t) === -1) tags.push(t);
      typer.value = "";
      sync();
    }
    typer.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addTyped(); }
      else if (e.key === "Backspace" && !typer.value && tags.length) { tags.pop(); sync(); }
    });
    // Picking a datalist suggestion is a "replacement" input, not typing.
    typer.addEventListener("input", function (e) {
      var picked = !e.inputType || e.inputType === "insertReplacementText";
      if (picked && options.indexOf(clean(typer.value)) !== -1) addTyped();
    });
    // Anything left half-typed still counts when you leave the box or save.
    typer.addEventListener("blur", addTyped);
    sync();
  }

  // --- Save a block's minutes as soon as it changes ----------------------------
  document.addEventListener("change", function (e) {
    if (e.target.matches("[data-autosubmit]")) e.target.form.requestSubmit();
  });

  // --- After saving, scroll back to the block you were working on --------------
  function scrollToMarked() {
    var marker = document.querySelector("[data-scroll-to]");
    if (!marker) return;
    var el = document.getElementById(marker.getAttribute("data-scroll-to"));
    marker.removeAttribute("data-scroll-to");
    if (el) el.scrollIntoView({ block: "start" });
  }
  document.addEventListener("htmx:afterSettle", function () { setTimeout(scrollToMarked, 0); });

  function init(root) {
    (root || document).querySelectorAll("[data-tag-input]").forEach(initTagInput);
  }
  document.addEventListener("DOMContentLoaded", scrollToMarked);
  document.addEventListener("DOMContentLoaded", function () { init(document); });
  document.addEventListener("htmx:load", function (e) { init(e.detail.elt); });
})();
