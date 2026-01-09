from pathlib import Path 
import argparse
from facts_experiment_builder.core.experiment.experiment import Experiment
import os 

def run_experiment_implementer(experiment_name: str, implementation: str = "docker_compose"):
    """Run a FACTS experiment."""
    cwd = os.getcwd()
    experiment_dir = Path(cwd).parent / "v2_experiments" / experiment_name
    print('experiment_dir: ', experiment_dir)
    experiment = Experiment(experiment_dir)
    experiment.generate_compose_file()
    print(f"Generated Docker Compose file for experiment: {experiment_dir}. \n Location: {experiment.experiment_dir / 'v2-compose.yaml'}")
    print("Now, run the experiment with: docker compose -f v2-compose.yaml up")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Docker Compose file for a FACTS experiment .")
    parser.add_argument("experiment_dir", type=Path, help="The directory containing the experiment metadata.")
    parser.add_argument("--implementation", type=str, default="docker_compose", help="The implementation to use for the experiment. Currently only 'docker_compose' is supported.")
    args = parser.parse_args()
    experiment_dir = args.experiment_dir
    implementation = args.implementation
    run_experiment_implementer(experiment_dir, implementation)
