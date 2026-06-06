import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("crash-agent")


@dataclass(frozen=True)
class FirebaseAppConfig:
    app_id: str
    package_name: str


@dataclass(frozen=True)
class FirebaseConfig:
    project_id: str
    project_number: str
    storage_bucket: str
    apps: list[FirebaseAppConfig]


def load_firebase_config() -> FirebaseConfig:
    config_path = os.getenv(
        "FIREBASE_GOOGLE_SERVICES_PATH",
        "config/google-services.json",
    )
    with open(config_path, encoding="utf-8") as config_file:
        raw_config = json.load(config_file)
    project_info = raw_config["project_info"]
    apps = [
        FirebaseAppConfig(
            app_id=client["client_info"]["mobilesdk_app_id"],
            package_name=client["client_info"]["android_client_info"]["package_name"],
        )
        for client in raw_config["client"]
    ]
    config = FirebaseConfig(
        project_id=project_info["project_id"],
        project_number=project_info["project_number"],
        storage_bucket=project_info["storage_bucket"],
        apps=apps,
    )
    logger.info(
        "Loaded Firebase config for project=%s with %d app(s)",
        config.project_id,
        len(config.apps),
    )
    return config
