/**
 * Toggle visibility of price history sections
 * @param {string} historyId - The ID of the history section to toggle
 */
function toggleHistory(historyId) {
    const historyDiv = document.getElementById(historyId);
    const icon = document.getElementById("icon-" + historyId);
    const button = icon.parentElement;
    
    if (historyDiv.classList.contains("hidden")) {
        historyDiv.classList.remove("hidden");
        icon.style.transform = "rotate(180deg)";
        const textNode = Array.from(button.childNodes).find(node => 
            node.nodeType === 3 && node.textContent.includes("Afficher")
        );
        if (textNode) textNode.textContent = "Masquer l'historique des prix";
    } else {
        historyDiv.classList.add("hidden");
        icon.style.transform = "rotate(0deg)";
        const textNode = Array.from(button.childNodes).find(node => 
            node.nodeType === 3 && node.textContent.includes("Masquer")
        );
        if (textNode) textNode.textContent = "Afficher l'historique des prix";
    }
}
