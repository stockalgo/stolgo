/**
 * Copy text to clipboard safely with fallback for headless/restricted environments.
 */
export async function copyText(text) {
  if (typeof window === "undefined" || !text) return false;

  // Try modern navigator.clipboard
  if (navigator?.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to fallback
    }
  }

  // Fallback for headless, restricted permissions, or HTTP
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    textArea.setAttribute("readonly", "");
    document.body.appendChild(textArea);
    textArea.select();
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    return !!successful;
  } catch {
    return false;
  }
}
