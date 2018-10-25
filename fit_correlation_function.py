from argparse import ArgumentParser
from csv import writer, QUOTE_MINIMAL

from plots import do_eff_mass_plot, do_correlator_plot
from data import get_target_correlator
from bootstrap import bootstrap_correlators, bootstrap_eff_masses
from fitting import minimize_chisquare, ps_fit_form, ps_av_fit_form


def get_output_filename(basename, type, channel='', tstart='', tend='',
                        filetype='pdf'):
    if channel:
        channel = f'_{channel}'
    if tstart:
        tstart = f'_{tstart}'
    if tend:
        tend = f'_{tend}'
    if tstart and not tend:
        tend = '_XX'
    if tend and not tstart:
        tstart = '_XX'

    return f'{basename}{type}{channel}{tstart}{tend}.{filetype}'


class Incomplete(Exception):
    pass


def process_correlator(
        correlator_filename,
        channel_name, channel_set, channel_latexes, symmetries,
        correlator_names, fit_forms, NT, NS, parameter_ranges,
        ensemble_selection=0,
        initial_configuration=0, configuration_separation=1,
        bootstrap_sample_count=200, plateau_start=None, plateau_end=None,
        eff_mass_plot_ymin=None, eff_mass_plot_ymax=None,
        correlator_lowerbound=None, correlator_upperbound=None,
        optimizer_intensity='default', output_filename_prefix=''
):
    target_correlators = get_target_correlator(
        correlator_filename, channel_set, NT, NS, symmetries,
        ensemble_selection, initial_configuration, configuration_separation
    )

    (bootstrap_mean_correlators, bootstrap_error_correlators,
     bootstrap_correlator_samples_set) = bootstrap_correlators(
         target_correlators, bootstrap_sample_count
     )

    bootstrap_mean_eff_masses, bootstrap_error_eff_masses = (
        bootstrap_eff_masses(bootstrap_correlator_samples_set)
    )

    do_eff_mass_plot(
        bootstrap_mean_eff_masses[0],
        bootstrap_error_eff_masses[0],
        get_output_filename(output_filename_prefix, 'effmass', channel_name),
        ymin=eff_mass_plot_ymin,
        ymax=eff_mass_plot_ymax
    )

    for correlator_name, channel_latex, \
            bootstrap_mean_correlator, bootstrap_error_correlator in zip(
            correlator_names,
            channel_latexes,
            bootstrap_mean_correlators,
            bootstrap_error_correlators
            ):
        do_correlator_plot(
            bootstrap_mean_correlator,
            bootstrap_error_correlator,
            get_output_filename(output_filename_prefix, 'correlator',
                                correlator_name),
            channel_latex
        )

    if not (plateau_start and plateau_end):
        raise Incomplete(
            "Effective mass plot has been generated. "
            "Now specify the start and end of the plateau to perform the fit."
        )

    fit_results, (chisquare_value, chisquare_error) = minimize_chisquare(
        bootstrap_correlator_samples_set,
        bootstrap_mean_correlators,
        fit_forms,
        parameter_ranges,
        plateau_start,
        plateau_end,
        NT,
        fit_means=True,
        intensity=optimizer_intensity
    )
    fit_result_values = tuple(fit_result[0] for fit_result in fit_results)

    for correlator_name, channel_latex, fit_form, \
            bootstrap_mean_correlator, bootstrap_error_correlator in zip(
                correlator_names,
                channel_latexes,
                fit_forms,
                bootstrap_mean_correlators,
                bootstrap_error_correlators
            ):
        do_correlator_plot(
            bootstrap_mean_correlator,
            bootstrap_error_correlator,
            get_output_filename(output_filename_prefix,
                                'centrally_fitted_correlator',
                                channel=channel_name,
                                tstart=plateau_start,
                                tend=plateau_end),
            channel_latex,
            fit_function=fit_form,
            fit_params=(*fit_result_values, NT),
            fit_legend='Fit of central values',
            t_lowerbound=plateau_start - 3.5,
            t_upperbound=plateau_end - 0.5,
            corr_upperbound=correlator_upperbound,
            corr_lowerbound=correlator_lowerbound
        )

    fit_results, (chisquare_value, chisquare_error) = minimize_chisquare(
        bootstrap_correlator_samples_set,
        bootstrap_mean_correlators,
        fit_forms,
        parameter_ranges,
        plateau_start,
        plateau_end,
        NT,
        fit_means=False
    )
    (mass, mass_error), *_ = fit_results

    do_eff_mass_plot(
        bootstrap_mean_eff_masses[0],
        bootstrap_error_eff_masses[0],
        get_output_filename(output_filename_prefix,
                            'effmass_withfit',
                            channel=channel_name,
                            tstart=plateau_start,
                            tend=plateau_end),
        ymin=eff_mass_plot_ymin,
        ymax=eff_mass_plot_ymax,
        m=mass,
        m_error=mass_error,
        tmin=plateau_start - 0.5,
        tmax=plateau_end - 0.5
    )

    return fit_results, (chisquare_value, chisquare_error)


