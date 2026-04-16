const gallery = document.getElementById("gallery");
const photoCount = document.getElementById("photoCount");
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightboxImg");
const lightboxCaption = document.getElementById("lightboxCaption");
const closeBtn = document.getElementById("closeBtn");

function openLightbox(src, alt, caption) {
  lightboxImg.src = src;
  lightboxImg.alt = alt || "放大预览";
  lightboxCaption.textContent = caption || "";
  lightbox.classList.add("open");
  lightbox.setAttribute("aria-hidden", "false");
}

function closeLightbox() {
  lightbox.classList.remove("open");
  lightbox.setAttribute("aria-hidden", "true");
  lightboxImg.src = "";
  lightboxCaption.textContent = "";
}

function renderEmptyHint() {
  gallery.innerHTML = `
    <article class="empty">
      <strong>还没有读取到照片。</strong><br>
      请把图片放到 <code>assets/photos/</code>，然后在 <code>assets/gallery.json</code> 里登记路径。
    </article>
  `;
  photoCount.textContent = "0 张照片";
}

function createPhotoCard(item) {
  const card = document.createElement("figure");
  card.className = "photo-card";

  const img = document.createElement("img");
  img.className = "photo";
  img.src = item.src;
  img.alt = item.title || "照片";
  img.loading = "lazy";
  img.decoding = "async";

  const figcap = document.createElement("figcaption");
  figcap.className = "caption";
  figcap.innerHTML = `
    <h3>${item.title || "未命名照片"}</h3>
    <p>${item.date || ""}</p>
  `;

  img.addEventListener("click", () => {
    openLightbox(item.src, item.title || "照片", `${item.title || "照片"}  ${item.date || ""}`);
  });

  card.appendChild(img);
  card.appendChild(figcap);
  return card;
}

function renderGallery(items) {
  gallery.innerHTML = "";
  if (!items || items.length === 0) {
    renderEmptyHint();
    return;
  }
  items.forEach((item) => gallery.appendChild(createPhotoCard(item)));
  photoCount.textContent = `${items.length} 张照片`;
}

async function loadGallery() {
  try {
    const response = await fetch("./assets/gallery.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("gallery.json not found");
    }
    const data = await response.json();
    if (!Array.isArray(data.photos)) {
      throw new Error("invalid gallery.json");
    }
    renderGallery(data.photos);
  } catch (error) {
    renderEmptyHint();
  }
}

closeBtn.addEventListener("click", closeLightbox);

lightbox.addEventListener("click", (event) => {
  if (event.target === lightbox) closeLightbox();
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeLightbox();
});

loadGallery();
