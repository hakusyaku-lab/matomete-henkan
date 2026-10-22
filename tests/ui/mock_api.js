/* 画面の動作テスト用の「にせ Python」。tests/test_ui_smoke.py が読み込みます。
 * 本物の main.Api と同じ名前・同じ形の値を返します。Api に関数を足したらここにも足してください。 */
window.__calls = [];
(function () {
  const PT = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="170"><rect width="120" height="170" fill="#fff"/></svg>');
  const TH = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="120"><rect width="160" height="120" fill="#c9d3e0"/></svg>');
  const ok = (o) => Promise.resolve(Object.assign({ ok: true }, o));
  const api = {
    app_info: () => ok({ version: '0.0.0-test', op_labels: { hankaku: '英数を半角', remove_comma: 'カンマ除去', trim: '前後の空白除去' } }),
    pick_files: () => ok({ paths: [] }),
    pick_file: () => ok({ path: null }),
    reveal: () => ok({}),
    csv_load: (paths) => ok({ files: paths.map((p, i) => ({ path: p, name: 'test' + i + '.csv', encoding: 'cp932', encoding_label: 'Shift_JIS', row_count: 10, col_count: 3 })) }),
    csv_check: () => ok({ unencodable: [{ char: '😀', row: 2, col: 1, value: '😀' }] }),
    csv_export: () => ok({ path: '/out.xlsx', rows: 10, replaced: 0 }),
    image_inspect: (paths) => ok({ skipped: 0, images: paths.map((p, i) => ({ path: p, name: 'img' + i + '.png', width: 800, height: 600, has_alpha: i === 0, animated: false, thumb: TH })) }),
    image_convert: (paths) => ok({ folder: '/out', count: paths.length, errors: [] }),
    map_load_source: (p) => ok({ path: p, name: 'src.csv', encoding_label: 'UTF-8', row_count: 3, header: ['商品番号', '価格'] }),
    map_load_target: () => ok({ header: ['コード', '価格'] }),
    map_preview: (p, rows) => ok({ rows: [rows.map((r) => r.target), rows.map((r) => (r.source === '__fixed__' ? r.fixed : 'v'))] }),
    map_export: () => ok({ path: '/out.csv', rows: 3, replaced: 0 }),
    tpl_list: () => ok({ names: ['テスト'] }),
    tpl_save: (name) => ok({ name, names: ['テスト', name] }),
    tpl_load: () => ok({ data: { mapping: [{ target: 'コード', source: '商品番号', fixed: '', ops: ['trim'] }], encoding: 'cp932' } }),
    tpl_delete: () => ok({ names: [] }),
    pdf_inspect: (paths) => ok({ skipped: 0, files: paths.map((p, i) => ({ path: p, name: 'doc' + i + '.pdf', pages: 3, thumbs: [PT, PT, PT] })) }),
    pdf_merge: () => ok({ path: '/m.pdf', pages: 6 }),
    pdf_split: () => ok({ folder: '/s', count: 3 }),
    pdf_extract: () => ok({ path: '/e.pdf', pages: 2 }),
  };
  const wrapped = {};
  Object.keys(api).forEach((k) => { wrapped[k] = (...a) => { window.__calls.push(k); return api[k](...a); }; });
  window.pywebview = { api: wrapped };
})();
