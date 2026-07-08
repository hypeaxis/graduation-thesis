document.addEventListener("DOMContentLoaded", () => {
  const searchBox = document.getElementById("searchBox");
  const cards = Array.from(document.querySelectorAll("[data-theory-card]"));

  if (!searchBox) {
    return;
  }

  searchBox.addEventListener("input", () => {
    const needle = searchBox.value.trim().toLowerCase();
    cards.forEach((card) => {
      const haystack = card.getAttribute("data-search") || "";
      card.style.display = !needle || haystack.includes(needle) ? "" : "none";
    });
  });
});