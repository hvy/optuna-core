import core
from core.pruners._base import BasePruner  # NOQA
from core.pruners._hyperband import HyperbandPruner  # NOQA
from core.pruners._median import MedianPruner  # NOQA
from core.pruners._nop import NopPruner  # NOQA
from core.pruners._percentile import PercentilePruner  # NOQA
from core.pruners._successive_halving import SuccessiveHalvingPruner  # NOQA
from core.pruners._threshold import ThresholdPruner  # NOQA


def _filter_study(
    study: "core.study.Study", trial: "core.trial.FrozenTrial"
) -> "core.study.Study":
    if isinstance(study.pruner, HyperbandPruner):
        # Create `_BracketStudy` to use trials that have the same bracket id.
        pruner = study.pruner  # type: HyperbandPruner
        return pruner._create_bracket_study(study, pruner._get_bracket_id(study, trial))
    else:
        return study
