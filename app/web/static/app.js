(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  // ---------- Toast ----------
  const toastEl = $("#toast");
  let toastTimer;
  function toast(message, isError = false) {
    toastEl.textContent = message;
    toastEl.classList.toggle("is-error", isError);
    toastEl.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 2600);
  }

  // Mensaje que sobrevive a una redirección (ej: "Entry publicada").
  try {
    const flash = sessionStorage.getItem("flash");
    if (flash) { sessionStorage.removeItem("flash"); setTimeout(() => toast(flash), 150); }
  } catch (e) {}
  function redirectWithFlash(url, message) {
    try { sessionStorage.setItem("flash", message); } catch (e) {}
    window.location.href = url;
  }

  // ---------- Tema claro / oscuro ----------
  $("#theme-toggle")?.addEventListener("click", () => {
    const root = document.documentElement;
    const isDark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = isDark ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
  });

  // ---------- "/" enfoca el buscador ----------
  const search = $("#search");
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && search && !/input|textarea|select/i.test(document.activeElement.tagName)) {
      e.preventDefault();
      search.focus();
      search.select();
    }
  });

  // ---------- Flechas para cambiar de mes en el calendario ----------
  document.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || /input|textarea|select/i.test(document.activeElement.tagName)) return;
    const link = $(`[data-hotkey="${e.key}"]`);
    if (link) window.location.href = link.href;
  });

  // ---------- Resaltado de código + copiar ----------
  if (window.hljs) {
    $$(".code pre code").forEach((el) => {
      const lang = [...el.classList].find((c) => c.startsWith("language-"))?.slice(9);
      if (lang && !hljs.getLanguage(lang)) el.className = ""; // lenguaje desconocido -> autodetectar
      hljs.highlightElement(el);
    });
  }
  $$("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const code = btn.closest(".code").querySelector("code").innerText;
      try {
        await navigator.clipboard.writeText(code);
        btn.textContent = "¡Copiado!";
      } catch (e) {
        btn.textContent = "No se pudo copiar";
      }
      setTimeout(() => (btn.textContent = "Copiar"), 1600);
    });
  });

  // ---------- Borrar ----------
  $$("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("¿Borrar esta entry? No se puede deshacer.")) return;
      btn.disabled = true;
      const res = await fetch(`/api/v1/entries/${encodeURIComponent(btn.dataset.delete)}`, { method: "DELETE" });
      if (res.ok) redirectWithFlash("/", "Entry borrada");
      else { btn.disabled = false; toast("No se pudo borrar", true); }
    });
  });

  // ---------- Formulario ----------
  const form = $("#entry-form");
  if (!form) return;

  // Input de tags con chips
  const tagBox = $("#tag-input");
  const tagText = $("#tags-input");
  const tagHidden = $("#tags-hidden");
  let tags = tagHidden.value ? tagHidden.value.split(",").filter(Boolean) : [];

  function renderTags() {
    $$(".tag-chip", tagBox).forEach((el) => el.remove());
    tags.forEach((name, i) => {
      const chip = document.createElement("span");
      chip.className = "tag-chip";
      chip.textContent = name;
      const x = document.createElement("button");
      x.type = "button";
      x.setAttribute("aria-label", `Quitar ${name}`);
      x.textContent = "×";
      x.addEventListener("click", () => { tags.splice(i, 1); renderTags(); });
      chip.append(x);
      tagBox.insertBefore(chip, tagText);
    });
    tagHidden.value = tags.join(",");
  }
  function addTag(raw) {
    raw.split(",").map((t) => t.trim().toLowerCase().replace(/^#/, "")).filter(Boolean).forEach((t) => {
      if (!tags.includes(t)) tags.push(t);
    });
    tagText.value = "";
    renderTags();
  }
  tagText.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === ",") && tagText.value.trim()) {
      e.preventDefault();
      addTag(tagText.value);
    } else if (e.key === "Enter") {
      e.preventDefault();
    } else if (e.key === "Backspace" && !tagText.value && tags.length) {
      tags.pop();
      renderTags();
    }
  });
  tagText.addEventListener("blur", () => tagText.value.trim() && addTag(tagText.value));
  tagText.addEventListener("input", () => {
    // Elegir una opción del datalist la agrega directo.
    if ([...$("#tags-list").options].some((o) => o.value === tagText.value)) addTag(tagText.value);
  });
  tagBox.addEventListener("click", (e) => e.target === tagBox && tagText.focus());
  renderTags();

  // Ctrl/Cmd + Enter publica
  form.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) form.requestSubmit();
  });

  function clearErrors() {
    $$(".field.has-error", form).forEach((f) => f.classList.remove("has-error"));
    $$("[data-error-for]", form).forEach((p) => (p.textContent = ""));
  }
  function showError(field, message) {
    const p = $(`[data-error-for="${field}"]`, form);
    if (!p) return false;
    p.textContent = message;
    p.closest(".field").classList.add("has-error");
    return true;
  }
  function humanize(err) {
    const msg = err.msg.replace(/^Value error, /, "");
    const map = {
      string_too_short: `Muy corto (mínimo ${err.ctx?.min_length} caracteres)`,
      string_too_long: `Muy largo (máximo ${err.ctx?.max_length} caracteres)`,
      url_parsing: "No parece una URL válida (tiene que empezar con http:// o https://)",
      url_scheme: "La URL tiene que empezar con http:// o https://",
      missing: "Este campo es obligatorio",
    };
    return map[err.type] || msg;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (tagText.value.trim()) addTag(tagText.value);
    clearErrors();

    const data = Object.fromEntries(new FormData(form));
    const payload = {
      title: data.title,
      content: data.content,
      code_snippet: data.code_snippet || null,
      language: data.language || null,
      difficulty: data.difficulty,
      reference_url: data.reference_url || null,
      learned_on: data.learned_on || null,
      tags,
    };

    const submit = $('button[type="submit"]', form);
    submit.disabled = true;
    try {
      const res = await fetch(form.dataset.action, {
        method: form.dataset.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok) {
        redirectWithFlash(`/e/${body.slug}`, form.dataset.method === "POST" ? "¡Entry publicada!" : "Cambios guardados");
        return;
      }
      if (res.status === 422 && Array.isArray(body.detail)) {
        let firstField = null;
        body.detail.forEach((err) => {
          const field = err.loc?.[1];
          if (showError(field, humanize(err)) && !firstField) firstField = field;
        });
        if (firstField) (form.elements[firstField] || tagText)?.focus?.();
        toast("Revisá los campos marcados", true);
      } else {
        toast(body.detail || "Algo salió mal", true);
      }
    } catch (err) {
      toast("No se pudo conectar con el servidor", true);
    }
    submit.disabled = false;
  });
})();
