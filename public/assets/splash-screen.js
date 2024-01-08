var isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

var body = document.querySelector('body');
var html = document.querySelector('html');
var defClassName = 'splash-screen';

if (!isDark) {
  body?.classList.remove(defClassName);
  html.classList.remove(defClassName);
}
