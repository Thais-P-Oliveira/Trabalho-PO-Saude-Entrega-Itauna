"""Estimativa de pessoal a partir das horas CNES; nao representa folha paga."""
import pandas as pd
from caminhos import BASE
from tabelas import ler_tabela

CATEGORIAS = {'medico': 'medicos', 'enfermeiro': 'enfermeiros',
              'tecnico': 'tecnicos_enfermagem', 'auxiliar': 'auxiliares_enfermagem'}

def cadastro():
    return ler_tabela(BASE/'fontes_publicas/ubs_recursos_cnes_202607.xlsx', sep=';', dtype={'cnes':str})

def estimar(linha, custos, horas_referencia=40):
    # Uma remuneracao de referencia equivale a 40 horas semanais.
    # Cada categoria possui remuneracao propria.
    return sum(float(linha[prefixo+'_horas_cadastradas'])/horas_referencia *
               custos[categoria]
               for categoria,prefixo in CATEGORIAS.items())

def por_site(sites,args,custos,custo_esf,limites):
    # Testes sinteticos sem preservacao do cadastro mantem seus custos de entrada.
    if not getattr(args,'preservar_acs_atuais',True):
        return {j:custo_esf*limites[j][0] for j in range(len(sites))}
    ids=ler_tabela(args.ubs,dtype={'cnes':str}).set_index('j').cnes.to_dict()
    rec=cadastro().set_index('cnes')
    saida={}
    for j,s in sites.iterrows():
        if not s['existente']:
            saida[j]=0.;continue
        c=ids[int(str(s['id'])[3:])]
        saida[j]=estimar(rec.loc[c],custos)
    return saida

def total_atual(custos):
    return sum(estimar(r,custos) for _,r in cadastro().iterrows())
