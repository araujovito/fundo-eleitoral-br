export type Cell = {party: string; uf: string; office: string; gender: string; race: string; candidates: number; funded: number; value: number};
export type Flow = {party: string; donorParty: string; source: string; target: string; value: number};
export type Efficiency = {party: string; uf: string; office: string; value: number; votes: number; candidates: number};
export type Concentration = {party: string; gini: number; coverage: number; top10: number};
export type Renewal = {profile: string; value: number; candidates: number; share: number};
export type SeatReference = {year: number; byUf: Record<string, number>};
export type CycleMetadata = {status: 'partial' | 'final'; partial: boolean; observedDirectFefc: number; officialAllocation: number | null; coveragePercent: number | null; coverageBasis: string | null; resultsAvailable: boolean; seatReferenceYears: number[]};
export type Dataset = {generatedAt: string; source: string; years: Record<string, {metadata?: CycleMetadata; cells: Cell[]; electorate: Record<string, number>; seats: Record<string, SeatReference>; efficiency: Efficiency[]; flows: Flow[]; concentration: Concentration[]; renewal: Renewal[]}>};
export const DASHBOARD_VIEWS = ['overview', 'territory', 'representation', 'strategy', 'efficiency', 'flows', 'method'] as const;
export type DashboardView = typeof DASHBOARD_VIEWS[number];
export type DashboardState = {year: string; party: string; office: string; view: DashboardView};
export function parseDashboardState(search: string): DashboardState {
  const params = new URLSearchParams(search);
  const year = ['2018', '2022', '2026'].includes(params.get('ano') || '') ? params.get('ano')! : '2022';
  const requestedView = params.get('visao');
  const view = DASHBOARD_VIEWS.includes(requestedView as DashboardView) ? requestedView as DashboardView : 'overview';
  return {year, party: params.get('partido') || 'Todos os partidos', office: params.get('cargo') || 'Todos os cargos', view};
}
export function dashboardSearch({year, party, office, view}: DashboardState) {
  const params = new URLSearchParams();
  if (year !== '2022') params.set('ano', year);
  if (party !== 'Todos os partidos') params.set('partido', party);
  if (office !== 'Todos os cargos') params.set('cargo', office);
  if (view !== 'overview') params.set('visao', view);
  const value = params.toString();
  return value ? `?${value}` : '';
}
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
