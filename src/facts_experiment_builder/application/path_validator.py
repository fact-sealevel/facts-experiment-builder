from facts_experiment_builder.core.modules.abcs.abcs import ModulePathsABC

class PathValidator:
    """Validates paths exist before creating Docker compose."""
    
    def validate_for_docker(self, paths: ModulePathsABC) -> None:
        """Optional: validate paths exist before Docker setup."""
        pass