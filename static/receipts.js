const form = document.getElementById("receipt-form");

function getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

function clearErrors() {
  document.querySelectorAll(".bubble").forEach((node) => {
    node.textContent = "";
    node.classList.remove("show");
  });
  form.querySelectorAll("input").forEach((input) => input.classList.remove("invalid"));
}

function showError(field, message) {
  const node = document.querySelector(`[data-for="${field}"]`);
  const input = form.elements[field];
  if (input && input.classList) input.classList.add("invalid");
  if (!node) return;
  node.textContent = message;
  node.classList.add("show");
}

function parseQr(raw) {
  if (!raw) return;
  const query = raw.includes("?") ? raw.split("?").pop() : raw;
  const params = new URLSearchParams(query);
  const setIfEmpty = (name, value) => {
    const input = form.elements[name];
    if (input && !input.value && value) input.value = value;
  };
  setIfEmpty("fn", params.get("fn"));
  setIfEmpty("fd", params.get("i"));
  setIfEmpty("fp", params.get("fp"));
  const sum = params.get("s");
  if (sum) setIfEmpty("amount", sum.replace(",", "."));
  const stamp = params.get("t");
  if (stamp && /^\d{8}T\d{4,6}$/.test(stamp)) {
    const iso = `${stamp.slice(0, 4)}-${stamp.slice(4, 6)}-${stamp.slice(6, 8)}T${stamp.slice(9, 11)}:${stamp.slice(11, 13)}`;
    setIfEmpty("purchased_at", iso);
  }
}

form.elements.qr.addEventListener("change", () => parseQr(form.elements.qr.value.trim()));

function clientErrors() {
  const errors = {};
  const fn = form.elements.fn.value.trim();
  const fd = form.elements.fd.value.trim();
  const fp = form.elements.fp.value.trim();
  const amount = form.elements.amount.value.trim().replace(",", ".").replace("₽", "").trim();
  form.elements.amount.value = amount;
  const when = form.elements.purchased_at.value;
  if (!/^\d{16}$/.test(fn)) errors.fn = "ФН — 16 цифр.";
  if (!/^\d{1,10}$/.test(fd)) errors.fd = "ФД — от 1 до 10 цифр.";
  if (!/^\d{10}$/.test(fp)) errors.fp = "ФП — 10 цифр.";
  if (!when) errors.purchased_at = "Укажите дату и время покупки.";
  const number = Number(amount);
  if (!amount || Number.isNaN(number) || number < 1000) errors.amount = "Минимальная сумма чека — 1 000 ₽.";
  return errors;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();
  parseQr(form.elements.qr.value.trim());
  const errors = clientErrors();
  if (Object.keys(errors).length) {
    Object.entries(errors).forEach(([field, message]) => showError(field, message));
    return;
  }
  const response = await fetch(window.location.pathname, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
      Accept: "application/json",
    },
    body: new FormData(form),
  });
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    showError("__all__", "Сервер не ответил. Попробуйте ещё раз.");
    return;
  }
  if (!response.ok || !data.ok) {
    Object.entries(data.errors || {}).forEach(([field, messages]) => showError(field, messages.join(" ")));
    return;
  }
  document.getElementById("form-card").hidden = true;
  document.getElementById("success-card").hidden = false;
});
