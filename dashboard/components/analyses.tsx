'use client';

import { useMemo } from 'react';
import {
  ArrowDownToLine,
  ArrowUpRight,
  CircleHelp,
  Network,
  Vote,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  Sankey,
  Cell as ChartCell,
} from 'recharts';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  type Cell,
  type Dataset,
  type SeatReference,
  group,
  sum,
  percent,
  money,
  number,
} from '@/lib/data';

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}
const regions: Record<string, string[]> = {
  Norte: ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
  Nordeste: ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
  'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
  Sudeste: ['ES', 'MG', 'RJ', 'SP'],
  Sul: ['PR', 'RS', 'SC'],
};
const formatIndex = (n: number) =>
  `${n.toLocaleString('pt-BR', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}×`;

export function Territory({
  cells,
  electorate,
  office,
  offices,
  onOfficeChange,
  seats,
}: {
  cells: Cell[];
  electorate: Record<string, number>;
  office: string;
  offices: string[];
  onOfficeChange: (office: string) => void;
  seats?: SeatReference;
}) {
  const domestic = cells.filter((c) => c.uf in electorate),
    total = sum(domestic, 'value');
  const population = Object.values(electorate).reduce((s, v) => s + v, 0);
  const ufValues = new Map(group(domestic, 'uf').map((r) => [r.name, r.value]));
  const totalSeats = seats
    ? Object.values(seats.byUf).reduce((a, b) => a + b, 0)
    : 0;
  const rows = Object.entries(electorate)
    .map(([uf, voters]) => {
      const value = ufValues.get(uf) || 0;
      const share = total ? (value / total) * 100 : 0;
      const electorateShare = (voters / population) * 100;
      const seatShare = seats?.byUf[uf]
        ? (seats.byUf[uf] / totalSeats) * 100
        : null;
      const seatIndex = seatShare ? share / seatShare : null;
      return {
        uf,
        voters,
        value,
        share,
        electorateShare,
        index: share / electorateShare,
        seatIndex,
        gap: share - electorateShare,
      };
    })
    .sort((a, b) => b.gap - a.gap);
  const hasSeats = Boolean(seats && totalSeats);
  const ranking = [...rows]
    .sort((a, b) =>
      hasSeats ? (b.seatIndex || 0) - (a.seatIndex || 0) : b.index - a.index,
    )
    .map((row) => ({
      ...row,
      plottedIndex: hasSeats ? row.seatIndex || 0 : row.index,
      region:
        Object.entries(regions).find(([, ufs]) => ufs.includes(row.uf))?.[0] ||
        '',
    }));
  const reference = hasSeats ? 'cadeiras em disputa' : 'eleitorado';
  return (
    <div className="view-content">
      <div className="section-line">
        <span>TERRITÓRIO & PESO ELEITORAL</span>
        <span>27 UFs · Presidência excluída</span>
      </div>
      {!hasSeats && (
        <div className="notice info">
          <CircleHelp size={17} />
          <div>
            <b>Compare com cadeiras em disputa</b>
            <span>
              Escolha um cargo abaixo. Com todos os cargos, o eleitorado é
              apenas uma referência descritiva.
            </span>
          </div>
          <label className="territory-office-picker">
            <span>Cargo</span>
            <select
              aria-label="Cargo para comparação territorial"
              value={office}
              onChange={(event) => onOfficeChange(event.target.value)}
            >
              <option value="Todos os cargos">Todos os cargos</option>
              {offices.map((value) => (
                <option value={value} key={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      <div className="territory-grid">
        <Panel
          title={
            hasSeats
              ? 'Onde o fundo pesa mais por cadeira'
              : 'Fundo em relação ao eleitorado'
          }
          subtitle={
            hasSeats
              ? `Índice: participação no fundo eleitoral ÷ participação nas cadeiras · cadeiras de ${seats?.year}`
              : 'Índice: participação no fundo eleitoral ÷ participação no eleitorado'
          }
        >
          <div className="territory-chart">
            <ResponsiveContainer width="100%" height={560}>
              <BarChart
                layout="vertical"
                data={ranking}
                margin={{ top: 8, right: 54, left: 8, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 5"
                  horizontal={false}
                  stroke="#eadfd2"
                />
                <XAxis
                  type="number"
                  domain={[0, (dataMax) => Math.max(1.5, Math.ceil(dataMax))]}
                  tickFormatter={(value) => `${value}×`}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#776b61' }}
                />
                <YAxis
                  type="category"
                  dataKey="uf"
                  width={34}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 13, fontWeight: 700, fill: '#2b2520' }}
                />
                <ReferenceLine
                  x={1}
                  stroke="#e94b20"
                  strokeWidth={2}
                  label={{
                    value: reference,
                    position: 'top',
                    fill: '#8e341d',
                    fontSize: 11,
                  }}
                />
                <Tooltip
                  cursor={{ fill: '#fff0e8' }}
                  formatter={(value, _name, item) => [
                    formatIndex(Number(value)),
                    `Fundo eleitoral ${money(Number(item.payload.value))} · ${item.payload.region}`,
                  ]}
                  labelFormatter={(label) => `UF: ${label}`}
                  contentStyle={{
                    borderRadius: 0,
                    border: '1px solid #241c17',
                    background: '#fffaf3',
                  }}
                />
                <Bar
                  dataKey="plottedIndex"
                  name="Índice territorial"
                  radius={[0, 4, 4, 0]}
                  barSize={13}
                >
                  {ranking.map((row) => (
                    <ChartCell
                      key={row.uf}
                      fill={
                        row.plottedIndex > 1.1
                          ? '#d9461d'
                          : row.plottedIndex < 0.9
                            ? '#d9cabc'
                            : '#f0a27f'
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="tile-legend">
            <span>
              <i className="above" /> Acima da referência
            </span>
            <span>
              <i className="balanced" /> Próximo da referência
            </span>
            <span>
              <i className="below" /> Abaixo da referência
            </span>
          </div>
        </Panel>
        <article className="territory-insight">
          <MapIcon />
          <div className="eyebrow">COMO LER O ÍNDICE</div>
          <h2>1,00×</h2>
          <p>
            {hasSeats
              ? 'significa que a fatia do fundo acompanha o peso da UF nas cadeiras em disputa.'
              : 'significa que a fatia do fundo acompanha o peso da UF no eleitorado.'}
          </p>
          <div className="insight-divider" />
          <strong>{money(total)}</strong>
          <p>destinados a candidaturas das 27 UFs no recorte.</p>
          <small>
            {money(
              sum(
                cells.filter((c) => c.uf === 'BR'),
                'value',
              ),
            )}{' '}
            em campanhas nacionais ficam fora desta comparação. Valores refletem
            o destino registrado da candidatura.
          </small>
        </article>
      </div>
      <Panel
        title="Distribuição por UF"
        subtitle="Ordenado pela diferença, em pontos percentuais, entre fundo e eleitorado"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>UF</TableHead>
              <TableHead className="numeric">FUNDO</TableHead>
              <TableHead className="numeric">FATIA DO FUNDO</TableHead>
              <TableHead className="numeric">ELEITORADO</TableHead>
              <TableHead className="numeric">DIFERENÇA</TableHead>
              <TableHead className="numeric">ÍNDICE</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.uf}>
                <TableCell>
                  <b>{r.uf}</b>
                </TableCell>
                <TableCell className="numeric">{money(r.value)}</TableCell>
                <TableCell className="numeric">{percent(r.share)}</TableCell>
                <TableCell className="numeric">
                  {percent(r.electorateShare)}
                </TableCell>
                <TableCell className="numeric">
                  {total
                    ? `${r.gap > 0 ? '+' : ''}${r.gap.toFixed(2)} pp`
                    : '—'}
                </TableCell>
                <TableCell className="numeric">
                  <span
                    className={`index-pill ${r.index >= 1 ? 'positive' : ''}`}
                  >
                    {total ? formatIndex(r.index) : '—'}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>
    </div>
  );
}
function MapIcon() {
  return (
    <div className="map-icon">
      <Network size={26} />
    </div>
  );
}

const human = (s: string) =>
  ({
    FEMININO: 'Mulheres',
    MASCULINO: 'Homens',
    PRETA: 'Pretas',
    PARDA: 'Pardas',
    BRANCA: 'Brancas',
    AMARELA: 'Amarelas',
    INDÍGENA: 'Indígenas',
    'NÃO INFORMADO': 'Não informado no cadastro',
    'NÃO DIVULGÁVEL': 'Não divulgado pelo TSE',
  })[s] || 'Sem categoria na base';
export function Representation({ cells }: { cells: Cell[] }) {
  const total = sum(cells, 'value'),
    candidates = sum(cells, 'candidates');
  const chart = (key: 'gender' | 'race') =>
    group(cells, key).map((g) => ({
      name: human(g.name),
      candidates: candidates ? (g.candidates / candidates) * 100 : 0,
      funds: total ? (g.value / total) * 100 : 0,
      value: g.value,
      n: g.candidates,
    }));
  const rows = (
    [
      ['Gênero', chart('gender')],
      ['Raça/cor', chart('race')],
    ] as const
  ).flatMap(([dimension, values]) =>
    values.map((value) => ({ ...value, dimension })),
  );
  return (
    <div className="view-content">
      <div className="section-line">
        <span>REPRESENTATIVIDADE</span>
        <span>Gênero e raça autodeclarados</span>
      </div>
      <div className="two-column">
        {(['gender', 'race'] as const).map((key) => (
          <Panel
            key={key}
            title={
              key === 'gender'
                ? 'Gênero: candidaturas e recursos'
                : 'Raça: candidaturas e recursos'
            }
            subtitle="Compare a participação no registro e no fundo recebido"
          >
            <div className="representation-chart">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={chart(key)}
                  layout="vertical"
                  margin={{ left: 5, right: 25, bottom: 10 }}
                >
                  <CartesianGrid horizontal={false} strokeDasharray="3 5" />
                  <XAxis
                    type="number"
                    unit="%"
                    tick={{ fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={145}
                    tick={{ fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip formatter={(v) => percent(Number(v))} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                  <Bar
                    dataKey="candidates"
                    name="Candidaturas"
                    fill="#cfc4b7"
                    radius={[0, 3, 3, 0]}
                    barSize={13}
                  />
                  <Bar
                    dataKey="funds"
                    name="Fundo eleitoral"
                    fill="#e94b20"
                    radius={[0, 3, 3, 0]}
                    barSize={13}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        ))}
      </div>
      <Panel
        title="Participação e diferença de alocação"
        subtitle="Diferença = percentual do fundo menos percentual de candidaturas"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>RECORTE</TableHead>
              <TableHead>GRUPO</TableHead>
              <TableHead className="numeric">CANDIDATURAS</TableHead>
              <TableHead className="numeric">FUNDO ELEITORAL</TableHead>
              <TableHead className="numeric">DIFERENÇA</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={`${r.dimension}-${r.name}`}>
                <TableCell>{r.dimension}</TableCell>
                <TableCell>{r.name}</TableCell>
                <TableCell className="numeric">
                  {percent(r.candidates)}
                </TableCell>
                <TableCell className="numeric">{percent(r.funds)}</TableCell>
                <TableCell className="numeric">
                  {(r.funds - r.candidates).toFixed(2)} pp
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="chart-note">
          “Não divulgado pelo TSE” e “não informado no cadastro” são categorias
          preservadas da fonte, não lacunas estimadas pelo painel. Não inferimos
          atributos autodeclarados. Comparação descritiva; diferenças não são,
          isoladamente, um veredito sobre cumprimento de cotas.
        </p>
      </Panel>
    </div>
  );
}

export function EfficiencyView({
  data,
  year,
  party,
  office,
}: {
  data: Dataset;
  year: string;
  party: string;
  office: string;
}) {
  const selectedOffice =
    office === 'Todos os cargos' ? 'DEPUTADO FEDERAL' : office;
  if (year === '2026')
    return (
      <div className="empty">
        <Vote size={34} />
        <h2>O resultado de 2026 ainda está em aberto</h2>
        <p>Selecione 2018 ou 2022 para comparar financiamento e votos.</p>
      </div>
    );
  if (
    !['DEPUTADO FEDERAL', 'DEPUTADO ESTADUAL', 'DEPUTADO DISTRITAL'].includes(
      selectedOffice,
    )
  )
    return (
      <div className="empty">
        <h2>Selecione um cargo proporcional</h2>
        <p>
          Esta comparação usa deputado federal, estadual ou distrital, todos com
          turno único.
        </p>
      </div>
    );
  const records = data.years[year].efficiency.filter(
    (r) =>
      r.office === selectedOffice &&
      (party === 'Todos os partidos' || r.party === party),
  );
  const grouped = new Map<
    string,
    { party: string; value: number; votes: number; candidates: number }
  >();
  for (const r of records) {
    const g = grouped.get(r.party) || {
      party: r.party,
      value: 0,
      votes: 0,
      candidates: 0,
    };
    g.value += r.value;
    g.votes += r.votes;
    g.candidates += r.candidates;
    grouped.set(r.party, g);
  }
  const rows = [...grouped.values()]
    .filter((r) => r.value > 0)
    .sort(
      (a, b) =>
        (a.votes ? a.value / a.votes : Infinity) -
        (b.votes ? b.value / b.votes : Infinity),
    );
  return (
    <div className="view-content">
      <div className="section-line">
        <span>FUNDO ELEITORAL POR VOTO</span>
        <span>{selectedOffice}</span>
      </div>
      <div className="notice info">
        <CircleHelp size={17} /> Com “Todos os cargos”, esta aba usa deputado
        federal para comparar disputas equivalentes. Valores nominais; não
        representam o custo total da campanha nem efeito causal do
        financiamento.
      </div>
      <Panel
        title="Quanto fundo corresponde a cada voto?"
        subtitle="Menor valor de fundo por voto primeiro · votos de legenda excluídos"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>PARTIDO</TableHead>
              <TableHead className="numeric">FUNDO ELEITORAL</TableHead>
              <TableHead className="numeric">VOTOS NOMINAIS</TableHead>
              <TableHead className="numeric">CANDIDATURAS</TableHead>
              <TableHead className="numeric">R$ / VOTO</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.party}>
                <TableCell>
                  <b>{r.party}</b>
                </TableCell>
                <TableCell className="numeric">{money(r.value)}</TableCell>
                <TableCell className="numeric">{number(r.votes)}</TableCell>
                <TableCell className="numeric">
                  {number(r.candidates)}
                </TableCell>
                <TableCell className="numeric">
                  <span className="index-pill positive">
                    {r.votes
                      ? `R$ ${(r.value / r.votes).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                      : 'Sem votos'}
                  </span>
                </TableCell>
              </TableRow>
            ))}
            {!rows.length && (
              <TableRow>
                <TableCell colSpan={5}>
                  Nenhuma candidatura neste recorte.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <p className="chart-note">
          Partidos sem repasse direto no recorte não entram na ordenação.
          Candidaturas sem votos continuam no numerador. Os resultados eleitorais
          podem refletir revisões posteriores do TSE; esta é a versão armazenada
          no projeto.
        </p>
      </Panel>
    </div>
  );
}

const profileName: Record<string, string> = {
  incumbente_mesmo_cargo: 'Incumbentes no mesmo cargo',
  eleito_outro_cargo: 'Eleitos em outro cargo',
  candidato_recorrente: 'Candidaturas recorrentes',
  novo_no_recorte: 'Novos no recorte',
  cpf_invalido: 'CPF inválido',
};
export function StrategyView({ data, year }: { data: Dataset; year: string }) {
  const current = data.years[year],
    concentration = [...current.concentration].sort((a, b) => b.gini - a.gini);
  if (!concentration.length)
    return (
      <div className="empty">
        <h2>Sem concentração comparável neste ciclo</h2>
        <p>
          Selecione outro ciclo para ver os partidos com ao menos R$ 20 milhões
          em fundo eleitoral.
        </p>
      </div>
    );
  return (
    <div className="view-content">
      <div className="section-line">
        <span>ESTRATÉGIA DE ALOCAÇÃO</span>
        <span>Concentração e renovação</span>
      </div>
      <div className="two-column">
        <Panel
          title="Quem concentra o fundo"
          subtitle="Gini alto = recursos mais concentrados entre candidaturas"
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>PARTIDO</TableHead>
                <TableHead className="numeric">GINI</TableHead>
                <TableHead className="numeric">TOP 10%</TableHead>
                <TableHead className="numeric">COBERTURA</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {concentration.slice(0, 10).map((r) => (
                <TableRow key={r.party}>
                  <TableCell>
                    <b>{r.party}</b>
                  </TableCell>
                  <TableCell className="numeric">
                    {r.gini.toLocaleString('pt-BR', {
                      minimumFractionDigits: 2,
                    })}
                  </TableCell>
                  <TableCell className="numeric">{percent(r.top10)}</TableCell>
                  <TableCell className="numeric">
                    {percent(r.coverage)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>
        <Panel
          title="Renovação no deputado federal"
          subtitle={
            year === '2018'
              ? 'Série começa em 2022'
              : `Comparação com o ciclo anterior`
          }
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>PERFIL</TableHead>
                <TableHead className="numeric">FUNDO</TableHead>
                <TableHead className="numeric">PARTICIPAÇÃO</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {current.renewal.map((r) => (
                <TableRow key={r.profile}>
                  <TableCell>{profileName[r.profile] || r.profile}</TableCell>
                  <TableCell className="numeric">{money(r.value)}</TableCell>
                  <TableCell className="numeric">{percent(r.share)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="chart-note">
            “Novo no recorte” significa ausência no ciclo imediatamente
            anterior, não estreia absoluta na política.
          </p>
        </Panel>
      </div>
    </div>
  );
}

export function FlowsView({
  data,
  year,
  party,
}: {
  data: Dataset;
  year: string;
  party: string;
}) {
  const rows = useMemo(() => {
    const grouped = new Map<
      string,
      { source: string; target: string; value: number }
    >();
    for (const r of data.years[year].flows) {
      if (
        party !== 'Todos os partidos' &&
        r.party !== party &&
        r.donorParty !== party
      )
        continue;
      const k = `${r.source}|${r.target}`;
      const g = grouped.get(k) || {
        source: r.source,
        target: r.target,
        value: 0,
      };
      g.value += r.value;
      grouped.set(k, g);
    }
    return [...grouped.values()]
      .filter((r) => r.value > 0)
      .sort((a, b) => b.value - a.value);
  }, [data, year, party]);
  const sources = [...new Set(rows.map((r) => r.source))],
    targets = [...new Set(rows.map((r) => r.target))];
  const nodes = [
    ...sources.map((name) => ({ name: `${name} →` })),
    ...targets.map((name) => ({ name: `→ ${name}` })),
  ];
  const links = rows.map((r) => ({
    source: sources.indexOf(r.source),
    target: sources.length + targets.indexOf(r.target),
    value: r.value,
  }));
  return (
    <div className="view-content">
      <div className="section-line">
        <span>CANAIS DE TRANSFERÊNCIA</span>
        <span>Todos os cargos · {party}</span>
      </div>
      <div className="notice info">
        <CircleHelp size={17} /> Este painel usa ciclo e partido; o filtro de
        cargo não se aplica. A largura dos fluxos representa receitas declaradas
        em cada etapa, que não devem ser somadas como recursos novos.
      </div>
      <Panel
        title="Da origem declarada ao destino"
        subtitle="Fluxos por esfera · selecione um partido para investigar seus canais"
      >
        <div className="sankey-head">
          <span>ORIGEM DECLARADA</span>
          <span>DESTINO DECLARADO</span>
        </div>
        <div className="sankey-chart">
          {rows.length ? (
            <ResponsiveContainer width="100%" height={400}>
              <Sankey
                data={{ nodes, links }}
                nodePadding={35}
                nodeWidth={12}
                margin={{ left: 20, right: 20, top: 10, bottom: 10 }}
                link={{ stroke: '#e94b20', strokeOpacity: 0.28 }}
                node={({
                  x,
                  y,
                  width,
                  height,
                  index,
                  payload,
                }: {
                  x: number;
                  y: number;
                  width: number;
                  height: number;
                  index: number;
                  payload: { name: string };
                }) => (
                  <g>
                    <rect
                      x={x}
                      y={y}
                      width={width}
                      height={height}
                      fill={index < sources.length ? '#241c17' : '#e94b20'}
                      rx={2}
                    />
                    <text
                      x={index < sources.length ? x + width + 9 : x - 9}
                      y={y + height / 2}
                      textAnchor={index < sources.length ? 'start' : 'end'}
                      dominantBaseline="middle"
                      fill="#332820"
                      fontSize={12}
                    >
                      {payload.name}
                    </text>
                  </g>
                )}
              >
                <Tooltip formatter={(v) => money(Number(v))} />
              </Sankey>
            </ResponsiveContainer>
          ) : (
            <div className="empty">Sem fluxos para o recorte.</div>
          )}
        </div>
      </Panel>
      <Panel
        title="Volumes por canal"
        subtitle="Inclui auto-receitas declaradas; não presume que representam entradas novas do Tesouro"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ORIGEM</TableHead>
              <TableHead>DESTINO</TableHead>
              <TableHead className="numeric">RECEITAS DECLARADAS</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={`${r.source}|${r.target}`}>
                <TableCell>{r.source}</TableCell>
                <TableCell>{r.target}</TableCell>
                <TableCell className="numeric">{money(r.value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="chart-note">
          “Não identificada” significa ausência de esfera partidária no
          registro; pode incluir doadores de outra natureza e repasses de
          candidaturas. O diagrama agrega canais e não rastreia cada real ao
          longo de uma cadeia.
        </p>
      </Panel>
    </div>
  );
}

export function Method({ data }: { data: Dataset }) {
  return (
    <div className="view-content">
      <div className="section-line">
        <span>TRANSPARÊNCIA & REPRODUÇÃO</span>
        <span>Dados públicos, método aberto</span>
      </div>
      <div className="method-grid">
        {[
          [
            '01',
            'Qual dinheiro estamos medindo?',
            'FEFC registrado como FUNDO ESPECIAL nas receitas das candidaturas, excluindo a origem “Recursos de outros candidatos”. Não inclui o Fundo Partidário nem todos os gastos de campanha.',
          ],
          [
            '02',
            'Como os filtros funcionam?',
            'Ciclo, partido e cargo filtram os indicadores de alocação. Território usa apenas as 27 UFs. Eficiência usa cargos proporcionais; na ausência de cargo, deputado federal. Fluxos usa apenas ciclo e partido.',
          ],
          [
            '03',
            'O que significa a referência territorial?',
            'Com um cargo selecionado, o índice principal divide a fatia da UF no fundo pela sua fatia nas cadeiras em disputa; isso separa o desenho constitucional da escolha partidária. Sem um cargo único, o painel mostra apenas a referência descritiva do eleitorado. BR e exterior ficam fora.',
          ],
          [
            '04',
            'Como interpretar raça e gênero?',
            'As categorias são autodeclaradas ao TSE. Pretas e pardas formam o agregado de pessoas negras. O painel é descritivo e não substitui auditoria jurídica de cotas ou despesas compartilhadas.',
          ],
          [
            '05',
            'E as comparações entre anos?',
            'Valores nominais, sem ajuste por inflação. Siglas não são harmonizadas por fusões ou incorporações, exceto PC do B/PCDOB. 2026 é prestação parcial. Ausência de uma sigla em um ciclo não significa financiamento zero de seus antecessores.',
          ],
          [
            '06',
            'De onde vêm os números?',
            'Parquet público do projeto, originado nos arquivos do TSE. Eleitorado, votos e cadeiras são dimensões derivadas e publicadas no mesmo dataset. Apenas agregados são enviados ao navegador, sem nomes ou documentos de candidaturas.',
          ],
        ].map(([n, title, text]) => (
          <article key={n} className="method-card">
            <span>{n}</span>
            <h2>{title}</h2>
            <p>{text}</p>
          </article>
        ))}
      </div>
      <div className="source-links">
        <div>
          <b>Uma fotografia dos dados</b>
          <p>
            Exportação: {new Date(data.generatedAt).toLocaleString('pt-BR')}.
            Atualizações do TSE exigem uma nova exportação.
          </p>
        </div>
        <a
          href="https://dadosabertos.tse.jus.br/"
          target="_blank"
          rel="noreferrer"
        >
          Portal do TSE <ArrowUpRight size={16} />
        </a>
        <a
          href="https://github.com/araujovito/fundo-eleitoral-br"
          target="_blank"
          rel="noreferrer"
        >
          Código e metodologia <ArrowUpRight size={16} />
        </a>
        <a href="/data.json" download="fundo-eleitoral-agregados.json">
          Baixar os agregados <ArrowDownToLine size={16} />
        </a>
      </div>
    </div>
  );
}
