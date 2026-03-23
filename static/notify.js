(function(){
  async function pollLatest(){
    try{
      const resp = await fetch('/api/latest_detection');
      if(!resp.ok) return;
      const data = await resp.json();
      if(data && data.intensity){
        showBanner(`🔥 Fire detected (${data.intensity}) at ${data.date} ${data.time}`);
      }
    }catch(e){/* ignore */}
  }

  function showBanner(text){
    let el = document.getElementById('fire-banner');
    if(!el){
      el = document.createElement('div');
      el.id = 'fire-banner';
      el.style.position = 'fixed';
      el.style.top = '0';
      el.style.left = '0';
      el.style.right = '0';
      el.style.zIndex = '9999';
      el.style.background = '#b00020';
      el.style.color = 'white';
      el.style.padding = '12px 16px';
      el.style.fontFamily = 'Arial, sans-serif';
      el.style.textAlign = 'center';
      document.body.appendChild(el);
    }
    el.textContent = text;
    el.style.display = 'block';
    setTimeout(()=>{ el.style.display = 'none'; }, 10000);
  }

  setInterval(pollLatest, 8000);
})();



