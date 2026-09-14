// Reusable copy-to-clipboard behavior for any page.
//
// Wire up a button by pointing it at the element whose text should be
// copied:
//
//   <code id="my-code">ABC123</code>
//   <button data-copy-target="my-code" data-copied-label="Kopiert!">Kopieren</button>
//
// The button's own text is restored automatically after a short delay.
// Buttons are left untouched (no listener attached) when the Clipboard API
// is unavailable, e.g. on an insecure (non-HTTPS) origin - the copy target
// stays visible and selectable as a manual fallback.
document.addEventListener("DOMContentLoaded", () => {
    if (!navigator.clipboard) {
        return
    }

    document.querySelectorAll<HTMLButtonElement>("[data-copy-target]").forEach((button) => {
        const targetId = button.dataset.copyTarget
        const target = targetId ? document.getElementById(targetId) : null
        if (!target) {
            return
        }

        const defaultLabel = button.textContent ?? ""
        const copiedLabel = button.dataset.copiedLabel ?? defaultLabel

        button.addEventListener("click", () => {
            const text = target.textContent?.trim() ?? ""
            navigator.clipboard.writeText(text).then(() => {
                button.textContent = copiedLabel
                window.setTimeout(() => {
                    button.textContent = defaultLabel
                }, 1500)
            })
        })
    })
})
