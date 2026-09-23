document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-nav-toggle]");
    const menu = document.querySelector("[data-nav-menu]");

    if (toggle && menu) {
        const setMenuState = (isOpen) => {
            toggle.setAttribute("aria-expanded", String(isOpen));
            menu.dataset.open = String(isOpen);
        };

        toggle.addEventListener("click", () => {
            const isOpen = toggle.getAttribute("aria-expanded") === "true";
            setMenuState(!isOpen);
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
                setMenuState(false);
                toggle.focus();
            }
        });
    }

    document.querySelectorAll("[data-dismiss-message]").forEach((button) => {
        button.addEventListener("click", () => {
            const message = button.closest("[data-message]");
            if (message) {
                message.remove();
            }
        });
    });
});
