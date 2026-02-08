from ..startup import rsoxs_config
from ..Functions.alignment import (
    get_sample_id_and_index, 
    duplicate_sample, 
    load_samp,
)
from ..configuration_setup.configuration_load_save import sync_rsoxs_config_to_nbs_manipulator


def create_sample(
        sample_metadata = {
            "sample_id": None,
            "project_name": None,
            "institution": None,
            "proposal_id": None,
            "notes": None,
        },
        sample_id_to_duplicate = "TEM",
):
    """
    """

    ## First use the duplicate_sample function to copy over metadata.
    sample_id_to_duplicate, sample_index_to_duplicate = get_sample_id_and_index(sample_id_to_duplicate)
    duplicate_sample(sample_index_to_duplicate, sample_metadata["sample_id"])

    ## Then change any specific metadata as desired
    for metadata_key in list(sample_metadata.keys()):
        if sample_metadata[metadata_key] is not None:
            rsoxs_config["bar"][-1][metadata_key] = sample_metadata[metadata_key]
            if metadata_key == "sample_id":
                rsoxs_config["bar"][-1]["sample_name"] = sample_metadata[metadata_key]    
    sync_rsoxs_config_to_nbs_manipulator()

    ## Load sample to ensure that the metadata is loaded
    yield from load_samp(sample_metadata["sample_id"])


