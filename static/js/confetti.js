function fireConfetti(count = 24) {
  const colors = ["#2A3B8F", "#C99A2E", "#2E9E70", "#DA5A4C"];
  for (let i = 0; i < count; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "vw";
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.animationDelay = Math.random() * 0.3 + "s";
    piece.style.animationDuration = 1.4 + Math.random() * 0.8 + "s";
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 2500);
  }
}
