import optuna_core


if __name__ == "__main__":
    study = optuna_core.study.create_study(direction="minimize")

    for _ in range(100):
        trial = study.ask()

        x = trial.suggest_float("x", -5.0, 5.0)
        y = (x - 2) ** 2

        study.tell(trial, state=optuna_core.trial.TrialState.COMPLETE, value=y)

        print(f"Completed trial {trial.number}: {y}. Best: {study.best_trial.value}.")
