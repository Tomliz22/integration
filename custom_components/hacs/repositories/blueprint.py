"""Class for themes in HACS."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..enums import HacsCategory, HacsDispatchEvent
from ..exceptions import HacsException
from ..utils.decorator import concurrent
from .base import HacsRepository

if TYPE_CHECKING:
    from ..base import HacsBase


class HacsBlueprintRepository(HacsRepository):
    """Blueprints in HACS."""

    def __init__(self, hacs: HacsBase, full_name: str):
        """Initialize."""
        super().__init__(hacs=hacs)
        self.data.full_name = full_name
        self.data.full_name_lower = full_name.lower()
        self.data.category = HacsCategory.BLUEPRINT
        self.content.path.remote = ""
        self.content.path.local = self.localpath
        self.content.single = True

    @property
    def localpath(self) -> str | None:
        """Return localpath."""
        if self.repository_manifest.blueprint_type is None or self.repository_owner is None:
            return None

        return f"{self.hacs.core.config_path}/blueprints/{self.repository_manifest.blueprint_type}/{self.repository_owner}"

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        self.data.file_name = self.repository_manifest.filename

        if (
            not self.data.file_name
            or "/" in self.data.file_name
            or not self.data.file_name.endswith(".yaml")
            or self.data.file_name not in self.treefiles
            or self.repository_manifest.blueprint_type is None
        ):
            raise HacsException(
                f"{self.string} Repository structure for {self.ref.replace('tags/','')} is not compliant"
            )

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.status.startup:
                    self.logger.error("%s %s", self.string, error)
        return self.validate.success

    async def async_post_registration(self):
        """Registration."""
        # Set filenames
        self.data.file_name = self.repository_manifest.filename
        self.content.path.local = self.localpath

        if self.hacs.system.action:
            await self.hacs.validation.async_run_repository_checks(self)

    @concurrent(concurrenttasks=10, backoff_time=5)
    async def update_repository(self, ignore_issues=False, force=False):
        """Update."""
        if not await self.common_update(ignore_issues, force) and not force:
            return

        # Update filenames
        self.data.file_name = self.repository_manifest.filename
        self.content.path.local = self.localpath

        # Signal entities to refresh
        if self.data.installed:
            self.hacs.async_dispatch(
                HacsDispatchEvent.REPOSITORY,
                {
                    "id": 1337,
                    "action": "update",
                    "repository": self.data.full_name,
                    "repository_id": self.data.id,
                },
            )
