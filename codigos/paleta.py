"""Cores por significado, compartilhadas pelos mapas e graficos."""
EXISTENTE = '#969696'
URBANA = '#7030A0'
RURAL = '#D97706'
MOVEL = '#008060'
NO_RAIO = '#2878B5'
FORA_RAIO = '#C43C39'
ATUAL = '#52627A'
PROPOSTA = '#16789A'


def cor_ubs(status, nome):
    if status != 'NOVA':
        return EXISTENTE
    return RURAL if '(rural)' in str(nome).lower() else URBANA
