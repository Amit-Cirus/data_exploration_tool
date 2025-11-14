import argparse

from loguru import logger as log

from dash_bootstrap_templates import load_figure_template

from src.logic.exceptions import AppException
from src.logic.factory import create_data_object, get_defaults

from src.data_loaders.keter_data_loader import get_pipeline_versions
from src.data_loaders.keter_raw_data import get_machines, get_machine_names
from src.logic.initialization import initialize_app

load_figure_template("bootstrap")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sensorial Inspector Tool")
    parser.add_argument("--customer", type=str, default="Keter")
    parser.add_argument("--test_machine", type=str, default="2-10051164")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--debug", action='store_true')
    parser.add_argument("--read_files_multi", action='store_true')

    args = parser.parse_args()
    test_machine = args.test_machine
    log.debug(f'Test machine: {test_machine}')

    only_manual_mode = False
    try:
        all_machines = get_machines()
        machine_names = get_machine_names(all_machines)
        pipeline_versions_options = get_pipeline_versions()
    except AppException as e:
        log.error(f'[SWITCHING TO MANUAL AND DEFAULTS ONLY] Please verify DB connection: {e}')
        defaults = get_defaults()
        all_machines = defaults['all_machines']
        pipeline_versions_options = defaults['pipeline_versions_options']
        machine_names = defaults['machine_names']
        only_manual_mode = defaults['only_manual_mode']

    machine_ids_str = [str(machine_idx) for machine_idx in list(all_machines.keys())]

    data_object = create_data_object(
        all_machines=all_machines,
        machine_ids_str=machine_ids_str,
        args=args,
        pipeline_versions_options=pipeline_versions_options
    )

    dash_app = initialize_app(
        customer_name=args.customer,
        machines=machine_names,
        selected_machine=test_machine,
        data_object=data_object,
        only_manual_mode=only_manual_mode
    )

    dash_app.run(debug=args.debug, port=args.port, use_reloader=False)
