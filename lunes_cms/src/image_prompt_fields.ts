// Show only the prompt fields that match "supports show people" on the image
// prompt form (#1143): the single prompt, or the variants with and without
// people. A used prompt is read-only and has no checkbox; the admin renders
// only its relevant fields then.
document.addEventListener("DOMContentLoaded", () => {
    const checkbox = document.getElementById("id_supports_show_people") as HTMLInputElement | null
    if (!checkbox) {
        return
    }

    const setVisible = (field: string, visible: boolean) => {
        document.querySelectorAll<HTMLElement>(`.form-group.field-${field}`).forEach((row) => {
            row.hidden = !visible
        })
    }

    const toggleFields = () => {
        const variants = checkbox.checked
        setVisible("prompt", !variants)
        setVisible("prompt_with_people", variants)
        setVisible("prompt_without_people", variants)
    }

    checkbox.addEventListener("change", toggleFields)
    toggleFields()
})
