// ui.js — scroll reveals, video cards, chat panel open/close

// ── Scroll reveal ──────────────────────────────────────────────────────────
const observer = new IntersectionObserver(
  (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add('visible')),
  { threshold: 0.12 }
);
document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));

// ── Video cards ────────────────────────────────────────────────────────────
document.querySelectorAll('.video-card').forEach((card) => {
  card.addEventListener('click', () => {
    const localFile = card.dataset.localFile;
    const wistiaId  = card.dataset.wistiaId;
    const embedContainer = card.closest('.group').querySelector('.video-embed');

    card.classList.add('hidden');
    embedContainer.classList.remove('hidden');

    if (localFile) {
      embedContainer.innerHTML = `
        <video class="w-full h-full bg-black" controls autoplay>
          <source src="${localFile}" type="video/mp4">
        </video>`;
    } else if (wistiaId) {
      embedContainer.innerHTML = `
        <div class="wistia_embed wistia_async_${wistiaId} autoPlay=true seo=false"
             style="width:100%;height:100%;"></div>`;
    }
  });
});

// ── Chat panel open/close ──────────────────────────────────────────────────
window.openChat = function () {
  const panel = document.getElementById('chat-panel');
  panel.classList.remove('hidden');
  requestAnimationFrame(() => panel.classList.add('open'));
  document.getElementById('chat-input')?.focus();
};

window.closeChat = function () {
  const panel = document.getElementById('chat-panel');
  panel.classList.remove('open');
  panel.addEventListener('transitionend', () => panel.classList.add('hidden'), { once: true });
};
