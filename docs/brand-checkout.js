/* brand-checkout.js — in-place checkout window for portfolio brand sites (v1, 14 Oct 2026).
 *
 * Standing rule (Mohammed, 14 Oct 2026): a buyer must never land on a Gumroad-designed
 * product or profile page. Buy buttons open the processor's CHECKOUT step (never the
 * product page) inside a window on the brand's own page.
 *
 * Markup:   <a href="https://<store>.gumroad.com/l/<permalink>?wanted=true" data-checkout>Buy</a>
 *   - href MUST carry wanted=true: Gumroad 302s that straight to gumroad.com/checkout
 *     (URL parameters kept), so even with JS off the buyer skips the product page.
 *   - PWYW products: add &price=<listed price> or Gumroad shows the product page instead.
 *   - optional data-checkout-title="Box Fourteen · VAT Prep Pilot" (window header).
 * Script:   <script src="/brand-checkout.js" defer data-brand="Box Fourteen" data-accent="#C23B2D" data-lang="en"></script>
 * Deep link: <page>?checkout=1 (or #checkout) opens the first button's window on load; ?checkout=<permalink> opens that
 *   product (data-store="<store>" on the script tag allows email-only products with no button on the page).
 * CSP:      frame-src https://*.gumroad.com https://gumroad.com
 *
 * Do NOT load gumroad.js on the same page (it would rewire the links into its own overlay,
 * whose first screen is the Gumroad product page).
 */
(function () {
  var s = document.currentScript || document.querySelector("script[src*='brand-checkout']");
  var brand = (s && s.dataset.brand) || "";
  var accent = (s && s.dataset.accent) || "#1a1814";
  var fixedLang = s && s.dataset.lang; // else follow <html lang> at click time (bilingual toggles)
  var ar, T;
  function setLang() {
    ar = /^ar/i.test(fixedLang || document.documentElement.lang || "en");
    T = ar
      ? { secure: "دفع آمن", close: "إغلاق", loading: "جارٍ فتح نافذة الدفع الآمن…", en: "نافذة الدفع باللغة الإنجليزية" }
      : { secure: "Secure checkout", close: "Close", loading: "Opening secure checkout…", en: "" };
  }
  setLang();

  function withWanted(href) {
    try {
      var u = new URL(href, location.href);
      if (!/(^|\.)gumroad\.com$/i.test(u.hostname)) return null;
      u.searchParams.set("wanted", "true");
      return u.toString();
    } catch (e) {
      return null;
    }
  }

  var wrap, frame, prevOverflow;
  function close() {
    if (!wrap) return;
    wrap.remove();
    wrap = frame = null;
    document.body.style.overflow = prevOverflow || "";
    document.removeEventListener("keydown", onKey);
  }
  function onKey(e) {
    if (e.key === "Escape") close();
  }
  function open(url, title) {
    close();
    setLang();
    prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    wrap = document.createElement("div");
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-modal", "true");
    wrap.setAttribute("aria-label", T.secure);
    wrap.style.cssText =
      "position:fixed;inset:0;z-index:2147483000;background:rgba(10,10,8,.62);display:flex;align-items:center;justify-content:center;padding:12px;";
    var panel = document.createElement("div");
    panel.dir = ar ? "rtl" : "ltr";
    panel.style.cssText =
      "background:#fff;width:100%;max-width:620px;height:min(92vh,900px);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 30px 80px -30px rgba(0,0,0,.6);font-family:inherit;";
    var head = document.createElement("div");
    head.style.cssText =
      "display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-bottom:3px solid " + accent + ";";
    var label = document.createElement("div");
    label.style.cssText = "font-size:14px;line-height:1.3;color:#1a1814;min-width:0;";
    var b = document.createElement("strong");
    b.textContent = title || brand;
    label.appendChild(b);
    var sub = document.createElement("div");
    sub.style.cssText = "font-size:12px;color:#6b665c;";
    sub.textContent = "\uD83D\uDD12 " + T.secure + (T.en ? " · " + T.en : "");
    label.appendChild(sub);
    var x = document.createElement("button");
    x.type = "button";
    x.setAttribute("aria-label", T.close);
    x.innerHTML = "&times;";
    x.style.cssText =
      "flex:none;width:36px;height:36px;border-radius:50%;border:1px solid #e0ddd5;background:#fff;color:#1a1814;font-size:22px;line-height:1;cursor:pointer;";
    x.onclick = close;
    head.appendChild(label);
    head.appendChild(x);
    var body = document.createElement("div");
    body.style.cssText = "position:relative;flex:1;background:#fafafa;";
    var load = document.createElement("div");
    load.textContent = T.loading;
    load.style.cssText = "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#6b665c;font-size:14px;";
    frame = document.createElement("iframe");
    frame.title = T.secure;
    frame.src = url;
    frame.allow = "payment *";
    frame.style.cssText = "position:absolute;inset:0;width:100%;height:100%;border:0;background:transparent;";
    frame.onload = function () {
      load.style.display = "none";
    };
    body.appendChild(load);
    body.appendChild(frame);
    panel.appendChild(head);
    panel.appendChild(body);
    wrap.appendChild(panel);
    wrap.addEventListener("click", function (e) {
      if (e.target === wrap) close();
    });
    document.addEventListener("keydown", onKey);
    document.body.appendChild(wrap);
    x.focus();
  }

  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest && e.target.closest("a[data-checkout]");
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return;
    var url = withWanted(a.getAttribute("data-checkout") || a.href);
    if (!url) return;
    e.preventDefault();
    open(url, a.getAttribute("data-checkout-title"));
  });
  // Deep link from outside the site (e.g. a Telegram bot button or an email):
  // <page>?checkout=1 opens the first checkout button's window on load; <page>?checkout=<permalink> opens the
  // button for that product, or (for email-only products with no button) the brand store's product given by
  // data-store="<store>" on the script tag. Only the brand's own store is ever opened.
  var store = s && s.dataset.store;
  try {
    var m = /[?&]checkout=([A-Za-z0-9_-]+)/.exec(location.search);
    if (m || location.hash === "#checkout") {
      var want = m ? m[1] : "1";
      var go = function () {
        var a0 = null;
        if (want !== "1") a0 = document.querySelector('a[data-checkout][href*="/l/' + want + '?"], a[data-checkout][href$="/l/' + want + '"]');
        else a0 = document.querySelector("a[data-checkout]");
        if (a0) {
          var u0 = withWanted(a0.getAttribute("data-checkout") || a0.href);
          if (u0) open(u0, a0.getAttribute("data-checkout-title"));
        } else if (want !== "1" && store && /^[a-z0-9]+$/.test(store)) {
          open("https://" + store + ".gumroad.com/l/" + want + "?wanted=true", brand);
        }
      };
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
      else go();
    }
  } catch (e) {}
  window.BrandCheckout = { open: function (href, title) { var u = withWanted(href); if (u) open(u, title); }, close: close };
})();
