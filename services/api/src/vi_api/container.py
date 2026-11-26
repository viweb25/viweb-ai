from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from redis import Redis

from vi_api.app.catalogue.get_function_templates import GetFunctionTemplates
from vi_api.app.demo_examples.create_demo_example import CreateDemoExample
from vi_api.app.demo_examples.get_demo_example_image import GetDemoExampleImage
from vi_api.app.demo_examples.list_demo_examples import ListDemoExamples
from vi_api.app.health.check_readiness import CheckReadiness
from vi_api.app.identity.sign_in import SignIn
from vi_api.app.identity.sign_up import SignUp
from vi_api.app.inspection.inspection_service import InspectionService
from vi_api.app.training.dataset_service import DatasetService
from vi_api.app.training.job_service import TrainingJobService
from vi_api.app.workspaces.workspace_service import WorkspaceService
from vi_api.config.settings import Settings
from vi_api.domain.catalogue.repository import CatalogueRepository
from vi_api.domain.demo_examples.repository import DemoExampleRepository
from vi_api.domain.identity.ports import IdentityRepository
from vi_api.domain.training.ports import TrainingFileStore
from vi_api.infrastructure.cache.catalogue import CachedCatalogueRepository
from vi_api.infrastructure.database.readiness import DatabaseReadinessRepository
from vi_api.infrastructure.database.session import Session, engine
from vi_api.infrastructure.identity.passwords import ScryptPasswordHasher, ScryptPasswordVerifier
from vi_api.infrastructure.inference.client import HttpInferenceClient
from vi_api.infrastructure.repository.accounts import PostgresAccountRepository
from vi_api.infrastructure.repository.catalogue import JsonCatalogueRepository
from vi_api.infrastructure.repository.demo_examples import PostgresDemoExampleRepository
from vi_api.infrastructure.repository.identity import PostgresIdentityRepository
from vi_api.infrastructure.repository.training_datasets import PostgresDatasetRepository
from vi_api.infrastructure.repository.training_jobs import PostgresTrainingJobRepository
from vi_api.infrastructure.repository.workspaces import PostgresWorkspaceRepository
from vi_api.infrastructure.storage.training_files import LocalTrainingFileStore
from vi_api.interfaces.http.errors import ApiError, ErrorCode

ROOT = Path(__file__).resolve().parents[4]
CATALOGUE_PATH = ROOT / "packages/schemas/functions/catalogue.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_catalogue_repository() -> CatalogueRepository:
    source = JsonCatalogueRepository(CATALOGUE_PATH)
    url = get_settings().redis_cache_url
    if not url:
        return source
    cache = Redis.from_url(url, socket_connect_timeout=0.2, socket_timeout=0.2)
    version = sha256(CATALOGUE_PATH.read_bytes()).hexdigest()
    return CachedCatalogueRepository(source, cache, f"vi:catalogue:v1:{version}")


def get_function_templates() -> GetFunctionTemplates:
    return GetFunctionTemplates(get_catalogue_repository())


def check_readiness() -> CheckReadiness:
    return CheckReadiness(DatabaseReadinessRepository(engine))


def get_demo_example_repository() -> DemoExampleRepository:
    directory = get_settings().demo_image_dir
    if not directory:
        raise ApiError(404, ErrorCode.DEMO_DISABLED, "Local demo is disabled")
    return PostgresDemoExampleRepository(Session, Path(directory))


DemoRepo = Annotated[DemoExampleRepository, Depends(get_demo_example_repository)]


def get_create_demo_example(repository: DemoRepo) -> CreateDemoExample:
    return CreateDemoExample(repository)


def get_list_demo_examples(repository: DemoRepo) -> ListDemoExamples:
    return ListDemoExamples(repository)


def get_demo_example_image_operation(repository: DemoRepo) -> GetDemoExampleImage:
    return GetDemoExampleImage(repository)


def get_identity_repository() -> IdentityRepository:
    return PostgresIdentityRepository(Session)


def get_sign_in(
    repository: Annotated[IdentityRepository, Depends(get_identity_repository)],
) -> SignIn:
    return SignIn(repository, ScryptPasswordVerifier())


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_sign_up() -> SignUp:
    return SignUp(PostgresAccountRepository(), ScryptPasswordHasher())


def get_training_files(settings: SettingsDependency) -> TrainingFileStore:
    return LocalTrainingFileStore(settings.training_image_dir, settings.training_run_dir)


def get_inference_client(settings: SettingsDependency) -> HttpInferenceClient:
    return HttpInferenceClient(settings.inference_url)


TrainingFiles = Annotated[TrainingFileStore, Depends(get_training_files)]
InferenceClient = Annotated[HttpInferenceClient, Depends(get_inference_client)]


def get_dataset_service(files: TrainingFiles) -> DatasetService:
    return DatasetService(PostgresDatasetRepository(Session), files)


def get_training_job_service(
    files: TrainingFiles, inference: InferenceClient
) -> TrainingJobService:
    return TrainingJobService(PostgresTrainingJobRepository(Session), files, inference)


def get_inspection_service(inference: InferenceClient) -> InspectionService:
    return InspectionService(inference)


def get_workspace_service() -> WorkspaceService:
    return WorkspaceService(PostgresWorkspaceRepository(Session))
