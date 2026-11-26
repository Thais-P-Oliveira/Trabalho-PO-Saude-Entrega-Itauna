"""Exporta a formulacao APS para MathProg com os mesmos dados do modelo Python."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from caminhos import RAIZ, MODELOS, resolver_caminho_plano
sys.path.insert(0, str(MODELOS))
import aps_base as aps
from pessoal_cnes import por_site


def escrever(destino, dem, sites, dist, args, fase, alvo, operacao, investimento):
    limites = aps.limites_equipes(sites, args)
    acs = aps.acs_atuais(sites, args) if args.preservar_acs_atuais else {}
    pessoal = por_site(sites, args, aps.CUSTO, aps.CUSTO_ESF, limites)
    novas = [j for j, s in sites.iterrows() if not s.existente]
    raios = aps.raios_por_ponto(dem, args)
    linhas = ['data;', 'set I := ' + ' '.join(f'i{i}' for i in range(len(dem))) + ';',
              'set J := ' + ' '.join(f'j{j}' for j in range(len(sites))) + ';',
              'set C := ' + ' '.join(f'j{j}' for j in novas) + ';']
    for j, s in sites.iterrows():
        linhas.append(f'# j{j}: {s.id} - {s.nome}')
    def parametro(nome, valores):
        linhas.append('param ' + nome + ' :=\n' + '\n'.join(
            f'{k} {float(v):.17g}' for k, v in valores) + '\n;')
    parametro('pop', ((f'i{i}', r.pessoas) for i, r in dem.iterrows()))
    for nome, valores in [('emin', {j:v[0] for j,v in limites.items()}),
                          ('emax', {j:v[1] for j,v in limites.items()}),
                          ('acs0', {j:acs.get(j,0) for j in range(len(sites))}),
                          ('fixo', sites.fixo.to_dict()), ('pessoal', pessoal)]:
        parametro(nome, ((f'j{j}', v) for j,v in valores.items()))
    parametro('minimo', ((f'j{j}', aps.minimo_nova(sites.iloc[j],dem,args)) for j in novas))
    parametro('obra', ((k,v) for k,v in aps.precos_construcao().items() if k <= 4))
    for nome, valores in [('dist', dist), ('cob', dist <= raios[:,None]+1e-9)]:
        linhas.append('param ' + nome + ' :=\n' + '\n'.join(
            f'i{i} j{j} {float(valores[i,j]):.17g}'
            for i in range(len(dem)) for j in range(len(sites))) + '\n;')
    comprometido = 12*sum(sites.iloc[j].fixo+pessoal[j]+aps.CUSTO['acs']*acs.get(j,0)
                          for j in range(len(sites)) if sites.iloc[j].existente)
    orcamento = args.orcamento_ap_anual
    disponivel = 0 if orcamento is None else (orcamento-comprometido-
        args.reserva_moveis_anual-args.comprometimento_adicional_anual)
    escalares = dict(hab_esf=args.hab_esf, hab_acs=aps.HAB_POR_ACS,
        custo_esf=aps.CUSTO_ESF, custo_acs=aps.CUSTO['acs'], custo_km=args.custo_km,
        meses=12*args.horizonte_anos, max_novas=len(novas) if args.max_novas is None else args.max_novas,
        usar_orcamento=int(orcamento is not None), disponivel_anual=disponivel,
        fase=fase, alvo=alvo, operacao_referencia=operacao,
        obra_referencia=investimento, folga=args.folga_custo or 0)
    linhas += [f'param {k} := {float(v):.17g};' for k,v in escalares.items()]
    destino.write_text('\n'.join(linhas)+'\nend;\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plano', type=Path, default=RAIZ/'resultados/atual/plano/plano_aps.json')
    p.add_argument('--saida', type=Path, default=MODELOS/'dados')
    p.add_argument('--resolver', action='store_true', help='resolve as fases em sequencia e atualiza suas referencias')
    p.add_argument('--time-limit', type=int, default=600)
    a = p.parse_args()
    plano = json.loads(a.plano.read_text(encoding='utf-8'))
    parametros = dict(plano['parametros'])
    for chave in ['demanda','ubs','limites_equipes','growth_file']:
        if parametros.get(chave): parametros[chave] = resolver_caminho_plano(parametros[chave])
    args = SimpleNamespace(**parametros)
    dem, _, sites, dist = aps.carregar_dados(args)
    a.saida.mkdir(parents=True, exist_ok=True)
    alvo = plano['cobertura']-1e-4
    operacao = plano['custos']['fase2']['operacional_mensal']
    investimento = plano['custos']['fase2']['investimento']
    for fase in [1,2,3]:
        dat = a.saida/f'aps_fase{fase}.dat'
        escrever(dat,dem,sites,dist,args,fase,alvo,operacao,investimento)
        if a.resolver:
            solver = shutil.which('glpsol')
            if not solver: raise FileNotFoundError('Instale GLPK e adicione glpsol ao PATH.')
            r = subprocess.run([solver,'-m',str(MODELOS/'aps.mod'),'-d',str(dat),
                '--tmlim',str(a.time_limit),'--mipgap',str(args.gap)],
                capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
            if 'INTEGER OPTIMAL SOLUTION FOUND' not in r.stdout:
                raise RuntimeError('Fase sem otimo comprovado; as referencias seguintes nao foram atualizadas.')
            resumo = next(l for l in r.stdout.splitlines() if l.startswith('RESUMO;')).split(';')
            if fase == 1: alvo = float(resumo[1])-1e-4
            if fase == 2: operacao,investimento = map(float,resumo[2:4])
            print(r.stdout)
    print('Dados APS exportados para', a.saida)


if __name__ == '__main__':
    main()
