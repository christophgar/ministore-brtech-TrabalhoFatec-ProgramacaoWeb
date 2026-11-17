const toggle=document.getElementById('theme-toggle');
function updateToggle(){const light=document.documentElement.dataset.theme==='light';toggle.textContent=light?'☾ Modo escuro':'☀ Modo claro';toggle.setAttribute('aria-pressed',String(light));}
updateToggle();
toggle.addEventListener('click',()=>{const next=document.documentElement.dataset.theme==='light'?'dark':'light';document.documentElement.dataset.theme=next;try{localStorage.setItem('brasiltech-theme',next)}catch(e){}updateToggle();});
