from typing import Dict

from benedict import benedict


def create_data_object(all_machines, machine_ids_str, args, pipeline_versions_options) -> benedict:
    data_object = {
        "machines": all_machines,
        "data_sources_values": dict.fromkeys(machine_ids_str),
        "data_sources_metadata": dict.fromkeys(machine_ids_str),
        "algo": {'predicted_events': dict.fromkeys(machine_ids_str),
                 'reconstruction': dict.fromkeys(machine_ids_str),
                 },
        "events": dict.fromkeys(machine_ids_str),
        "configurations":
            {
                "reading_files_multi": args.read_files_multi,
                "pipeline_versions_options": pipeline_versions_options,
                "pipeline_versions":
                    {
                        "stats_pipe_version": pipeline_versions_options["stats_pipe_options"][0],
                        "labeled_events_pipe_version": pipeline_versions_options["labeled_events_pipe_options"][0],
                        "training_pipe_version": pipeline_versions_options["training_pipe_options"][0],
                        "events_pipe_version": pipeline_versions_options["events_pipe_options"][0],
                    },
                "time_configurations":
                    {
                        "show_before_event": 3,
                        "show_after_event": 1
                    },
                "events_configurations":
                    {
                        "max_data_sources_to_show": 5
                    },
                "manual_tagging":
                    {
                        "username": "Unknown",
                        "use_db": True,
                        "show_deprecated": False,
                        "enable_untagging": False
                    }
            },
    }
    return benedict(data_object)


def get_defaults() -> Dict:
    return dict(
        all_machines={1: 10051158, 2: 10051164, 3: 10051167, 4: 10051173, 5: 10052000},
        pipeline_versions_options={'stats_pipe_options': ['manual'],
                                   'labeled_events_pipe_options': ['manual'],
                                   'training_pipe_options': ['manual'],
                                   'events_pipe_options': ['manual']},
        machine_names=['1-10051158', '2-10051164', '3-10051167', '4-10051173', '5-10052000'],
        only_manual_mode=True
    )
