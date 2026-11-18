// Read the first viewport after fonts settle. Record the element path so an
// operator can find the measured node even on sites with generated classes.
() => {
  const box = (el) => el.getBoundingClientRect();
  const visible = (el) => {
    const r = box(el);
    return r.width > 4 && r.height > 4 && r.bottom > 0 && r.top < innerHeight
      && r.right > 0 && r.left < innerWidth && el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});
  };
  const path = (el) => {
    const parts = [];
    while (el && el !== document.body) {
      const siblings = [...el.parentElement.children].filter(s => s.localName === el.localName);
      parts.unshift(el.localName + (siblings.length > 1 ? ':nth-of-type(' + (siblings.indexOf(el) + 1) + ')' : ''));
      el = el.parentElement;
    }
    return ['body', ...parts].join(' > ');
  };
  const properties = ['font-family','font-size','font-weight','line-height','letter-spacing','color',
    'background-color','border-radius','padding','display','gap','text-align'];
  const sample = el => {
    const s = getComputedStyle(el);
    return {
      selector: path(el), text: el.innerText.trim().replace(/\s+/g,' ').slice(0,100),
      css: Object.fromEntries(properties.map(k => [k, s.getPropertyValue(k)])),
      box: box(el).toJSON()
    };
  };
  const nodes = sel => [...document.querySelectorAll(sel)].filter(el => visible(el) && el.innerText?.trim());
  const headings = nodes('h1,h2,[role="heading"]').sort((a,b) => parseFloat(getComputedStyle(b).fontSize) - parseFloat(getComputedStyle(a).fontSize));
  const body = nodes('p').filter(el => el.innerText.trim().length > 28);
  const controls = nodes('a,button,[role="button"]').filter(el => el.innerText.trim().length < 56);
  return {headings: headings.slice(0,4).map(sample), paragraphs: body.slice(0,5).map(sample),
    controls: controls.filter(el => !el.closest('header,nav')).slice(0,8).map(sample),
    navigation: controls.filter(el => el.closest('header,nav')).slice(0,3).map(sample)};
}
