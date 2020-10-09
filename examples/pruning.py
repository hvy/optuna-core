import optuna_core


def f(x):
    return (x - 2) ** 2


def df(x):
    return 2 * x - 4


if __name__ == "__main__":
    study = optuna_core.study.create_study(direction="minimize")

    for _ in range(100):
        trial = study.ask()

        lr = trial.suggest_loguniform("lr", 1e-5, 1e-1)

        x = 3.0
        for step in range(128):
            y = f(x)

            trial.report(y, step=step)
            if trial.should_prune():
                print(f"Pruned trial {trial.number} at step {step}: {y}. ", end="")
                study.tell(trial, state=optuna_core.trial.TrialState.PRUNED, value=y)
                break

            gy = df(x)
            x -= gy * lr
        else:
            print(f"Completed trial {trial.number}: {y}. ", end="")
            study.tell(trial, state=optuna_core.trial.TrialState.COMPLETE, value=y)

        print(f"Best: {study.best_trial.value}.")
