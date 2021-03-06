import copy
import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import optuna_core
from optuna_core import exceptions
from optuna_core import pruners
from optuna_core import samplers
from optuna_core import storages
from optuna_core import trial as trial_module
from optuna_core.study._study_direction import StudyDirection
from optuna_core.study._study_summary import StudySummary  # NOQA
from optuna_core.trial import create_trial
from optuna_core.trial import FrozenTrial
from optuna_core.trial import TrialState


ObjectiveFuncType = Callable[[trial_module.Trial], float]


class Study(object):
    """A study corresponds to an optimization task, i.e., a set of trials.

    This object provides interfaces to run a new :class:`~optuna.trial.Trial`, access trials'
    history, set/get user-defined attributes of the study itself.

    Note that the direct use of this constructor is not recommended.
    To create and load a study, please refer to the documentation of
    :func:`~optuna.study.create_study` and :func:`~optuna.study.load_study` respectively.

    """

    def __init__(
        self,
        study_name: str,
        storage: Union[str, "storages.BaseStorage"],
        sampler: Optional["samplers.BaseSampler"] = None,
        pruner: Optional[pruners.BasePruner] = None,
    ) -> None:
        self.study_name = study_name
        storage = storages.get_storage(storage)
        study_id = storage.get_study_id_from_name(study_name)

        self._study_id = study_id
        self._storage = storage

        self.sampler = sampler or samplers.RandomSampler()
        self.pruner = pruner or pruners.MedianPruner()

        self._optimize_lock = threading.Lock()
        self._stop_flag = False

    def __getstate__(self) -> Dict[Any, Any]:

        state = self.__dict__.copy()
        del state["_optimize_lock"]
        return state

    def __setstate__(self, state: Dict[Any, Any]) -> None:

        self.__dict__.update(state)
        self._optimize_lock = threading.Lock()

    def ask(self) -> trial_module.Trial:
        self._storage.read_trials_from_remote_storage(self._study_id)

        trial_id = self._storage.create_new_trial(self._study_id)
        return trial_module.Trial(self, trial_id)

    def tell(self, trial: trial_module.Trial, state: TrialState, value: Optional[float]) -> None:
        if state == TrialState.COMPLETE:
            assert value is not None
        if value is not None:
            self._storage.set_trial_value(trial._trial_id, value)
        self._storage.set_trial_state(trial._trial_id, state)

    @property
    def best_params(self) -> Dict[str, Any]:
        return self.best_trial.params

    @property
    def best_value(self) -> float:
        """Return the best objective value in the study.

        Returns:
            A float representing the best objective value.
        """

        best_value = self.best_trial.value
        assert best_value is not None

        return best_value

    @property
    def best_trial(self) -> FrozenTrial:
        """Return the best trial in the study.

        Returns:
            A :class:`~optuna.FrozenTrial` object of the best trial.
        """

        return copy.deepcopy(self._storage.get_best_trial(self._study_id))

    @property
    def direction(self) -> "optuna_core.study.StudyDirection":
        """Return the direction of the study.

        Returns:
            A :class:`~optuna.study.StudyDirection` object.
        """

        return self._storage.get_study_direction(self._study_id)

    @property
    def trials(self) -> List[FrozenTrial]:
        """Return all trials in the study.

        The returned trials are ordered by trial number.

        This is a short form of ``self.get_trials(deepcopy=True)``.

        Returns:
            A list of :class:`~optuna.FrozenTrial` objects.
        """

        return self.get_trials()

    def get_trials(self, deepcopy: bool = True) -> List[FrozenTrial]:
        """Return all trials in the study.

        The returned trials are ordered by trial number.

        For library users, it's recommended to use more handy
        :attr:`~optuna.study.Study.trials` property to get the trials instead.

        Example:
            .. testcode::

                import optuna


                def objective(trial):
                    x = trial.suggest_uniform("x", -1, 1)
                    return x ** 2


                study = optuna.create_study()
                study.optimize(objective, n_trials=3)

                trials = study.get_trials()
                assert len(trials) == 3
        Args:
            deepcopy:
                Flag to control whether to apply ``copy.deepcopy()`` to the trials.
                Note that if you set the flag to :obj:`False`, you shouldn't mutate
                any fields of the returned trial. Otherwise the internal state of
                the study may corrupt and unexpected behavior may happen.

        Returns:
            A list of :class:`~optuna.FrozenTrial` objects.
        """

        self._storage.read_trials_from_remote_storage(self._study_id)
        return self._storage.get_all_trials(self._study_id, deepcopy=deepcopy)

    @property
    def user_attrs(self) -> Dict[str, Any]:
        """Return user attributes.

        .. seealso::

            See :func:`~optuna.study.Study.set_user_attr` for related method.

        Example:

            .. testcode::

                import optuna


                def objective(trial):
                    x = trial.suggest_float("x", 0, 1)
                    y = trial.suggest_float("y", 0, 1)
                    return x ** 2 + y ** 2


                study = optuna.create_study()

                study.set_user_attr("objective function", "quadratic function")
                study.set_user_attr("dimensions", 2)
                study.set_user_attr("contributors", ["Akiba", "Sano"])

                assert study.user_attrs == {
                    "objective function": "quadratic function",
                    "dimensions": 2,
                    "contributors": ["Akiba", "Sano"],
                }

        Returns:
            A dictionary containing all user attributes.
        """

        return copy.deepcopy(self._storage.get_study_user_attrs(self._study_id))

    @property
    def system_attrs(self) -> Dict[str, Any]:
        """Return system attributes.

        Returns:
            A dictionary containing all system attributes.
        """

        return copy.deepcopy(self._storage.get_study_system_attrs(self._study_id))

    def set_user_attr(self, key: str, value: Any) -> None:
        """Set a user attribute to the study.

        .. seealso::

            See :attr:`~optuna.study.Study.user_attrs` for related attribute.

        Example:

            .. testcode::

                import optuna


                def objective(trial):
                    x = trial.suggest_float("x", 0, 1)
                    y = trial.suggest_float("y", 0, 1)
                    return x ** 2 + y ** 2


                study = optuna.create_study()

                study.set_user_attr("objective function", "quadratic function")
                study.set_user_attr("dimensions", 2)
                study.set_user_attr("contributors", ["Akiba", "Sano"])

                assert study.user_attrs == {
                    "objective function": "quadratic function",
                    "dimensions": 2,
                    "contributors": ["Akiba", "Sano"],
                }

        Args:
            key: A key string of the attribute.
            value: A value of the attribute. The value should be JSON serializable.

        """

        self._storage.set_study_user_attr(self._study_id, key, value)

    def set_system_attr(self, key: str, value: Any) -> None:
        """Set a system attribute to the study.

        Note that Optuna internally uses this method to save system messages. Please use
        :func:`~optuna.study.Study.set_user_attr` to set users' attributes.

        Args:
            key: A key string of the attribute.
            value: A value of the attribute. The value should be JSON serializable.

        """

        self._storage.set_study_system_attr(self._study_id, key, value)

    def stop(self) -> None:

        """Exit from the current optimization loop after the running trials finish.

        This method lets the running :meth:`~optuna.study.Study.optimize` method return
        immediately after all trials which the :meth:`~optuna.study.Study.optimize` method
        spawned finishes.
        This method does not affect any behaviors of parallel or successive study processes.

        Example:

            .. testcode::

                import optuna


                def objective(trial):
                    if trial.number == 4:
                        trial.study.stop()
                    x = trial.suggest_uniform("x", 0, 10)
                    return x ** 2


                study = optuna.create_study()
                study.optimize(objective, n_trials=10)
                assert len(study.trials) == 5

        Raises:
            RuntimeError:
                If this method is called outside an objective function or callback.
        """

        if self._optimize_lock.acquire(False):
            self._optimize_lock.release()
            raise RuntimeError(
                "`Study.stop` is supposed to be invoked inside an objective function or a "
                "callback."
            )

        self._stop_flag = True

    def enqueue_trial(self, params: Dict[str, Any]) -> None:
        """Enqueue a trial with given parameter values.

        You can fix the next sampling parameters which will be evaluated in your
        objective function.

        Example:

            .. testcode::

                import optuna


                def objective(trial):
                    x = trial.suggest_uniform("x", 0, 10)
                    return x ** 2


                study = optuna.create_study()
                study.enqueue_trial({"x": 5})
                study.enqueue_trial({"x": 0})
                study.optimize(objective, n_trials=2)

                assert study.trials[0].params == {"x": 5}
                assert study.trials[1].params == {"x": 0}

        Args:
            params:
                Parameter values to pass your objective function.
        """

        self.add_trial(
            create_trial(state=TrialState.WAITING, system_attrs={"fixed_params": params})
        )

    def add_trial(self, trial: FrozenTrial) -> None:
        """Add trial to study.

        The trial is validated before being added.

        Example:

            .. testcode::

                import optuna
                from optuna.distributions import UniformDistribution


                def objective(trial):
                    x = trial.suggest_uniform("x", 0, 10)
                    return x ** 2


                study = optuna.create_study()
                assert len(study.trials) == 0

                trial = optuna.trial.create_trial(
                    params={"x": 2.0},
                    distributions={"x": UniformDistribution(0, 10)},
                    value=4.0,
                )

                study.add_trial(trial)
                assert len(study.trials) == 1

                study.optimize(objective, n_trials=3)
                assert len(study.trials) == 4

                other_study = optuna.create_study()

                for trial in study.trials:
                    other_study.add_trial(trial)
                assert len(other_study.trials) == len(study.trials)

                other_study.optimize(objective, n_trials=2)
                assert len(other_study.trials) == len(study.trials) + 2

        .. seealso::

            This method should in general be used to add already evaluated trials
            (``trial.state.is_finished() == True``). To queue trials for evaluation,
            please refer to :func:`~optuna.study.Study.enqueue_trial`.

        .. seealso::

            See :func:`~optuna.trial.create_trial` for how to create trials.

        Args:
            trial: Trial to add.

        Raises:
            :exc:`ValueError`:
                If trial is an invalid state.

        """

        trial._validate()

        self._storage.create_new_trial(self._study_id, template_trial=trial)


