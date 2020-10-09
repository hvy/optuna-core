import optuna_core
from optuna_core.pruners._base import BasePruner  # NOQA
from optuna_core.pruners._hyperband import HyperbandPruner  # NOQA
from optuna_core.pruners._median import MedianPruner  # NOQA
from optuna_core.pruners._nop import NopPruner  # NOQA
from optuna_core.pruners._percentile import PercentilePruner  # NOQA
from optuna_core.pruners._successive_halving import SuccessiveHalvingPruner  # NOQA
from optuna_core.pruners._threshold import ThresholdPruner  # NOQA


def _filter_study(
    study: "optuna_core.study.Study", trial: "optuna_core.trial.FrozenTrial"
) -> "optuna_core.study.Study":
    if isinstance(study.pruner, HyperbandPruner):
        # Create `_BracketStudy` to use trials that have the same bracket id.
        pruner = study.pruner  # type: HyperbandPruner
        return pruner._create_bracket_study(study, pruner._get_bracket_id(study, trial))
    else:
        return study
