from ..tables import generate_table_from_db

ENSEMBLES = (
    'DB1M1', 'DB1M2', 'DB1M3', 'DB1M4', 'DB1M5', 'DB1M6',
    None,
    'DB2M1', 'DB2M2', 'DB2M3',
    None,
    'DB3M1', 'DB3M2', 'DB3M3', 'DB3M4', 'DB3M5', 'DB3M6', 'DB3M7', 'DB3M8',
    None,
    'DB4M1', 'DB4M2',
    None,
    'DB5M1'
)
ERROR_DIGITS = 2
EXPONENTIAL = False


def generate(data):
    columns = ['', None, r'$am_{\mathrm{PS}}$', r'$af_{\mathrm{PS}}$',
               r'$am_{\mathrm{S}}$', None,
               r'$m_{\mathrm{PS}}L$', r'$f_{\mathrm{PS}}L$']
    observables = ('g5_mass', 'g5_decay_const', 'id_mass',
                   'mPS_L', 'fPS_L')
    filename = 'table5.tex'

    for ensemble in ENSEMBLES:
        for source, dest in (('mass', 'mPS_L'), ('decay_const', 'fPS_L')):
            datum = data[(data.label == ensemble) &
                         (data.observable == f'g5_{source}')].copy()
            datum.observable = dest
            datum.value = datum.L * datum.value
            datum.uncertainty = datum.L * datum.uncertainty
            data = data.append(datum)

    generate_table_from_db(
        data=data,
        ensembles=ENSEMBLES,
        observables=observables,
        filename=filename,
        columns=columns,
        error_digits=ERROR_DIGITS,
        exponential=EXPONENTIAL
    )
