const BACKEND_URL = "https://TON-BACKEND.onrender.com"; // à changer après Render

let discount = 0;

function applyPromo() {
  const code = document.getElementById("promo").value;
  if (code === "🥵2026create") {
    discount = 0.5;
    document.getElementById("promoResult").innerText =
      "🔥 -50% appliqué sur tous les plans";
  } else {
    discount = 0;
    document.getElementById("promoResult").innerText =
      "Code invalide";
  }
}

async function upload() {
  const file = document.getElementById("videoInput").files[0];
  if (!file) return alert("Choisis une vidéo");

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BACKEND_URL}/upload`, {
    method: "POST",
    body: formData
  });

  const data = await res.json();
  document.getElementById("result").src =
    BACKEND_URL + data.video_url;
}