def write_results(filename, channel_name, headers, values):
    with open(filename, 'w', newline='') as csvfile:
        csv_writer = writer(csvfile, delimiter='\t', quoting=QUOTE_MINIMAL)
        csv_writer.writerow((f'{channel_name}_{header}'
                             for header in headers))
        csv_writer.writerow((value
                      for value_pair in values
                      for value in value_pair))


def main():
    parser = ArgumentParser()

    parser.add_argument('--correlator_filename', required=True)
    parser.add_argument('--channel', choices=('g5',), required=True)
    parser.add_argument('--NT', required=True, type=int)
    parser.add_argument('--NS', required=True, type=int)
    parser.add_argument('--configuration_separation', default=1, type=int)
    parser.add_argument('--initial_configuration', default=0, type=int)
    # ensemble_selection can range from 0 to configuration_separation
    parser.add_argument('--ensemble_selection', default=0, type=int)
    parser.add_argument('--bootstrap_sample_count', default=200, type=int)
    parser.add_argument('--silent', action='store_true')
    parser.add_argument('--eff_mass_plot_ymin', default=None, type=float)
    parser.add_argument('--eff_mass_plot_ymax', default=None, type=float)
    parser.add_argument('--plateau_start', default=None, type=int)
    parser.add_argument('--plateau_end', default=None, type=int)
    parser.add_argument('--correlator_lowerbound', default=0.0, type=float)
    parser.add_argument('--correlator_upperbound', default=None, type=float)
    parser.add_argument('--optimizer_intensity', default='default',
                        choices=('default', 'intense'))
    parser.add_argument('--output_filename_prefix', default=None)
    args = parser.parse_args()

    if not args.output_filename_prefix:
        args.output_filename_prefix = args.correlator_filename + '_'

    channel_name = args.channel

    channel_set_options = {
        'g5': (('g5',), ('g5_g0g5_re',))
    }
    correlator_names_options = {
        'g5': ('g5', 'g5_g0g5_re')
    }
    channel_latexes_options = {
        'g5': (r'\gamma_5,\gamma_5', '\gamma_0\gamma_5,\gamma_5')
    }
    fit_forms_options = {
        'g5': (ps_fit_form, ps_av_fit_form)
    }
    symmetries_options = {
        'g5': (+1, -1)
    }
    parameter_range_options = {
        'g5': ((0.01, 5), (0, 5), (0, 5))
    }
    output_file_header_options = {
        'g5': ('mass', 'mass_error', 'decay_const', 'decay_const_error',
               'amplitude', 'amplitude_error', 'chisquare', 'chisquare_error')
    }

    channel_set = channel_set_options[channel_name]
    correlator_names = correlator_names_options[channel_name]
    channel_latexes = channel_latexes_options[channel_name]
    fit_forms = fit_forms_options[channel_name]
    symmetries = symmetries_options[channel_name]
    parameter_ranges = parameter_range_options[channel_name]

    try:
        fit_results = process_correlator(
            args.correlator_filename,
            channel_name, channel_set, channel_latexes, symmetries,
            correlator_names, fit_forms, args.NT, args.NS,
            bootstrap_sample_count=args.bootstrap_sample_count,
            configuration_separation=args.configuration_separation,
            initial_configuration=args.initial_configuration,
            eff_mass_plot_ymin=args.eff_mass_plot_ymin,
            eff_mass_plot_ymax=args.eff_mass_plot_ymax,
            plateau_start=args.plateau_start,
            plateau_end=args.plateau_end,
            ensemble_selection=args.ensemble_selection,
            correlator_lowerbound=args.correlator_lowerbound,
            correlator_upperbound=args.correlator_upperbound,
            optimizer_intensity=args.optimizer_intensity,
            output_filename_prefix=args.output_filename_prefix,
            parameter_ranges=parameter_ranges
        )

    except Incomplete as ex:
        print("ANALYSIS NOT YET COMPLETE")
        print(ex.desc)
    else:
        mass, mass_error = fit_results[0][0]
        decay_const, decay_const_error = fit_results[0][1]
        if len(fit_results[0]) > 2:
            amplitude, amplitude_error = fit_results[0][2]
        chisquare_value, chisquare_error = fit_results[1]

        write_results(
            filename=get_output_filename(
                args.output_filename_prefix, 'mass', channel_name,
                filetype='dat'
            ),
            channel_name=channel_name,
            headers=output_file_header_options[channel_name],
            values=(*fit_results[0], fit_results[1])
        )
        if not args.silent:
            print(f'{channel_name} mass: {mass} ± {mass_error}')
            print(f'{channel_name} amplitude: '
                  f'{amplitude} ± {amplitude_error}')
            if len(fit_results[0]) > 2:
                print(f'{channel_name} decay constant: '
                      f'{decay_const} ± {decay_const_error}')
            print(f'{channel_name} chi-square: '
                  f'{chisquare_value} ± {chisquare_error}')


if __name__ == '__main__':
    main()
