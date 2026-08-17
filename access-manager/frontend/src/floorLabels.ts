import type { Piso, Torre } from './api/client';

type PisoLabelSource = Pick<Piso, 'codigo' | 'nombre_visible' | 'numero' | 'torre_id'>;
type TorreLabelSource = Pick<Torre, 'id' | 'nombre'>;

export function pisoVisibleLabel(item: PisoLabelSource) {
  return item.nombre_visible.trim() || `Piso ${item.numero}`;
}

export function pisoCodigoVisibleLabel(item: PisoLabelSource) {
  const codigo = item.codigo?.trim() || String(item.numero);
  const nombreVisible = item.nombre_visible.trim();
  return nombreVisible ? `${codigo} - ${nombreVisible}` : codigo;
}

export function pisoTorreLabel(item: PisoLabelSource, torres: TorreLabelSource[]) {
  const torre = torres.find((row) => row.id === item.torre_id);
  return torre ? `${torre.nombre} · ${pisoVisibleLabel(item)}` : pisoVisibleLabel(item);
}

function pisoCodigoSortValue(item: PisoLabelSource) {
  return item.codigo?.trim() || String(item.numero);
}

export function comparePisosByCodigo(left: PisoLabelSource, right: PisoLabelSource) {
  const byCodigo = pisoCodigoSortValue(left).localeCompare(pisoCodigoSortValue(right), 'es', {
    numeric: true,
    sensitivity: 'base',
  });
  if (byCodigo !== 0) return byCodigo;
  return pisoVisibleLabel(left).localeCompare(pisoVisibleLabel(right), 'es', { numeric: true, sensitivity: 'base' });
}

export function sortPisosByCodigo<T extends PisoLabelSource>(items: readonly T[]) {
  return [...items].sort(comparePisosByCodigo);
}
