import sys
import warnings

from preprocessing.scripts.prepare_language_folder import (
    extract_stimulus_version_number_from_asc,
)

from ..data_collection.multipleye_data_collection import MultipleyeDataCollection
from ..models.sid import Sid


class MeridDataCollection(MultipleyeDataCollection):
    num_sessions = 2
    type = "MeRID"

    def _load_session_stimulus_order(
        self, session_identifier, logfile_order_version: int
    ):
        sid = Sid(session_identifier)
        p_id = sid.pid
        session_id = int(sid.session_id)
        incomplete_order = []
        if p_id in self.crashed_session_ids:
            incomplete_order = self.sessions[session_identifier].completed_stimuli_ids

        stim_order_version = self.stim_order_versions[
            self.stim_order_versions["participant_id"] == int(p_id)
        ]
        if len(stim_order_version) == 0:
            print(
                "\n"
                "+" + "-" * 175 + "+" + "\n"
                f" WARNING: Participant ID {p_id} not found in stimulus order versions. Please check the "
                f" participant IDs in the stimulus order versions file. It is possible that the team did not "
                f"upload the correct stimulus version from the experiment folder. Extracting version "
                f"from asc file. Gaze data may be mapped to the wrong stimuli/AOIs. "
                f"Please verify that the stimulus folder contains the exact stimuli "
                f"that were presented to this participant."
                "\n"
                f"+" + "-" * 175 + "+",
                file=sys.stderr,
            )
            version = extract_stimulus_version_number_from_asc(
                self.sessions[session_identifier].asc_path
            )

            if version == logfile_order_version:
                stim_order_version = self.stim_order_versions[
                    self.stim_order_versions["version_number"] == version
                ]
                if stim_order_version.empty:
                    raise ValueError(
                        f"Stimulus order version {version} extracted from the ASC file "
                        f"cannot be found in the stimulus order versions CSV. "
                        f"The team should upload the correct stimulus folder."
                    )

                self.logger.warning(
                    "Using the stimulus order version from the ASC file. "
                    "The team should still upload the correct stimulus folder!"
                )

            else:
                self.logger.warning(
                    f"Stimulus order version in logfile ({logfile_order_version}) does not match the version "
                    f"extracted from the asc file ({version}) for participant ID {p_id}. OR no version found in asc file. "
                    f"Please check the files "
                    f"carefully."
                )

        if len(stim_order_version) == 1:
            version = stim_order_version["version_number"].values[0]
            if logfile_order_version != version:
                warnings.warn(
                    f"Stimulus order version in logfile ({logfile_order_version}) does not match the version "
                    f"in the stimulus order versions file ({version}) for participant ID {p_id}. Using the "
                    f"version from the logfile."
                )
            stimulus_order = (
                stim_order_version.drop(columns=["version_number", "participant_id"])
                .values[0]
                .tolist()
            )

            if session_id == 1:
                stimulus_order = [stimulus_order[0]] + stimulus_order[2:7]
            elif session_id == 2:
                stimulus_order = [stimulus_order[1]] + stimulus_order[7:]

        else:
            raise ValueError(
                f"More than one entry found for participant ID {p_id} in stimulus order versions. "
                f"Please check the stimulus order versions file for duplicates."
            )

        if incomplete_order:
            stimulus_order_copy = stimulus_order.copy()
            incom, comp = 0, 0
            for _ in range(len(stimulus_order)):
                if len(incomplete_order) == incom:
                    return incomplete_order

                if incomplete_order[incom] == stimulus_order_copy[comp]:
                    incom += 1
                    comp += 1
                    continue

                if incomplete_order[incom] != stimulus_order_copy[comp]:
                    stimulus_order_copy.pop(incom)

                if stimulus_order_copy == incomplete_order:
                    return incomplete_order

                if len(stimulus_order_copy) < len(incomplete_order):
                    raise ValueError(
                        "Crashed session stimulus order is not a subset of the stimuli order which was "
                        "supposed to be completed."
                    )
            return incomplete_order

        return stimulus_order

    def _load_psychometric_tests(self, session_identifier: str) -> bool:
        # TODO: make sure that it works with the sessions. I.e. in one session one tests is done,
        #  in the other the others.

        warnings.warn(
            "Not yet implemented: loading psychometric tests for MeRID data collection."
        )
