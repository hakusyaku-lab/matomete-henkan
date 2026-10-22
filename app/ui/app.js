/* まとめて変換 - 画面の動き。変換処理は Python 側（window.pywebview.api）が行います。 */
(function () {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const debounce = (fn, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

  // 列の加工の一覧は Python 側（converters/normalize.py の OP_LABELS）が正。起動時に app_info で受け取る。
  let OPS = [];

  const S = {
    view: 'csv',
    csv: { files: [], fmt: 'xlsx', unencodable: [] },
    img: { images: [], fmt: 'jpeg' },
    map: { source: null, rows: [] },
    pdf: { files: [], mode: 'merge', target: 0 },
  };

  // ---------- Python 呼び出し ----------
  async function call(name, args = [], { busy = false } = {}) {
    if (busy) showBusy(true);
    try {
      const r = await window.pywebview.api[name](...args);
      if (r && r.ok === false) { toast(r.error, { error: true }); return null; }
      return r;
    } catch (e) {
      toast('エラー：' + (e && e.message ? e.message : e), { error: true });
      return null;
    } finally {
      if (busy) showBusy(false);
    }
  }

  function showBusy(on, label = '処理中…') {
    $('#busy').hidden = !on;
    $('#busy-label').textContent = label;
    $('#busy-bar').style.width = '0%';
  }
  window.__progress = (done, total, label) => {
    if ($('#busy').hidden) return;
    $('#busy-bar').style.width = total ? Math.round((done / total) * 100) + '%' : '0%';
    $('#busy-label').textContent = total ? `${label || '処理中'}（${Math.min(done + 1, total)} / ${total}）` : '処理中…';
  };

  let toastTimer;
  function toast(message, { error = false, revealPath = null } = {}) {
    const el = $('#toast');
    el.className = 'toast' + (error ? ' error' : '');
    el.innerHTML = `<span>${esc(message)}</span>` + (revealPath ? '<button type="button" id="toast-open">保存先を開く</button>' : '');
    el.hidden = false;
    if (revealPath) $('#toast-open').onclick = () => call('reveal', [revealPath]);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, error ? 9000 : 7000);
  }

  function notice(kind, mark, text) {
    return `<div class="notice ${kind}"><span class="mark">${mark}</span><span>${esc(text)}</span></div>`;
  }

  function setSeg(container, attr, value) {
    $$(`button[data-${attr}]`, container).forEach((b) => b.classList.toggle('on', b.dataset[attr] === value));
  }

  // ---------- 画面切り替え ----------
  function showView(view) {
    S.view = view;
    $$('.nav-item').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
    $$('.view').forEach((v) => v.classList.toggle('active', v.id === 'view-' + view));
  }

  // ---------- ファイルの追加（ボタン／ドラッグ） ----------
  async function pickFor(kind) {
    if (kind === 'map') return pickMapSource();
    const r = await call('pick_files', [kind]);
    if (r && r.paths.length) addFiles(kind, r.paths);
  }

  function addFiles(kind, paths) {
    if (kind === 'csv') return csvAdd(paths);
    if (kind === 'image') return imgAdd(paths);
    if (kind === 'pdf') return pdfAdd(paths);
    if (kind === 'map') {
      const p = paths.find((x) => /\.(csv|txt|tsv)$/i.test(x)) || paths[0];
      return mapSetSource(p);
    }
  }

  window.onFilesDropped = (paths) => {
    document.body.classList.remove('dragging');
    addFiles(S.view, paths);
  };

  let dragDepth = 0;
  document.addEventListener('dragenter', (e) => { e.preventDefault(); dragDepth++; document.body.classList.add('dragging'); });
  document.addEventListener('dragleave', () => { dragDepth = Math.max(dragDepth - 1, 0); if (!dragDepth) document.body.classList.remove('dragging'); });
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop', (e) => { e.preventDefault(); dragDepth = 0; document.body.classList.remove('dragging'); });

  // =====================================================================
  // ① CSV 変換・結合
  // =====================================================================
  function csvOptions() {
    return {
      protect_zero: $('#opt-protect').checked,
      hankaku: $('#opt-hankaku').checked,
      kana_zenkaku: $('#opt-kana').checked,
      wareki: $('#opt-wareki').checked,
      kishu: $('#opt-kishu').checked,
      trim: $('#opt-trim').checked,
      add_source: $('#opt-source').checked,
    };
  }
  const csvPaths = () => S.csv.files.filter((f) => !f.error).map((f) => f.path);

  async function csvAdd(paths) {
    const known = new Set(S.csv.files.map((f) => f.path));
    const fresh = paths.filter((p) => !known.has(p));
    if (!fresh.length) return;
    const r = await call('csv_load', [fresh], { busy: true });
    if (!r) return;
    S.csv.files.push(...r.files);
    renderCsv();
    csvCheck();
  }

  function renderCsv() {
    const files = S.csv.files;
    $('#csv-count').textContent = files.length;
    $('#csv-files').innerHTML = files.length
      ? files.map((f, i) => f.error
        ? `<tr class="err"><td>${esc(f.name)}</td><td colspan="3">${esc(f.error)}</td><td><button type="button" class="icon-btn" data-csv-del="${i}" aria-label="${esc(f.name)}を外す">×</button></td></tr>`
        : `<tr><td>${esc(f.name)}</td><td>${esc(f.encoding_label)}</td><td class="num">${f.row_count.toLocaleString()}</td><td class="num">${f.col_count}</td><td><button type="button" class="icon-btn" data-csv-del="${i}" aria-label="${esc(f.name)}を外す">×</button></td></tr>`).join('')
      : '<tr class="empty"><td colspan="5">まだファイルがありません</td></tr>';
    const n = csvPaths().length;
    const btn = $('#csv-run');
    btn.disabled = n === 0;
    btn.textContent = n > 1 ? '結合して保存' : '保存';
    renderCsvNotices();
  }

  function renderCsvNotices() {
    const fmt = S.csv.fmt;
    const o = csvOptions();
    const out = [];
    if (fmt === 'xlsx') {
      out.push(o.protect_zero
        ? notice('ok', '◎', '全項目を文字列で保存するので、先頭の0や長い番号もそのまま残ります。')
        : notice('ok', '○', '普通の数字は数値として保存します（集計向き）。先頭が0の値は文字列のまま残します。'));
    } else if (fmt === 'csv_utf8') {
      out.push(notice('ok', '◎', 'Excelでそのまま開いても文字化けしません。'));
      out.push(notice('warn', '△', 'CSVをExcelで開くと、先頭の0が表示上消えることがあります。Excelで編集するならExcel形式がおすすめです。'));
    } else if (fmt === 'csv_sjis') {
      const u = S.csv.unencodable;
      if (u.length) {
        const ex = [...new Set(u.map((x) => x.char))].slice(0, 8).join(' ');
        out.push(notice('warn', '△', `Shift_JISで表せない文字が${u.length >= 50 ? '50件以上' : u.length + '件'}あり、「?」に置き換わります（例：${ex}）。`));
      } else {
        out.push(notice('ok', '◎', 'Shift_JISで表せない文字はありません。'));
      }
    } else if (fmt === 'json') {
      out.push(notice('ok', '◎', '全項目を文字列で保持するので、元の表に戻せます。'));
    }
    if (csvPaths().length > 1) out.push(notice('ok', '◎', '見出し名をそろえて結合します。列の並びが違っても大丈夫です。'));
    $('#csv-notices').innerHTML = out.join('');
  }

  const csvCheck = debounce(async () => {
    if (S.csv.fmt !== 'csv_sjis' || !csvPaths().length) { S.csv.unencodable = []; renderCsvNotices(); return; }
    const r = await call('csv_check', [csvPaths(), csvOptions()]);
    S.csv.unencodable = r ? r.unencodable : [];
    renderCsvNotices();
  });

  async function csvRun() {
    const r = await call('csv_export', [csvPaths(), csvOptions(), S.csv.fmt], { busy: true });
    if (!r || r.cancelled) return;
    let msg = `${r.rows.toLocaleString()}行を保存しました`;
    if (r.replaced) msg += `（${r.replaced}か所を「?」に置き換え）`;
    toast(msg, { revealPath: r.path });
  }

  // =====================================================================
  // ② 画像一括変換
  // =====================================================================
  function imgOptions() {
    return {
      fmt: S.img.fmt,
      max_side: Number($('#img-size').value),
      quality: Number($('#img-quality').value),
      lossless: $('#img-lossless').checked,
      square: $('#img-square').checked,
      strip_gps: $('#img-gps').checked,
      sequential: $('#img-seq').checked,
      prefix: $('#img-prefix').value,
    };
  }
  const imgOk = () => S.img.images.filter((i) => !i.error);

  async function imgAdd(paths) {
    const known = new Set(S.img.images.map((i) => i.path));
    const fresh = paths.filter((p) => !known.has(p));
    if (!fresh.length) return;
    showBusy(true, '読み込み中');
    const r = await call('image_inspect', [fresh]);
    showBusy(false);
    if (!r) return;
    S.img.images.push(...r.images);
    if (r.skipped) toast(`画像ではないファイル${r.skipped}件は外しました`);
    renderImg();
  }

  function renderImg() {
    const imgs = S.img.images;
    const o = imgOptions();
    $('#img-count').textContent = imgs.length;
    $('#img-grid').innerHTML = imgs.length
      ? imgs.map((im, i) => im.error
        ? `<div class="thumb err"><div class="pic">${esc(im.error)}</div><div class="name">${esc(im.name)}</div><button type="button" class="icon-btn x" data-img-del="${i}" aria-label="${esc(im.name)}を外す">×</button></div>`
        : `<div class="thumb${o.square ? ' square' : ''}"><div class="pic"><img src="${im.thumb}" alt=""></div>
            ${im.has_alpha ? '<span class="badge">透明あり</span>' : ''}
            <button type="button" class="icon-btn x" data-img-del="${i}" aria-label="${esc(im.name)}を外す">×</button>
            <div class="name" title="${esc(im.name)}">${esc(im.name)}</div><div class="meta">${im.width}×${im.height}</div></div>`).join('')
      : '<div class="drop-empty">ここに画像をドラッグ（JPEG・PNG・WebP・HEIC など）</div>';
    $('#img-run').disabled = imgOk().length === 0;
    $('#img-run').textContent = imgOk().length ? `${imgOk().length}枚を変換` : 'まとめて変換';
    $('#img-lossless-wrap').hidden = o.fmt !== 'webp';
    $('#img-quality-wrap').hidden = o.fmt === 'png' || (o.fmt === 'webp' && o.lossless);
    $('#img-prefix-wrap').hidden = !o.sequential;
    $('#img-quality-val').textContent = o.quality;
    renderImgNotices();
  }

  function renderImgNotices() {
    const o = imgOptions();
    const ok = imgOk();
    const alpha = ok.filter((i) => i.has_alpha).length;
    const anim = ok.filter((i) => i.animated).length;
    const out = [];
    if (o.fmt === 'jpeg') {
      out.push(o.quality >= 75
        ? notice('ok', '○', `JPEG 品質${o.quality}：見た目ではほぼ分かりませんが、わずかに劣化します。`)
        : notice('warn', '△', `JPEG 品質${o.quality}：劣化が目に見えることがあります。`));
      if (alpha) out.push(notice('warn', '△', `透明部分のある画像${alpha}枚：透明部分は白になります。`));
    } else if (o.fmt === 'png') {
      out.push(notice('ok', '◎', 'PNG：画質は落ちません。写真はファイルサイズが大きくなります。'));
    } else {
      out.push(o.lossless
        ? notice('ok', '◎', 'WebP（無劣化）：画質は落ちません。PNGより小さくなりやすいです。')
        : notice('ok', '○', `WebP 品質${o.quality}：JPEGより小さく、劣化はわずかです。`));
    }
    if (o.square && alpha && o.fmt !== 'jpeg') out.push(notice('warn', '△', '正方形にすると、透明部分も白い背景になります。'));
    if (anim) out.push(notice('warn', '△', `アニメーション画像${anim}枚：1コマ目だけになります。`));
    if (o.max_side) out.push(notice('ok', '◎', `長辺${o.max_side}pxより大きい画像だけ縮小します（拡大はしません）。`));
    $('#img-notices').innerHTML = out.join('');
  }

  async function imgRun() {
    showBusy(true, '変換中');
    const r = await call('image_convert', [imgOk().map((i) => i.path), imgOptions()]);
    showBusy(false);
    if (!r || r.cancelled) return;
    if (r.errors.length) {
      toast(`${r.count}枚を保存しました。${r.errors.length}枚は失敗しました（${r.errors.map((e) => e.name).slice(0, 3).join('、')}）`, { error: true, revealPath: r.folder });
    } else {
      toast(`${r.count}枚を保存しました`, { revealPath: r.folder });
    }
  }

  // =====================================================================
  // ③ CSV 形式変換
  // =====================================================================
  async function pickMapSource() {
    const r = await call('pick_file', ['csv']);
    if (r && r.path) mapSetSource(r.path);
  }

  async function mapSetSource(path) {
    const r = await call('map_load_source', [path], { busy: true });
    if (!r) return;
    S.map.source = r;
    $('#map-src-info').innerHTML = `<strong>${esc(r.name)}</strong>（${esc(r.encoding_label)}・${r.row_count.toLocaleString()}行・${r.header.length}列）`;
    renderMap();
  }

  function newMapRow(target = '', source = '') {
    return { target, source, fixed: '', ops: [] };
  }

  function sourceOptions(row) {
    const header = S.map.source ? S.map.source.header : [];
    const opts = ['<option value="">（空欄）</option>'];
    header.forEach((h) => opts.push(`<option value="${esc(h)}"${row.source === h ? ' selected' : ''}>${esc(h)}</option>`));
    if (row.source && row.source !== '__fixed__' && !header.includes(row.source)) {
      opts.push(`<option value="${esc(row.source)}" selected>${esc(row.source)}（元のCSVにありません）</option>`);
    }
    opts.push(`<option value="__fixed__"${row.source === '__fixed__' ? ' selected' : ''}>固定値を入れる</option>`);
    return opts.join('');
  }

  function renderMap() {
    const rows = S.map.rows;
    $('#map-rows').innerHTML = rows.length
      ? rows.map((r, i) => `<tr>
          <td class="target"><input type="text" data-map="target" data-i="${i}" value="${esc(r.target)}" aria-label="変換先の列名"></td>
          <td><div class="src-cell">
            <select data-map="source" data-i="${i}" aria-label="元の列">${sourceOptions(r)}</select>
            ${r.source === '__fixed__' ? `<input type="text" data-map="fixed" data-i="${i}" value="${esc(r.fixed)}" placeholder="入れる値" aria-label="固定値">` : ''}
          </div></td>
          <td><div class="chips">${OPS.map(([k, label]) => `<label class="chip${r.ops.includes(k) ? ' on' : ''}"><input type="checkbox" data-map="op" data-op="${k}" data-i="${i}"${r.ops.includes(k) ? ' checked' : ''}>${label}</label>`).join('')}</div></td>
          <td style="white-space:nowrap">
            <button type="button" class="icon-btn" data-map-move="-1" data-i="${i}" aria-label="上へ"${i === 0 ? ' disabled' : ''}>↑</button>
            <button type="button" class="icon-btn" data-map-move="1" data-i="${i}" aria-label="下へ"${i === rows.length - 1 ? ' disabled' : ''}>↓</button>
            <button type="button" class="icon-btn" data-map-del="${i}" aria-label="この列を削除">×</button>
          </td></tr>`).join('')
      : '<tr class="empty"><td colspan="4">「＋ 列を追加」か「見本CSVから列を読み込む」で始めます</td></tr>';
    $('#map-run').disabled = !(S.map.source && rows.length);
    mapPreview();
  }

  const mapPreview = debounce(async () => {
    const el = $('#map-preview');
    if (!S.map.source || !S.map.rows.length) {
      el.innerHTML = '<tbody><tr class="empty"><td>元のCSVと列の対応を設定すると表示されます</td></tr></tbody>';
      return;
    }
    const r = await call('map_preview', [S.map.source.path, S.map.rows, 3]);
    if (!r) return;
    const [head, ...body] = r.rows;
    el.innerHTML = `<thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${
      body.length ? body.map((row) => `<tr>${row.map((v) => `<td>${esc(v)}</td>`).join('')}</tr>`).join('') : `<tr class="empty"><td colspan="${head.length}">元のCSVにデータ行がありません</td></tr>`
    }</tbody>`;
  }, 300);

  async function mapFromSample() {
    const r = await call('pick_file', ['csv']);
    if (!r || !r.path) return;
    const t = await call('map_load_target', [r.path], { busy: true });
    if (!t) return;
    const header = S.map.source ? S.map.source.header : [];
    S.map.rows = t.header.map((h) => newMapRow(h, header.includes(h) ? h : ''));
    renderMap();
    toast(`変換先の列を${t.header.length}個読み込みました。同じ名前の列は自動で対応させています`);
  }

  async function tplRefresh(selected = '') {
    const r = await call('tpl_list');
    const names = r ? r.names : [];
    $('#map-tpl').innerHTML = '<option value="">（テンプレートを使わない）</option>' + names.map((n) => `<option value="${esc(n)}"${n === selected ? ' selected' : ''}>${esc(n)}</option>`).join('');
    $('#map-tpl-del').disabled = !selected;
  }

  async function tplLoad(name) {
    $('#map-tpl-del').disabled = !name;
    if (!name) return;
    const r = await call('tpl_load', [name]);
    if (!r) return;
    const d = r.data || {};
    S.map.rows = (d.mapping || []).map((m) => ({ target: m.target || '', source: m.source || '', fixed: m.fixed || '', ops: m.ops || [] }));
    if (d.encoding) $('#map-enc').value = d.encoding;
    $('#map-tpl-name').value = name;
    renderMap();
  }

  async function tplSave() {
    const name = $('#map-tpl-name').value.trim();
    if (!name) { toast('テンプレート名を入力してください', { error: true }); $('#map-tpl-name').focus(); return; }
    if (!S.map.rows.length) { toast('列の対応を設定してから保存してください', { error: true }); return; }
    const r = await call('tpl_save', [name, { mapping: S.map.rows, encoding: $('#map-enc').value }]);
    if (!r) return;
    await tplRefresh(r.name);
    toast(`テンプレート「${r.name}」を保存しました`);
  }

  let delArmed = false;
  async function tplDelete() {
    const name = $('#map-tpl').value;
    if (!name) return;
    const btn = $('#map-tpl-del');
    if (!delArmed) {
      delArmed = true;
      btn.textContent = 'もう一度押すと削除';
      setTimeout(() => { delArmed = false; btn.textContent = '削除'; }, 3000);
      return;
    }
    delArmed = false;
    btn.textContent = '削除';
    const r = await call('tpl_delete', [name]);
    if (r) { await tplRefresh(''); toast(`テンプレート「${name}」を削除しました`); }
  }

  async function mapRun() {
    const r = await call('map_export', [S.map.source.path, S.map.rows, $('#map-enc').value], { busy: true });
    if (!r || r.cancelled) return;
    let msg = `${r.rows.toLocaleString()}行を保存しました`;
    if (r.replaced) msg += `（${r.replaced}か所を「?」に置き換え）`;
    toast(msg, { revealPath: r.path });
  }

  // =====================================================================
  // ④ PDF
  // =====================================================================
  async function pdfAdd(paths) {
    showBusy(true, '読み込み中');
    const r = await call('pdf_inspect', [paths]);
    showBusy(false);
    if (!r) return;
    S.pdf.files.push(...r.files);
    if (r.skipped) toast(`PDFではないファイル${r.skipped}件は外しました`);
    renderPdf();
  }

  function parseRangesLoose(text, total) {
    const set = new Set();
    const t = String(text || '').replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xFEE0))
      .replace(/[、，]/g, ',').replace(/[－〜~]/g, '-').replace(/\s+/g, '');
    for (const part of t.split(',')) {
      const m = part.match(/^(\d+)?-(\d+)?$|^(\d+)$/);
      if (!m) continue;
      const a = m[3] ? +m[3] : +(m[1] || 1);
      const b = m[3] ? +m[3] : +(m[2] || total);
      for (let i = a; i <= Math.min(b, total); i++) if (i >= 1) set.add(i);
    }
    return set;
  }

  function renderPdf() {
    const { files, mode } = S.pdf;
    if (S.pdf.target >= files.length) S.pdf.target = 0;
    const okFiles = files.filter((f) => !f.error);
    const rangesInput = $('#pdf-ranges');
    const ranges = rangesInput ? rangesInput.value : '';
    const list = $('#pdf-list');
    list.innerHTML = files.length ? files.map((f, i) => {
      if (f.error) {
        return `<div class="pdf-file"><div class="top"><div class="title">${esc(f.name)}</div><button type="button" class="icon-btn" data-pdf-del="${i}" aria-label="${esc(f.name)}を外す">×</button></div><div style="color:var(--err-ink)">${esc(f.error)}</div></div>`;
      }
      const isTarget = mode !== 'merge' && i === S.pdf.target;
      const sel = mode === 'merge' ? null : (isTarget ? (mode === 'extract' ? parseRangesLoose(ranges, f.pages) : null) : new Set());
      const shown = Math.min(f.pages, 30);
      const pages = [];
      for (let p = 1; p <= shown; p++) {
        const on = mode === 'merge' || (isTarget && (mode === 'split' || (sel && sel.has(p))));
        const img = f.thumbs && f.thumbs[p - 1] ? `<img src="${f.thumbs[p - 1]}" alt="">` : '';
        pages.push(`<div class="page${on ? ' sel' : ''}"><div class="sheet">${img}</div>${p}ページ</div>`);
      }
      if (f.pages > shown) pages.push(`<div class="page more"><div class="sheet">ほか${f.pages - shown}ページ</div></div>`);
      return `<div class="pdf-file${isTarget ? ' target' : ''}">
        <div class="top">
          ${mode !== 'merge' ? `<label class="target-radio"><input type="radio" name="pdf-target" data-pdf-target="${i}"${isTarget ? ' checked' : ''}>対象</label>` : ''}
          <div class="title">${esc(f.name)} <small>（${f.pages}ページ）</small></div>
          <button type="button" class="icon-btn" data-pdf-move="-1" data-i="${i}" aria-label="上へ"${i === 0 ? ' disabled' : ''}>↑</button>
          <button type="button" class="icon-btn" data-pdf-move="1" data-i="${i}" aria-label="下へ"${i === files.length - 1 ? ' disabled' : ''}>↓</button>
          <button type="button" class="icon-btn" data-pdf-del="${i}" aria-label="${esc(f.name)}を外す">×</button>
        </div>
        <div class="pages">${pages.join('')}</div></div>`;
    }).join('') : '<div class="drop-empty">ここにPDFをドラッグ</div>';

    const field = $('#pdf-field');
    const run = $('#pdf-run');
    if (mode === 'merge') {
      field.innerHTML = `<div class="muted">上から順に結合します（↑↓で並べ替え）。${okFiles.length}ファイル・合計${okFiles.reduce((a, f) => a + f.pages, 0)}ページ</div>`;
      run.textContent = '結合して保存';
      run.disabled = okFiles.length < 2;
    } else if (mode === 'split') {
      if (!$('#pdf-every')) field.innerHTML = '<label class="field inline"><input type="number" id="pdf-every" min="1" value="1" style="width:90px" aria-label="何ページごと"><span>ページごとに分ける（「対象」のPDF）</span></label>';
      run.textContent = '分割して保存';
      run.disabled = !(files[S.pdf.target] && !files[S.pdf.target].error);
    } else {
      if (!$('#pdf-ranges')) field.innerHTML = '<label class="field"><span class="label">抜き出すページ（例：1-3, 5）</span><input type="text" id="pdf-ranges" placeholder="1-3, 5"></label>';
      run.textContent = '抜き出して保存';
      run.disabled = !(files[S.pdf.target] && !files[S.pdf.target].error);
    }
  }

  function pdfSetMode(mode) {
    S.pdf.mode = mode;
    $$('#pdf-modes button').forEach((b) => { const on = b.dataset.mode === mode; b.classList.toggle('on', on); b.setAttribute('aria-selected', on); });
    $('#pdf-field').innerHTML = '';
    renderPdf();
  }

  async function pdfRun() {
    const { files, mode, target } = S.pdf;
    let r;
    if (mode === 'merge') {
      r = await call('pdf_merge', [files.filter((f) => !f.error).map((f) => f.path)], { busy: true });
      if (r && !r.cancelled) toast(`${r.pages}ページのPDFを保存しました`, { revealPath: r.path });
    } else if (mode === 'split') {
      const every = Math.max(1, parseInt($('#pdf-every').value, 10) || 1);
      r = await call('pdf_split', [files[target].path, every], { busy: true });
      if (r && !r.cancelled) toast(`${r.count}個のPDFに分けて保存しました`, { revealPath: r.folder });
    } else {
      r = await call('pdf_extract', [files[target].path, $('#pdf-ranges').value], { busy: true });
      if (r && !r.cancelled) toast(`${r.pages}ページを抜き出して保存しました`, { revealPath: r.path });
    }
  }

  // ---------- イベント ----------
  function bind() {
    $$('.nav-item').forEach((b) => b.addEventListener('click', () => showView(b.dataset.view)));
    $$('[data-pick]').forEach((b) => b.addEventListener('click', () => pickFor(b.dataset.pick)));

    // ① CSV
    $('#csv-fmt').addEventListener('click', (e) => {
      const b = e.target.closest('button[data-fmt]');
      if (!b) return;
      S.csv.fmt = b.dataset.fmt;
      setSeg($('#csv-fmt'), 'fmt', S.csv.fmt);
      renderCsvNotices();
      csvCheck();
    });
    $$('#view-csv .options input').forEach((el) => el.addEventListener('change', () => { renderCsvNotices(); csvCheck(); }));
    $('#csv-files').addEventListener('click', (e) => {
      const b = e.target.closest('[data-csv-del]');
      if (!b) return;
      S.csv.files.splice(+b.dataset.csvDel, 1);
      renderCsv();
      csvCheck();
    });
    $('#csv-clear').addEventListener('click', () => { S.csv.files = []; renderCsv(); csvCheck(); });
    $('#csv-run').addEventListener('click', csvRun);

    // ② 画像
    $('#img-fmt').addEventListener('click', (e) => {
      const b = e.target.closest('button[data-fmt]');
      if (!b) return;
      S.img.fmt = b.dataset.fmt;
      setSeg($('#img-fmt'), 'fmt', S.img.fmt);
      renderImg();
    });
    ['#img-size', '#img-quality', '#img-lossless', '#img-square', '#img-gps', '#img-seq'].forEach((s) => $(s).addEventListener('input', renderImg));
    $('#img-grid').addEventListener('click', (e) => {
      const b = e.target.closest('[data-img-del]');
      if (!b) return;
      S.img.images.splice(+b.dataset.imgDel, 1);
      renderImg();
    });
    $('#img-clear').addEventListener('click', () => { S.img.images = []; renderImg(); });
    $('#img-run').addEventListener('click', imgRun);

    // ③ 形式変換
    $('#map-src-pick').addEventListener('click', pickMapSource);
    $('#map-add').addEventListener('click', () => { S.map.rows.push(newMapRow()); renderMap(); });
    $('#map-copy-all').addEventListener('click', () => {
      if (!S.map.source) { toast('先に元のCSVを選んでください', { error: true }); return; }
      S.map.rows = S.map.source.header.map((h) => newMapRow(h, h));
      renderMap();
    });
    $('#map-from-sample').addEventListener('click', mapFromSample);
    const rowsEl = $('#map-rows');
    rowsEl.addEventListener('input', (e) => {
      const el = e.target;
      const i = +el.dataset.i;
      const row = S.map.rows[i];
      if (!row) return;
      if (el.dataset.map === 'target') { row.target = el.value; mapPreview(); }
      if (el.dataset.map === 'fixed') { row.fixed = el.value; mapPreview(); }
    });
    rowsEl.addEventListener('change', (e) => {
      const el = e.target;
      const row = S.map.rows[+el.dataset.i];
      if (!row) return;
      if (el.dataset.map === 'source') { row.source = el.value; renderMap(); }
      if (el.dataset.map === 'op') {
        const k = el.dataset.op;
        row.ops = el.checked ? [...row.ops.filter((x) => x !== k), k] : row.ops.filter((x) => x !== k);
        el.closest('.chip').classList.toggle('on', el.checked);
        mapPreview();
      }
    });
    rowsEl.addEventListener('click', (e) => {
      const del = e.target.closest('[data-map-del]');
      const mv = e.target.closest('[data-map-move]');
      if (del) { S.map.rows.splice(+del.dataset.mapDel, 1); renderMap(); }
      if (mv) {
        const i = +mv.dataset.i, j = i + +mv.dataset.mapMove;
        if (j < 0 || j >= S.map.rows.length) return;
        [S.map.rows[i], S.map.rows[j]] = [S.map.rows[j], S.map.rows[i]];
        renderMap();
      }
    });
    $('#map-tpl').addEventListener('change', (e) => tplLoad(e.target.value));
    $('#map-tpl-save').addEventListener('click', tplSave);
    $('#map-tpl-del').addEventListener('click', tplDelete);
    $('#map-run').addEventListener('click', mapRun);

    // ④ PDF
    $('#pdf-modes').addEventListener('click', (e) => { const b = e.target.closest('button[data-mode]'); if (b) pdfSetMode(b.dataset.mode); });
    $('#pdf-list').addEventListener('click', (e) => {
      const del = e.target.closest('[data-pdf-del]');
      const mv = e.target.closest('[data-pdf-move]');
      const tg = e.target.closest('[data-pdf-target]');
      if (del) { S.pdf.files.splice(+del.dataset.pdfDel, 1); renderPdf(); }
      if (mv) {
        const i = +mv.dataset.i, j = i + +mv.dataset.pdfMove;
        if (j < 0 || j >= S.pdf.files.length) return;
        [S.pdf.files[i], S.pdf.files[j]] = [S.pdf.files[j], S.pdf.files[i]];
        if (S.pdf.target === i) S.pdf.target = j; else if (S.pdf.target === j) S.pdf.target = i;
        renderPdf();
      }
      if (tg) { S.pdf.target = +tg.dataset.pdfTarget; renderPdf(); }
    });
    $('#pdf-field').addEventListener('input', (e) => { if (e.target.id === 'pdf-ranges') renderPdf(); });
    $('#pdf-run').addEventListener('click', pdfRun);
  }

  async function init() {
    bind();
    renderCsv();
    renderImg();
    renderMap();
    renderPdf();
    const info = await call('app_info');
    if (info) {
      $('#version').textContent = `バージョン ${info.version}`;
      OPS = Object.entries(info.op_labels || {});
      renderMap();
    }
    tplRefresh();
  }

  if (window.pywebview && window.pywebview.api) init();
  else window.addEventListener('pywebviewready', init, { once: true });
})();