def create_study(
    storage: Optional[Union[str, "storages.BaseStorage"]] = None,
    sampler: Optional["samplers.BaseSampler"] = None,
    pruner: Optional[pruners.BasePruner] = None,
    study_name: Optional[str] = None,
    direction: str = "minimize",
    load_if_exists: bool = False,
) -> Study:
    """Create a new :class:`~optuna.study.Study`.

    Example:

        .. testcode::

            import optuna


            def objective(trial):
                x = trial.suggest_uniform("x", 0, 10)
                return x ** 2


            study = optuna.create_study()
            study.optimize(objective, n_trials=3)

    Args:
        storage:
            Database URL. If this argument is set to None, in-memory storage is used, and the
            :class:`~optuna.study.Study` will not be persistent.

            .. note::
                When a database URL is passed, Optuna internally uses `SQLAlchemy`_ to handle
                the database. Please refer to `SQLAlchemy's document`_ for further details.
                If you want to specify non-default options to `SQLAlchemy Engine`_, you can
                instantiate :class:`~optuna.storages.RDBStorage` with your desired options and
                pass it to the ``storage`` argument instead of a URL.

             .. _SQLAlchemy: https://www.sqlalchemy.org/
             .. _SQLAlchemy's document:
                 https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
             .. _SQLAlchemy Engine: https://docs.sqlalchemy.org/en/latest/core/engines.html

        sampler:
            A sampler object that implements background algorithm for value suggestion.
            If :obj:`None` is specified, :class:`~optuna.samplers.TPESampler` is used
            as the default. See also :class:`~optuna.samplers`.
        pruner:
            A pruner object that decides early stopping of unpromising trials. If :obj:`None`
            is specified, :class:`~optuna.pruners.MedianPruner` is used as the default. See
            also :class:`~optuna.pruners`.
        study_name:
            Study's name. If this argument is set to None, a unique name is generated
            automatically.
        direction:
            Direction of optimization. Set ``minimize`` for minimization and ``maximize`` for
            maximization.
        load_if_exists:
            Flag to control the behavior to handle a conflict of study names.
            In the case where a study named ``study_name`` already exists in the ``storage``,
            a :class:`~optuna.exceptions.DuplicatedStudyError` is raised if ``load_if_exists`` is
            set to :obj:`False`.
            Otherwise, the creation of the study is skipped, and the existing one is returned.

    Returns:
        A :class:`~optuna.study.Study` object.

    See also:
        :func:`optuna.create_study` is an alias of :func:`optuna.study.create_study`.

    """

    storage = storages.get_storage(storage)
    try:
        study_id = storage.create_new_study(study_name)
    except exceptions.DuplicatedStudyError:
        if load_if_exists:
            assert study_name is not None
            study_id = storage.get_study_id_from_name(study_name)
        else:
            raise

    study_name = storage.get_study_name_from_id(study_id)
    study = Study(study_name=study_name, storage=storage, sampler=sampler, pruner=pruner)

    if direction == "minimize":
        _direction = StudyDirection.MINIMIZE
    elif direction == "maximize":
        _direction = StudyDirection.MAXIMIZE
    else:
        raise ValueError("Please set either 'minimize' or 'maximize' to direction.")

    study._storage.set_study_direction(study_id, _direction)

    return study


