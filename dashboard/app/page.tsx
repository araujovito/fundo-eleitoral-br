'use client';

import { useEffect, useMemo, useState } from 'react';
import { flushSync } from 'react-dom';
import { ArrowUpRight, BookOpen, ChartNoAxesCombined, CircleHelp, ExternalLink, Landmark, Layers3, MapPin, Network, RefreshCw, SlidersHorizontal, Users, Vote } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell as ChartCell, AreaChart, Area } from 'recharts';
import { type Dataset, money, number, percent, sum, group, selectCells } from '@/lib/data';
import { Territory, Representation, EfficiencyView, FlowsView, Method } from '@/components/analyses';

const views = [['overview', 'Visão geral', ChartNoAxesCombined], ['territory', 'Território', MapPin], ['representation', 'Representatividade', Users], ['efficiency', 'Eficiência', Vote], ['flows', 'Caminho do dinheiro', Network], ['method', 'Metodologia', CircleHelp]] as const;

function Filter({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (v: string) => void }) {
  return <div className="filter"><span>{label}</span><Select value={value} onValueChange={v => v && onChange(v)}><SelectTrigger aria-label={label}><SelectValue>{value}</SelectValue></SelectTrigger><SelectContent>{values.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}</SelectContent></Select></div>;
}
export function Panel({ title, subtitle, tag, children, className = '' }: {title: string; subtitle?: string; tag?: string; children: React.ReactNode; className?: string}) {
  return <section className={`panel ${className}`}><div className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{tag && <span className="tag">{tag}</span>}</div>{children}</section>;
}
function Stat({ label, value, note, icon: Icon, accent = false }: { label: string; value: string; note: string; icon: typeof Landmark; accent?: boolean }) {
  return <article className={`stat ${accent ? 'accent-stat' : ''}`}><div className="stat-label">{label}<Icon size={19}/></div><strong>{value}</strong><p>{note}</p></article>;
}
export function Ranking({ rows, metric = 'value' }: {rows: {name: string; value: number}[]; metric?: 'value' | 'index'}) {
  return <div className="chart" role="img" aria-label="Ranking em barras; valores disponíveis na tabela"><ResponsiveContainer width="100%" height={340}><BarChart layout="vertical" data={rows.slice(0, 10)} margin={{top: 4, right: 36, left: 0, bottom: 0}}><CartesianGrid strokeDasharray="3 5" horizontal={false} stroke="#e7ecf1"/><XAxis type="number" tickFormatter={v => metric === 'value' ? money(v, false) : `${v}×`} axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#68788a'}}/><YAxis dataKey="name" type="category" width={98} axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#36465b'}}/><Tooltip cursor={{fill: '#f1f5f9'}} formatter={v => metric === 'value' ? money(Number(v)) : `${Number(v).toFixed(2)}×`} contentStyle={{borderRadius: 10, border: '1px solid #dae3ea'}}/><Bar dataKey="value" name={metric === 'value' ? 'FEFC direto' : 'Índice'} radius={[0, 4, 4, 0]} barSize={15}>{rows.slice(0, 10).map((r, i) => <ChartCell key={r.name} fill={i === 0 ? '#167d8d' : i < 3 ? '#234c78' : '#6d90b3'}/>)}</Bar></BarChart></ResponsiveContainer></div>;
}
export default function Home() {
  const [data, setData] = useState<Dataset | null>(null), [error, setError] = useState(false);
  const [year, setYear] = useState('2022'), [party, setParty] = useState('Todos os partidos'), [office, setOffice] = useState('Todos os cargos');
  const [view, setView] = useState('overview'), [search, setSearch] = useState('');
  useEffect(() => { fetch('/data.json').then(r => {if (!r.ok) throw new Error(); return r.json();}).then(value => {
    const d = value as Dataset;
    if (!d.years?.['2022']?.cells || !d.generatedAt) throw new Error('Dados inválidos');
    setData(d);
  }).catch(() => setError(true)); }, []);
  useEffect(() => {
    type ModelContext = {registerTool: (tool: {name: string; description: string; inputSchema: object; annotations: object; execute: (input: unknown) => unknown}, options: {signal: AbortSignal}) => void | Promise<void>};
    const context = (document as Document & {modelContext?: ModelContext}).modelContext;
    if (!data || !context?.registerTool) return;
    const lifecycle = new AbortController();
    const tool = {name: 'filtrar_fundo_eleitoral', description: 'Aplica ciclo e partido ao painel e retorna os totais visíveis de FEFC direto e candidaturas.', inputSchema: {type: 'object', properties: {ano: {type: 'string', enum: ['2018','2022','2026']}, partido: {type: 'string'}}, required: ['ano'], additionalProperties: false}, annotations: {readOnlyHint: false}, execute(input: unknown) {
      const args = input as {ano?: string; partido?: string};
      if (!args || !args.ano || !data.years[args.ano] || (args.partido !== undefined && typeof args.partido !== 'string')) throw new Error('Ciclo ou partido inválido');
      const p = args.partido || 'Todos os partidos';
      if (p !== 'Todos os partidos' && !data.years[args.ano].cells.some(c => c.party === p)) throw new Error('Partido ausente neste ciclo');
      const c = selectCells(data, args.ano, p, 'Todos os cargos');
      flushSync(() => {setYear(args.ano!);setParty(p);setOffice('Todos os cargos');setView('overview');setSearch('');});
      return {ano: args.ano, partido:p, fefc:sum(c,'value'), candidaturas:sum(c,'candidates'), financiadas:sum(c,'funded')};
    }};
    try { void Promise.resolve(context.registerTool(tool, {signal:lifecycle.signal})).catch(() => {}); } catch { /* Navegadores sem suporte continuam com a interface padrão. */ }
    return () => lifecycle.abort();
  }, [data]);
  const cells = useMemo(() => data ? selectCells(data, year, party, office) : [], [data, year, party, office]);
  const parties = useMemo(() => data ? [...new Set(data.years[year].cells.map(c => c.party))].sort() : [], [data, year]);
  const offices = useMemo(() => data ? [...new Set(data.years[year].cells.map(c => c.office))].filter(Boolean).sort() : [], [data, year]);
  const ranking = useMemo(() => group(cells, 'party'), [cells]);
  const total = sum(cells, 'value'), candidates = sum(cells, 'candidates'), funded = sum(cells, 'funded');
  const female = sum(cells.filter(c => c.gender === 'FEMININO'), 'value'), black = sum(cells.filter(c => ['PRETA', 'PARDA'].includes(c.race)), 'value');
  const topParty = ranking[0];
  const topFiveShare = total ? ranking.slice(0, 5).reduce((s, r) => s + r.value, 0) / total * 100 : 0;
  const femaleShare = total ? female / total * 100 : 0;
  const trend = data ? Object.keys(data.years).map(y => ({name: y === '2026' ? '2026*' : y, value: sum(selectCells(data, y, party, office), 'value')})) : [];
  const table = ranking.filter(r => r.name.toLowerCase().includes(search.toLowerCase()));
  return <div className="app-shell"><a href="#content" className="skip-link">Ir para os dados</a>
    <header className="masthead"><div className="masthead-inner"><div className="brand"><span className="brand-icon"><Landmark size={25}/></span><div><b>OBSERVATÓRIO</b><span>Fundo Eleitoral</span></div></div><div className="masthead-right"><span className="live-dot"/> Dados públicos · TSE <a href="https://github.com/araujovito/fundo-eleitoral-br" target="_blank" rel="noreferrer" aria-label="Código-fonte no GitHub"><ExternalLink size={18}/></a></div></div></header>
    <main id="content" className="workspace"><div className="page-title"><div><div className="eyebrow">FINANCIAMENTO DA DEMOCRACIA · DADOS TSE</div><h1>Para onde vai o fundo eleitoral?</h1><p>Um guia para ler as escolhas de financiamento dos partidos brasileiros.</p></div><div className="edition"><span className="edition-dot"/> Edição {year}<small>{year === '2026' ? 'Prestação de contas parcial' : 'Ciclo eleitoral encerrado'}</small></div></div>
      <div className="toolbar"><div className="filter-mark"><SlidersHorizontal size={18}/><span>Recorte</span></div><Filter label="Ciclo eleitoral" value={year} values={['2018', '2022', '2026']} onChange={v => {setYear(v); setParty('Todos os partidos'); setSearch('');}}/><Filter label="Partido" value={party} values={['Todos os partidos', ...parties]} onChange={setParty}/><Filter label="Cargo" value={office} values={['Todos os cargos', ...offices]} onChange={setOffice}/><button className="reset" onClick={() => {setParty('Todos os partidos'); setOffice('Todos os cargos'); setSearch('');}}><RefreshCw size={15}/>Limpar</button></div>
      {year === '2026' && <div className="notice"><CircleHelp size={17}/> 2026 está em prestação parcial. Os valores podem mudar e não são diretamente comparáveis aos ciclos encerrados.</div>}
      {error ? <div className="empty"><h2>Não foi possível carregar os dados</h2><p>Verifique sua conexão e tente novamente.</p><button onClick={() => location.reload()}>Tentar novamente</button></div> : !data ? <div className="loading" role="status"><Layers3 size={28}/><h2>Preparando o observatório</h2><p>Carregando os agregados do TSE…</p></div> : <>
      <section className="story-lede" aria-labelledby="leitura-titulo"><div className="story-kicker"><BookOpen size={16}/> LEITURA DO RECORTE</div><div className="story-main"><div><h2 id="leitura-titulo">O dinheiro não se distribui sozinho.</h2><p>Em {year}{year === '2026' ? ', com dados ainda parciais,' : ''} as candidaturas receberam <b>{money(total)}</b> em repasses diretos do FEFC. Os números abaixo ajudam a separar regra eleitoral, escala partidária e decisão de alocação.</p></div><div className="story-number"><strong>{percent(topFiveShare)}</strong><span>do fundo está nos cinco maiores partidos deste recorte</span></div></div><div className="reading-cards"><article><span>01 · CONCENTRAÇÃO</span><b>{topParty ? `${topParty.name} lidera com ${percent(topParty.value / total * 100)}` : 'Sem dados no recorte'}</b><p>A posição muda quando você seleciona um cargo, partido ou ciclo.</p></article><article><span>02 · REPRESENTAÇÃO</span><b>{percent(femaleShare)} vai para mulheres</b><p>Compare este valor à participação feminina entre as candidaturas na aba de representatividade.</p></article><article><span>03 · TERRITÓRIO</span><b>Eleitorado não é destino automático</b><p>Veja quais estados ficam acima ou abaixo do seu peso eleitoral.</p></article></div></section>
      <div className="stats"><Stat label="FEFC direto às candidaturas" value={money(total)} note="Repasses entre candidaturas excluídos" icon={Landmark} accent/><Stat label="Candidaturas financiadas" value={number(funded)} note={`${percent(funded / candidates * 100)} das ${number(candidates)} registradas`} icon={Vote}/><Stat label="Repasse a mulheres" value={percent(female / total * 100)} note={`${money(female)} no recorte selecionado`} icon={Users}/><Stat label="Repasse a pessoas negras" value={percent(black / total * 100)} note="Candidaturas autodeclaradas pretas e pardas" icon={ChartNoAxesCombined}/></div>
      <Tabs value={view} onValueChange={v => setView(String(v))} className="analysis-tabs"><TabsList variant="line" className="navigation">{views.map(([id, name, Icon]) => <TabsTrigger value={id} key={id}><Icon size={17}/>{name}</TabsTrigger>)}</TabsList>
      <TabsContent value="overview"><div className="section-line"><span><span className="tiny-dot"/> VISÃO NACIONAL</span><span>{party} · {year}</span></div><div className="overview-grid"><Panel title="Como os partidos distribuem o FEFC" subtitle="Os 10 maiores volumes de repasses diretos" tag="R$ nominais"><Ranking rows={ranking}/><div className="panel-foot"><span className="tiny-dot teal"/> Total recebido pelas candidaturas de cada partido.</div></Panel><div className="right-stack"><Panel title="Uma leitura entre ciclos" subtitle="FEFC direto no mesmo recorte"><div className="trend-chart"><ResponsiveContainer width="100%" height={180}><AreaChart data={trend} margin={{left: 0, right: 18, top: 18, bottom: 0}}><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#25828e" stopOpacity={0.25}/><stop offset="100%" stopColor="#25828e" stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf0f4"/><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 12}}/><YAxis tickFormatter={v => money(v, false)} axisLine={false} tickLine={false} width={65} tick={{fontSize: 12}}/><Tooltip formatter={v => money(Number(v))}/><Area type="linear" dataKey="value" name="FEFC direto" stroke="#167d8d" strokeWidth={2.5} fill="url(#area)" dot={{r: 4, fill: '#167d8d', stroke: 'white', strokeWidth: 2}}/></AreaChart></ResponsiveContainer></div><p className="chart-note">*2026 parcial. Sem correção pela inflação; siglas não são harmonizadas entre ciclos.</p></Panel><article className="insight"><div className="eyebrow">CONCENTRAÇÃO ENTRE PARTIDOS <ArrowUpRight size={17}/></div><strong>{percent(ranking.slice(0, 5).reduce((s, r) => s + r.value, 0) / total * 100)}</strong><p>do FEFC do recorte está nos {Math.min(5, ranking.length)} partidos com maior volume.</p><span>Participação entre partidos, não entre candidatos.</span></article></div></div>
      <Panel title="Partido por partido" subtitle="Totais, alcance do financiamento e participação no recorte" tag={`${ranking.length} partidos`}><div className="table-tools"><input aria-label="Buscar partido na tabela" placeholder="Buscar partido…" value={search} onChange={e => setSearch(e.target.value)}/><span>Ordenado por volume de FEFC</span></div><Table><TableHeader><TableRow><TableHead>PARTIDO</TableHead><TableHead className="numeric">FEFC DIRETO</TableHead><TableHead>PARTICIPAÇÃO</TableHead><TableHead className="numeric">CANDIDATURAS</TableHead><TableHead className="numeric">FINANCIADAS</TableHead></TableRow></TableHeader><TableBody>{table.map((r, i) => <TableRow key={r.name}><TableCell><span className="rank-number">{i + 1}</span><b>{r.name}</b></TableCell><TableCell className="numeric strong">{money(r.value)}</TableCell><TableCell><div className="share-cell"><span className="bar-track"><i style={{width: `${r.value / total * 100}%`}}/></span>{percent(r.value / total * 100)}</div></TableCell><TableCell className="numeric">{number(r.candidates)}</TableCell><TableCell className="numeric">{number(r.funded)}</TableCell></TableRow>)}{!table.length && <TableRow><TableCell colSpan={5}>Nenhum partido encontrado neste recorte.</TableCell></TableRow>}</TableBody></Table></Panel></TabsContent>
      <TabsContent value="territory"><Territory cells={cells} electorate={data.years[year].electorate}/></TabsContent>
      <TabsContent value="representation"><Representation cells={cells}/></TabsContent>
      <TabsContent value="efficiency"><EfficiencyView data={data} year={year} party={party} office={office}/></TabsContent>
      <TabsContent value="flows"><FlowsView data={data} year={year} party={party}/></TabsContent>
      <TabsContent value="method"><Method data={data}/></TabsContent>
      </Tabs></>}
      <footer><span><Landmark size={15}/> Observatório do Fundo Eleitoral</span><span>Fonte: TSE · {data ? `Extração em ${new Date(data.generatedAt).toLocaleDateString('pt-BR')}` : 'Dados abertos'}</span><a href="https://huggingface.co/datasets/buscafe/fundo-eleitoral-br" target="_blank" rel="noreferrer">Acessar a base <ArrowUpRight size={14}/></a></footer>
    </main></div>;
}
