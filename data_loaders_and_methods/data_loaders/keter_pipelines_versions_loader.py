from src.logic.data_access import df_from_db


def get_events_pipe_options(training_pipe_version):
    meta_experiment_slug = get_training_version_from_name(training_pipe_version)

    predicted_events_versions_df = df_from_db(
        schema="events",
        table="events_detection_metadata_view",
        columns=["run_id"],
        conditions=[f"meta_experiment_slug = '{meta_experiment_slug}'"]
        #             "is_deprecated=False"]
    )

    if predicted_events_versions_df.empty:
        return ['manual']

    versions_list = list(predicted_events_versions_df['run_id'].unique())
    versions_list.sort(reverse=True)
    return versions_list + ['manual']


def get_training_version_from_name(training_version_name):
    return training_version_name.split(': ')[0]


def get_training_pipe_options(stats_events_pipe_version, labeled_events_pipe_version):
    # TODO: Remove after training supports different meta for statistics and labeled events
    if stats_events_pipe_version != labeled_events_pipe_version:
        return ['manual']

    pipe4_versions_df = df_from_db(
        schema="pipelines_runs",
        table="runs",
        columns=["arguments"],
        conditions=[f"pipeline_id = 4"]
    )

    training_versions_df = df_from_db(
        schema="algo",
        table="metadata_pipeline_3",
        columns=["main_experiment_slug", 'configuration_json', 'start_timestamp'],
        conditions=[f"pipeline_3_type = 'TRAIN'"]
    )

    def get_pipe2_version_from_pipe3(configuration):
        return int(configuration['param_grid'][0]['pipeline_2_hash'][0].split('_')[1])

    def create_presented_name(row):
        return f"{row['main_experiment_slug']}: {row['start_timestamp'].date()}"

    def get_slug_from_pipe4_arguments(arguments):
        return arguments['cnvrg_main_exp_slug']

    training_versions_df['pipe2_version'] = training_versions_df['configuration_json'].apply(get_pipe2_version_from_pipe3)
    training_versions_df = training_versions_df[training_versions_df['pipe2_version'] == labeled_events_pipe_version]
    pipe4_versions_df['main_exp_slug'] = pipe4_versions_df['arguments'].apply(get_slug_from_pipe4_arguments)

    if not training_versions_df.empty:
        slugs_with_pipe4 = list(pipe4_versions_df['main_exp_slug'].unique())
        training_versions_df = training_versions_df[training_versions_df['main_experiment_slug'].isin(slugs_with_pipe4)]
        if not training_versions_df.empty:
            training_versions_df['version_name'] = training_versions_df.apply(create_presented_name, axis=1)
            training_versions_df.sort_values('start_timestamp', inplace=True, ascending=False)
            training_versions_list = list(training_versions_df["version_name"].unique()) + ['manual']
        else:
            training_versions_list = ['manual']
    else:
        training_versions_list = ['manual']
    return training_versions_list


def get_pipeline_versions():
    versions_object = {}

    data_sources_statistics_df = df_from_db(
        schema="statistics_calculation",
        table="data_sources_statistics_mv",
        columns=["run_id"]
    )

    statistics_versions_list = list(data_sources_statistics_df["run_id"].unique())
    statistics_versions_list.sort(reverse=True)
    # TODO: Add ['manual'] if we ever want to upload stats manually
    versions_object["stats_pipe_options"] = statistics_versions_list

    labeled_events_df = df_from_db(
        schema="events",
        table="merged_calculated_labeled_events",
        columns=["run_id"]
    )

    calculated_labeled_versions_list = list(labeled_events_df["run_id"].unique())
    calculated_labeled_versions_list.sort(reverse=True)
    versions_object["labeled_events_pipe_options"] = calculated_labeled_versions_list + ['manual']

    training_versions_list = get_training_pipe_options(versions_object["stats_pipe_options"][0],
                                                       versions_object["labeled_events_pipe_options"][0])
    versions_object["training_pipe_options"] = training_versions_list

    versions_object["events_pipe_options"] = get_events_pipe_options(training_versions_list[0])

    return versions_object
