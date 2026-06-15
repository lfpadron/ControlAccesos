export type ExportFormat = 'excel' | 'csv' | 'json';
export type ExportColumn<T> = {
  key: keyof T | string;
  label: string;
  value?: (row: T) => string | number | boolean | null | undefined;
};

function fileSafeName(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function escapeCsv(value: unknown) {
  const text = value === null || value === undefined ? '' : String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

function escapeHtml(value: unknown) {
  const text = value === null || value === undefined ? '' : String(value);
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function cellValue<T extends object>(row: T, column: ExportColumn<T>) {
  if (column.value) return column.value(row);
  return (row as Record<string, unknown>)[column.key as string];
}

function downloadBlob(content: BlobPart, mimeType: string, filename: string) {
  const blob = new Blob([content], { type: mimeType });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function exportRows<T extends object>(
  rows: T[],
  columns: ExportColumn<T>[],
  basename: string,
  format: ExportFormat,
) {
  const safeName = fileSafeName(basename) || 'exportacion';
  if (format === 'json') {
    const payload = rows.map((row) =>
      Object.fromEntries(columns.map((column) => [column.label, cellValue(row, column)])),
    );
    downloadBlob(JSON.stringify(payload, null, 2), 'application/json;charset=utf-8', `${safeName}.json`);
    return;
  }

  if (format === 'csv') {
    const header = columns.map((column) => escapeCsv(column.label)).join(',');
    const body = rows.map((row) => columns.map((column) => escapeCsv(cellValue(row, column))).join(',')).join('\n');
    downloadBlob(`\ufeff${header}\n${body}`, 'text/csv;charset=utf-8', `${safeName}.csv`);
    return;
  }

  const header = columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join('');
  const body = rows
    .map((row) => `<tr>${columns.map((column) => `<td>${escapeHtml(cellValue(row, column))}</td>`).join('')}</tr>`)
    .join('');
  const html = `<html><head><meta charset="utf-8"></head><body><table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></body></html>`;
  downloadBlob(html, 'application/vnd.ms-excel;charset=utf-8', `${safeName}.xls`);
}
