// Note filters (All / Work / Lab). Without JS every note stays visible.
document.querySelectorAll('.filters').forEach((group) => {
  const list = group.nextElementSibling;
  if (!list) return;
  group.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter');
    if (!btn) return;
    const value = btn.dataset.filter;
    group.querySelectorAll('.filter').forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
    list.querySelectorAll('.note').forEach((note) => {
      note.hidden = value !== 'all' && note.dataset.group !== value;
    });
  });
});

// Highlight the current section in the table of contents.
const tocLinks = document.querySelectorAll('.toc a');
if (tocLinks.length && 'IntersectionObserver' in window) {
  const byId = new Map([...tocLinks].map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      tocLinks.forEach((a) => a.removeAttribute('aria-current'));
      const link = byId.get(entry.target.id);
      if (link) link.setAttribute('aria-current', 'true');
    });
  }, { rootMargin: '0px 0px -70% 0px' });
  byId.forEach((_, id) => { const el = document.getElementById(id); if (el) observer.observe(el); });
}
