import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { group, selectCells, sum, money, percent, type Dataset } from '../lib/data.ts';

const data = JSON.parse(readFileSync(new URL('../public/data.json', import.meta.url), 'utf8')) as Dataset;
void test('snapshot reconciles with the published direct FEFC totals', () => {
  for (const [year, expected] of Object.entries({'2018':1693986475.42,'2022':4741151841.03,'2026':4610565650.36})) {
    const cells = selectCells(data,year,'Todos os partidos','Todos os cargos');
    assert.ok(Math.abs(sum(cells,'value')-expected)<1);
    assert.ok(Math.abs(group(cells,'party').reduce((s,c)=>s+c.value,0)-expected)<1);
    assert.equal(Object.keys(data.years[year].electorate).length,27);
    assert.ok(cells.every(c=>c.funded<=c.candidates));
  }
});
void test('filters compose and do not leak another party or office', () => {
  const cells=selectCells(data,'2022','PDT','DEPUTADO FEDERAL');
  assert.ok(cells.length>0);
  assert.ok(cells.every(c=>c.party==='PDT' && c.office==='DEPUTADO FEDERAL'));
  assert.equal(group(cells,'party').length,1);
  assert.equal(selectCells(data,'2022','INEXISTENTE','Todos os cargos').length,0);
});
void test('snapshot contains aggregates only and no 2026 vote result', () => {
  const text=readFileSync(new URL('../public/data.json',import.meta.url),'utf8');
  for(const field of ['sq_candidato','nr_cpf','nr_cnpj','nm_candidato']) assert.ok(!text.includes(field));
  assert.equal(data.years['2026'].efficiency.length,0);
});
void test('empty values remain readable',()=>{assert.equal(percent(NaN),'0%');assert.equal(money(0),'R$ 0');});
