import json
import logging
import os
from pathlib import Path
from typing import Any

import google.auth.transport.requests
import requests
from google.oauth2 import service_account

from app.firebase.config import FirebaseAppConfig, FirebaseConfig, load_firebase_config

logger = logging.getLogger("crash-agent")

CRASHLYTICS_BASE_URL = "https://firebasecrashlytics.googleapis.com/v1alpha"
CRASHLYTICS_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
TOP_ISSUES_REPORTS = ("topOpenIssues", "topIssues")


class CrashlyticsClient:
    def __init__(self) -> None:
        self._initialized = False
        self._credentials = None
        self._firebase_config: FirebaseConfig | None = None
        self._initialize_firebase()

    def _initialize_firebase(self) -> None:
        service_account_path = os.getenv(
            "FIREBASE_SERVICE_ACCOUNT_PATH",
            "service-account.json",
        )
        google_services_path = os.getenv(
            "FIREBASE_GOOGLE_SERVICES_PATH",
            "config/google-services.json",
        )
        if not os.path.exists(service_account_path):
            logger.warning(
                "Firebase service account not found at %s; using mock data",
                service_account_path,
            )
            return
        if not os.path.exists(google_services_path):
            logger.warning(
                "Google services config not found at %s; using mock data",
                google_services_path,
            )
            return
        try:
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            self._credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=CRASHLYTICS_SCOPES,
            )
            self._firebase_config = load_firebase_config()
            self._initialized = True
            logger.info(
                "Firebase initialized for project=%s",
                self._firebase_config.project_id,
            )
        except Exception as ex:
            logger.exception("Failed to initialize Firebase: %s", ex)

    def get_crashes(self) -> list[dict[str, Any]]:
        if self._initialized and self._firebase_config is not None:
            crashes = self._fetch_crashes_from_firebase(self._firebase_config)
            if crashes:
                return crashes
            logger.warning("No crashes returned from Crashlytics API; using mock data")
        return self._get_mock_crashes()

    def _fetch_crashes_from_firebase(
        self,
        firebase_config: FirebaseConfig,
    ) -> list[dict[str, Any]]:
        logger.info("Fetching crashes from Firebase Crashlytics")
        crashes: list[dict[str, Any]] = []
        for app in firebase_config.apps:
            app_crashes = self._fetch_crashes_for_app(firebase_config, app)
            crashes.extend(app_crashes)
        logger.info("Fetched %d crash issue(s) from Crashlytics", len(crashes))
        return crashes

    def _fetch_crashes_for_app(
        self,
        firebase_config: FirebaseConfig,
        app: FirebaseAppConfig,
    ) -> list[dict[str, Any]]:
        for report_name in TOP_ISSUES_REPORTS:
            report = self._get_crashlytics_report(
                firebase_config.project_id,
                app.app_id,
                report_name,
            )
            if report is None:
                continue
            crashes = self._parse_report_groups(report, app)
            if crashes:
                logger.info(
                    "Loaded %d issue(s) for package=%s via report=%s",
                    len(crashes),
                    app.package_name,
                    report_name,
                )
                return crashes
        return []

    def _get_access_token(self) -> str:
        if self._credentials is None:
            raise RuntimeError("Firebase credentials are not initialized")
        auth_request = google.auth.transport.requests.Request()
        self._credentials.refresh(auth_request)
        if not self._credentials.token:
            raise RuntimeError("Failed to obtain Firebase access token")
        return self._credentials.token

    def _get_crashlytics_report(
        self,
        project_id: str,
        app_id: str,
        report_name: str,
    ) -> dict[str, Any] | None:
        report_path = (
            f"projects/{project_id}/apps/{app_id}/reports/{report_name}"
        )
        url = f"{CRASHLYTICS_BASE_URL}/{report_path}"
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
        }
        try:
            response = requests.get(
                url,
                headers=headers,
                params={"pageSize": 50},
                timeout=30,
            )
            if response.status_code == 404:
                logger.warning(
                    "Crashlytics report not found: project=%s app=%s report=%s",
                    project_id,
                    app_id,
                    report_name,
                )
                return None
            if response.status_code == 403:
                error_body = response.json().get("error", {})
                logger.error(
                    "Crashlytics API access denied: %s",
                    error_body.get("message", response.text),
                )
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as ex:
            logger.exception(
                "Crashlytics API request failed for report=%s: %s",
                report_name,
                ex,
            )
            return None

    def _parse_report_groups(
        self,
        report: dict[str, Any],
        app: FirebaseAppConfig,
    ) -> list[dict[str, Any]]:
        crashes: list[dict[str, Any]] = []
        for group in report.get("groups", []):
            crash = self._parse_crash_group(group, app)
            if crash is not None:
                crashes.append(crash)
        return crashes

    def _parse_crash_group(
        self,
        group: dict[str, Any],
        app: FirebaseAppConfig,
    ) -> dict[str, Any] | None:
        issue = group.get("issue")
        if issue is None:
            return None
        metrics = group.get("metrics", [])
        impacted_users = 0
        if metrics:
            impacted_users = int(metrics[0].get("impactedUsersCount", 0))
        issue_id = issue.get("id")
        if not issue_id and issue.get("name"):
            issue_id = issue["name"].split("/")[-1]
        if not issue_id:
            return None
        return {
            "issue_id": issue_id,
            "title": issue.get("title", "Unknown crash"),
            "affected_users": impacted_users,
            "app_version": issue.get("lastSeenVersion", "unknown"),
            "package_name": app.package_name,
            "app_id": app.app_id,
        }

    def _get_mock_crashes(self) -> list[dict[str, Any]]:
        mock_file = Path(__file__).parent / "mock_crashes.json"
        with open(mock_file, encoding="utf-8") as mock_file_handle:
            crashes = json.load(mock_file_handle)
        logger.info("Loaded %d mock crash(es) from %s", len(crashes), mock_file)
        return crashes
