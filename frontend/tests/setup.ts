import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

// jsdom has no native dialog implementation; Chromium E2E verifies real modal focus.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
    this.querySelector<HTMLElement>("[autofocus]")?.focus();
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
}