def load_study(
    study_name: str,
    storage: Union[str, "storages.BaseStorage"],
    sampler: Optional["samplers.BaseSampler"] = None,
    pruner: Optional[pruners.BasePruner] = None,
) -> Study:
    """Load the existing :class:`~optuna.study.Study` that has the specified name.

    Example:

        .. testsetup::

            import os

            if os.path.exists("example.db"):
                raise RuntimeError("'example.db' already exists. Please remove it.")

        .. testcode::

            import optuna


            def objective(trial):
                x = trial.suggest_float("x", 0, 10)
                return x ** 2


            study = optuna.create_study(storage="sqlite:///example.db", study_name="my_study")
            study.optimize(objective, n_trials=3)

            loaded_study = optuna.load_study(study_name="my_study", storage="sqlite:///example.db")
            assert len(loaded_study.trials) == len(study.trials)

        .. testcleanup::

            os.remove("example.db")

    Args:
        study_name:
            Study's name. Each study has a unique name as an identifier.
        storage:
            Database URL such as ``sqlite:///example.db``. Please see also the documentation of
            :func:`~optuna.study.create_study` for further details.
        sampler:
            A sampler object that implements background algorithm for value suggestion.
            If :obj:`None` is specified, :class:`~optuna.samplers.TPESampler` is used
            as the default. See also :class:`~optuna.samplers`.
        pruner:
            A pruner object that decides early stopping of unpromising trials.
            If :obj:`None` is specified, :class:`~optuna.pruners.MedianPruner` is used
            as the default. See also :class:`~optuna.pruners`.

    See also:
        :func:`optuna.load_study` is an alias of :func:`optuna.study.load_study`.

    """

    return Study(study_name=study_name, storage=storage, sampler=sampler, pruner=pruner)


