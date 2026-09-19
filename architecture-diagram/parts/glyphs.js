/* Line glyphs for the parts of this pipeline that are not a vendor product: the
   publisher scripts, the landing zone, the rules, the checks. Vendor products keep
   their real logos from the sprite. That is the rule the three views share:
   vendor colour appears only on vendor glyphs, everything built here is line art
   in the accent green. */
var G={
  wal:'<path d="M3.2 7.4h4.2l2.2 9.2 3-14 2.6 11.6 1.8-6.8h4"/>',
  slot:'<rect x="3.4" y="6.4" width="17.2" height="11.2" rx="2.4"/><path d="M8.2 6.4v11.2M13 6.4v11.2"/><circle cx="17.6" cy="12" r="1.2"/>',
  parquet:'<rect x="3.6" y="4.2" width="7" height="7" rx="1.2"/><rect x="13.4" y="4.2" width="7" height="7" rx="1.2"/><rect x="3.6" y="12.8" width="7" height="7" rx="1.2"/><rect x="13.4" y="12.8" width="7" height="7" rx="1.2"/>',
  zone:'<path d="M3.6 8.2 12 4l8.4 4.2-8.4 4.2z"/><path d="M3.6 12.4 12 16.6l8.4-4.2M3.6 16.2 12 20.4l8.4-4.2"/>',
  upload:'<path d="M12 19.4V6.6M12 6.6 7.6 11M12 6.6 16.4 11"/><path d="M4.2 19.4h15.6"/>',
  broom:'<path d="M14.6 3.6 9 9.2M4.6 19.4l4.2-4.2M8.8 15.2 7 13.4a2.6 2.6 0 0 1 0-3.6l1.4-1.4a2.6 2.6 0 0 1 3.6 0l1.8 1.8z"/><path d="M12.4 14.4 19 21M15.6 11.2 21 16.6"/>',
  rules:'<path d="M4.4 6h9M4.4 12h13M4.4 18h7"/><path d="M17.6 4.6v6.2M20.6 7.6h-6"/>',
  star:'<circle cx="12" cy="12" r="3.2"/><path d="M12 4.2v4.6M12 15.2v4.6M4.2 12h4.6M15.2 12h4.6M6.6 6.6l3.2 3.2M14.2 14.2l3.2 3.2M17.4 6.6l-3.2 3.2M9.8 14.2l-3.2 3.2"/>',
  dedupe:'<rect x="4.2" y="4.2" width="10" height="10" rx="1.8"/><path d="M9.8 9.8h10v10h-10z"/><path d="M12.6 15.6l2 2 3.4-3.6"/>',
  clock:'<circle cx="12" cy="12" r="8.4"/><path d="M12 7.2v5.2l3.4 2"/>',
  check:'<circle cx="12" cy="12" r="8.4"/><path d="M8.4 12.2l2.6 2.6 4.8-5.2"/>',
  gauge:'<path d="M4 16.6a8.4 8.4 0 1 1 16 0"/><path d="M12 16.6 16.2 10"/><circle cx="12" cy="16.6" r="1.3"/>',
  coin:'<ellipse cx="12" cy="6.6" rx="7.6" ry="3"/><path d="M4.4 6.6v10.8c0 1.7 3.4 3 7.6 3s7.6-1.3 7.6-3V6.6"/><path d="M4.4 12c0 1.7 3.4 3 7.6 3s7.6-1.3 7.6-3"/>',
  user:'<circle cx="12" cy="8" r="3.4"/><path d="M5.5 20a6.5 6.5 0 0 1 13 0"/>',
  verdict:'<path d="M6.4 3.6h7.4l4.2 4.2v12.6H6.4z"/><path d="M13.6 3.6v4.4h4.4"/><path d="M9.4 14.6l1.8 1.8 3.6-4"/>',
  shield:'<path d="M12 3.2 19 6v5.4c0 4.2-2.8 7.4-7 9.4-4.2-2-7-5.2-7-9.4V6z"/><path d="M9 12l2.2 2.2L15.4 10"/>',
  loop:'<path d="M4.6 10.4a7.6 7.6 0 0 1 12.9-3.2l2.2 2.1"/><path d="M19.4 13.6a7.6 7.6 0 0 1-12.9 3.2l-2.2-2.1"/><path d="M19.9 5.2v4.1h-4.1M4.1 18.8v-4.1h4.1"/>',
  code:'<path d="M8.6 7.4 4 12l4.6 4.6M15.4 7.4 20 12l-4.6 4.6M13.4 4.6l-2.8 14.8"/>',
  table:'<rect x="3.4" y="4.6" width="17.2" height="14.8" rx="2"/><path d="M3.4 9.6h17.2M9 9.6v9.8M15 9.6v9.8"/>',
  bolt:'<path d="M13.4 3.2 5.8 13.4h5.2l-.8 7.4 7.6-10.2h-5.2z"/>',
  doc:'<path d="M6.4 3.6h7.4l4.2 4.2v12.6H6.4z"/><path d="M13.6 3.6v4.4h4.4M9.4 12.4h5.6M9.4 16h5.6"/>'
};
function glyph(k){return '<svg class="ico gl" viewBox="0 0 24 24" aria-hidden="true">'+(G[k]||"")+'</svg>';}
