import yaml

from argparse import ArgumentParser
from os import listdir
from importlib import import_module
from datetime import datetime
from os.path import getmtime

from .db import is_complete_descriptor, describe_ensemble, get_dataframe

from .w0 import plot_measure_and_save_w0
from .t0 import plot_measure_and_save_sqrt_8t0
from .Q import plot_measure_and_save_Q
from .avr_plaquette import measure_and_save_avr_plaquette
from .fit_correlation_function import plot_measure_and_save_mesons, Incomplete


DEBUG = True


def get_file_contents(filename):
    with open(filename, 'r') as f:
        return f.read()


def get_subdirectory_name(descriptor):
    return 'nf{Nf}{rep_suffix}/{T}x{L}x{L}x{L}b{beta}{m_suffix}'.format(
        Nf=descriptor['Nf'],
        L=descriptor['L'],
        T=descriptor['T'],
        beta=descriptor['beta'],
        m_suffix=f'm{descriptor["m"]}' if 'm' in descriptor else '',
        rep_suffix=(f'_{descriptor["representation"]}'
                    if 'representation' in descriptor else '')
    )


def do_single_analysis(label, ensemble,
                       ensembles_date=datetime.now,
                       skip_mesons=False):
    ensemble['descriptor'] = describe_ensemble(ensemble, label)
    subdirectory = get_subdirectory_name(ensemble['descriptor'])

    if DEBUG:
        print("Processing", subdirectory)

    if ensemble.get('measure_gflow', False):
        # Gradient flow: w0
        if DEBUG:
            print("  - w0")
        result = plot_measure_and_save_w0(
            W0=0.35,
            simulation_descriptor=ensemble['descriptor'],
            filename=f'raw_data/{subdirectory}/out_wflow',
            plot_filename=(
                f'processed_data/{subdirectory}/flows.pdf'
            )
        )
        if result and DEBUG:
            w0p, w0c = result
            print("    w0p:", w0p, "w0c:", w0c)
        elif DEBUG:
            print("    Already up to date")

        if ensemble['beta'] == 7.2:
            # Generate extra W0 values for figure 1
            # Could be made more efficient by splitting
            # `plot_measure_and_save_w0` into two functions
            for W0 in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0):
                result = plot_measure_and_save_w0(
                    W0=W0,
                    simulation_descriptor=ensemble['descriptor'],
                    filename=f'raw_data/{subdirectory}/out_wflow',
                )
                if result and DEBUG:
                    w0p, w0c = result
                    print("    W0:", W0, "| w0p:", w0p, "w0c:", w0c)
                elif DEBUG:
                    print("    W0:", W0, "also already up to date")

        # Gradient flow: t0
        if DEBUG:
            print("  - t0")
        result = plot_measure_and_save_sqrt_8t0(
            E0=0.35,
            simulation_descriptor=ensemble['descriptor'],
            filename=f'raw_data/{subdirectory}/out_wflow',
            plot_filename=(
                f'processed_data/{subdirectory}/flows_t0.pdf'
            )
        )
        if result and DEBUG:
            s8t0p, s8t0c = result
            print("    sqrt(8t0p):", s8t0p, "sqrt(8t0c):", s8t0c)
        elif DEBUG:
            print("    Already up to date")

        if ensemble['beta'] == 7.2:
            # Generate extra E0 values for figure 1
            # Could be made more efficient by splitting
            # `plot_measure_and_save_w0` into two functions
            for E0 in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0):
                result = plot_measure_and_save_sqrt_8t0(
                    E0=E0,
                    simulation_descriptor=ensemble['descriptor'],
                    filename=f'raw_data/{subdirectory}/out_wflow',
                )
                if result and DEBUG:
                    s8t0p, s8t0c = result
                    print("    E0:", E0, "| sqrt(8t0p):", s8t0p,
                          "sqrt(8t0c):", s8t0c)
                elif DEBUG:
                    print("    E0:", E0, "also already up to date")

        # Gradient flow: Q
        if DEBUG:
            print("  - Q")
        result = plot_measure_and_save_Q(
            simulation_descriptor=ensemble['descriptor'],
            flows_file=f'raw_data/{subdirectory}/out_wflow',
            output_file=f'processed_data/{subdirectory}/Q.pdf'
        )
        if result and DEBUG:
            print("    {}".format(
                ' '.join([f'{k}: {v}' for k, v in result.items()])
            ))
        else:
            print("    Already up to date")

    if ensemble.get('measure_plaq', False):
        # HMC history: plaquette
        if DEBUG:
            print("  - Plaquette")
        result = measure_and_save_avr_plaquette(
            simulation_descriptor=ensemble['descriptor'],
            filename=f'raw_data/{subdirectory}/out_hmc',
        )
        if result and DEBUG:
            plaq, Zv, Zav = result
            print('    plaq:', plaq, 'Zv:', Zv, 'Zav:', Zav)
        elif DEBUG:
            print('    Already up to date')

    if ensemble.get('measure_mesons', False) and not skip_mesons:
        # Mesonic observables
        for (channel_name,
             channel_parameters) in ensemble['measure_mesons'].items():
            if DEBUG:
                print(f"  - Mesons, {channel_name}")
            try:
                result = plot_measure_and_save_mesons(
                    simulation_descriptor=ensemble['descriptor'],
                    correlator_filename=f'raw_data/{subdirectory}/out_corr',
                    channel_name=channel_name,
                    meson_parameters=channel_parameters,
                    parameter_date=ensembles_date
                )
            except Incomplete as ex:
                print(f'    INCOMPLETE: {ex.message}')
            else:
                if result and DEBUG:
                    print('   ', result)
                else:
                    print('    Already up to date')


def do_analysis(ensembles, **kwargs):
    for label, ensemble in ensembles.items():
        do_single_analysis(label, ensemble, **kwargs)


def output_results(only=None):
    data = get_dataframe()

    for object_type in ('table', 'plot'):
        objects = [import_module(f'autospn.{object_type}_specs.' + module[:-3])
                   for module in listdir(f'autospn/{object_type}_specs')
                   if module[-3:] == '.py' and module[0] != '.']

        for object in objects:
            if '__' in object.__name__:
                continue
            if only and only not in object.__name__:
                continue
            try:
                print(f'Generating for {object.__name__}')
                object.generate(data)
            except AttributeError as ex:
                if "has no attribute 'generate'" in str(ex):
                    print(
                        f'Module {object.__name__} has no generate function.'
                    )
                else:
                    raise ex


def main():
    parser = ArgumentParser()
    parser.add_argument('--ensembles', default='ensembles.yaml')
    parser.add_argument('--skip_mesons', action='store_true')
    parser.add_argument('--skip_calculation', action='store_true')
    parser.add_argument('--only', default=None)
    args = parser.parse_args()

    ensembles = yaml.safe_load(get_file_contents(args.ensembles))
    ensembles_date = datetime.fromtimestamp(getmtime(args.ensembles))

    ensembles = {
        label: ensemble
        for label, ensemble in ensembles.items()
        if is_complete_descriptor(ensemble)
    }

    if args.skip_calculation or args.only:
        print("Skipping calculation as requested")
    else:
        do_analysis(ensembles,
                    ensembles_date=ensembles_date,
                    skip_mesons=args.skip_mesons,
                    only=args.only)

    print("Outputting results:")
    output_results(args.only)


if __name__ == '__main__':
    main()