def delete_study(
    study_name: str,
    storage: Union[str, "storages.BaseStorage"],
) -> None:
    """Delete a :class:`~optuna.study.Study` object.

    Example:

        .. testsetup::

            import os

            if os.path.exists("example.db"):
                raise RuntimeError("'example.db' already exists. Please remove it.")

        .. testcode::

            import optuna


            def objective(trial):
                x = trial.suggest_float("x", -10, 10)
                return (x - 2) ** 2


            study = optuna.create_study(study_name="example-study", storage="sqlite:///example.db")
            study.optimize(objective, n_trials=3)

            optuna.delete_study(study_name="example-study", storage="sqlite:///example.db")

        .. testcleanup::

            os.remove("example.db")

    Args:
        study_name:
            Study's name.
        storage:
            Database URL such as ``sqlite:///example.db``. Please see also the documentation of
            :func:`~optuna.study.create_study` for further details.

    See also:
        :func:`optuna.delete_study` is an alias of :func:`optuna.study.delete_study`.

    """

    storage = storages.get_storage(storage)
    study_id = storage.get_study_id_from_name(study_name)
    storage.delete_study(study_id)


def get_all_study_summaries(storage: Union[str, "storages.BaseStorage"]) -> List[StudySummary]:
    """Get all history of studies stored in a specified storage.

    Example:

        .. testsetup::

            import os

            if os.path.exists("example.db"):
                raise RuntimeError("'example.db' already exists. Please remove it.")

        .. testcode::

            import optuna


            def objective(trial):
                x = trial.suggest_float("x", -10, 10)
                return (x - 2) ** 2


            study = optuna.create_study(study_name="example-study", storage="sqlite:///example.db")
            study.optimize(objective, n_trials=3)

            study_summaries = optuna.study.get_all_study_summaries(storage="sqlite:///example.db")
            assert len(study_summaries) == 1

            study_summary = study_summaries[0]
            assert study_summary.study_name == "example-study"

        .. testcleanup::

            os.remove("example.db")

    Args:
        storage:
            Database URL such as ``sqlite:///example.db``. Please see also the documentation of
            :func:`~optuna.study.create_study` for further details.

    Returns:
        List of study history summarized as :class:`~optuna.study.StudySummary` objects.

    See also:
        :func:`optuna.get_all_study_summaries` is an alias of
        :func:`optuna.study.get_all_study_summaries`.

    """

    storage = storages.get_storage(storage)
    return storage.get_all_study_summaries()
