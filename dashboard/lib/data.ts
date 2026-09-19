export type Cell = {party: string; uf: string; office: string; gender: string; race: string; candidates: number; funded: number; value: number};
export type Flow = {party: string; donorParty: string; source: string; target: string; value: number};
export type Efficiency = {party: string; uf: string; office: string; value: number; votes: number; candidates: number};
export type Dataset = {generatedAt: string; source: string; years: Record<string, {cells: Cell[]; electorate: Record<string, number>; efficiency: Efficiency[]; flows: Flow[]}>};
export const number = (v: number) => new Intl.NumberFormat('pt-BR').format(v || 0);
export const percent = (v: number) => `${Number.isFinite(v) ? v.toLocaleString('pt-BR', {maximumFractionDigits: 1}) : '0'}%`;
export function money(v: number, symbol = true) {
  const unit = Math.abs(v) >= 1e9 ? 1e9 : Math.abs(v) >= 1e6 ? 1e6 : Math.abs(v) >= 1e3 ? 1e3 : 1;
  return `${symbol ? 'R$ ' : ''}${(v / unit).toLocaleString('pt-BR', {minimumFractionDigits: unit > 1 ? 2 : 0, maximumFractionDigits: 2})}${unit === 1e9 ? ' bi' : unit === 1e6 ? ' mi' : unit === 1e3 ? ' mil' : ''}`;
}
export const sum = (rows: Cell[], key: 'value' | 'candidates' | 'funded') => rows.reduce((s, c) => s + c[key], 0);
export const selectCells = (data: Dataset, year: string, party: string, office: string) => data.years[year].cells.filter(c => (party === 'Todos os partidos' || c.party === party) && (office === 'Todos os cargos' || c.office === office));
export function group(cells: Cell[], key: 'party' | 'uf' | 'gender' | 'race') {
  const groups = new Map<string, {name: string; value: number; candidates: number; funded: number}>();
  for (const c of cells) { const name = c[key] || 'Não informado'; const g = groups.get(name) || {name, value: 0, candidates: 0, funded: 0}; g.value += c.value; g.candidates += c.candidates; g.funded += c.funded; groups.set(name, g); }
  return [...groups.values()].sort((a, b) => b.value - a.value);
}
