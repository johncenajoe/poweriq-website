document.addEventListener('DOMContentLoaded', () => {
  // Highlight active nav link
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });

  // Mobile hamburger toggle
  const hamburger = document.getElementById('navHamburger');
  const navLinks  = document.getElementById('navLinks');
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('open');
      navLinks.classList.toggle('open');
    });
    navLinks.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        hamburger.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });
  }
});
