/**
 * script.js — Snip URL Shortener frontend
 * Uses the Fetch API to POST to /shorten and renders the result.
 * Also maintains an in-session history list.
 */

"use strict";

// ── DOM references (cached once) ─────────────────────────────────────────────
const urlInput      = document.getElementById("urlInput");
const shortenBtn    = document.getElementById("shortenBtn");
const errorBox      = document.getElementById("errorBox");
const errorText     = document.getElementById("errorText");
const resultBox     = document.getElementById("resultBox");
const shortLink     = document.getElementById("shortLink");
const shortCode     = document.getElementById("shortCode");
const createdAt     = document.getElementById("createdAt");
const alreadyBadge  = document.getElementById("alreadyExisted");
const historySection= document.getElementById("historySection");
const historyList   = document.getElementById("historyList");

// In-session history (cleared on page refresh — no localStorage needed)
const sessionHistory = [];

// ── Helper: show/hide elements ────────────────────────────────────────────────
function show(el) { el.hidden = false; }
function hide(el) { el.hidden = true; }

// ── Show error message ────────────────────────────────────────────────────────
function showError(message) {
  errorText.textContent = message;
  show(errorBox);
  hide(resultBox);
}

// ── Clear transient UI state ──────────────────────────────────────────────────
function clearState() {
  hide(errorBox);
  hide(resultBox);
}

// ── Format ISO timestamp to a readable local string ───────────────────────────
function formatDate(isoString) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString + "Z"); // treat as UTC
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

// ── Prepend an item to the session history list ───────────────────────────────
function addToHistory(code, originalUrl, shortUrl) {
  // Avoid duplicates in the same session
  if (sessionHistory.includes(code)) return;
  sessionHistory.unshift(code);

  const li = document.createElement("li");
  li.className = "history-item";
  li.innerHTML = `
    <a class="history-code" href="${shortUrl}" target="_blank" rel="noopener">${code}</a>
    <span class="history-url" title="${originalUrl}">${originalUrl}</span>
  `;
  historyList.prepend(li);
  show(historySection);
}

// ── Main: shorten a URL ───────────────────────────────────────────────────────
async function shortenUrl() {
  const rawUrl = urlInput.value.trim();

  // Client-side pre-validation (basic)
  if (!rawUrl) {
    showError("Please enter a URL before shortening.");
    urlInput.focus();
    return;
  }

  if (!rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
    showError("URL must start with http:// or https://");
    urlInput.focus();
    return;
  }

  // ── Lock the UI while the request is in-flight ──
  clearState();
  shortenBtn.disabled = true;
  shortenBtn.querySelector(".btn-text").textContent = "Shortening…";

  try {
    const response = await fetch("/shorten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: rawUrl }),
    });

    const data = await response.json();

    if (!response.ok) {
      // Server returned 4xx / 5xx with an error message
      showError(data.error || `Server error (${response.status})`);
      return;
    }

    // ── Render result ──
    shortLink.href        = data.short_url;
    shortLink.textContent = data.short_url;
    shortCode.textContent = data.code;
    createdAt.textContent = formatDate(data.created_at);

    if (data.already_existed) {
      show(alreadyBadge);
    } else {
      hide(alreadyBadge);
    }

    show(resultBox);

    // Append to session history
    addToHistory(data.code, rawUrl, data.short_url);

  } catch (err) {
    // Network failure or JSON parse error
    showError("Could not reach the server. Is the Flask app running?");
    console.error("[snip] fetch error:", err);
  } finally {
    // Unlock the UI regardless of outcome
    shortenBtn.disabled = false;
    shortenBtn.querySelector(".btn-text").textContent = "Shorten";
  }
}

// ── Copy short URL to clipboard ───────────────────────────────────────────────
async function copyToClipboard() {
  const url = shortLink.href;
  const icon = document.getElementById("copyIcon");

  try {
    await navigator.clipboard.writeText(url);
    icon.textContent = "✓";
    setTimeout(() => { icon.textContent = "⎘"; }, 1800);
  } catch {
    // Fallback for browsers that restrict clipboard access
    const temp = document.createElement("input");
    temp.value = url;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand("copy");
    document.body.removeChild(temp);
    icon.textContent = "✓";
    setTimeout(() => { icon.textContent = "⎘"; }, 1800);
  }
}

// ── Keyboard shortcut: Enter in the input field triggers shorten ──────────────
urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") shortenUrl();
});

// ── Auto-focus on load ────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  urlInput.focus();
});
