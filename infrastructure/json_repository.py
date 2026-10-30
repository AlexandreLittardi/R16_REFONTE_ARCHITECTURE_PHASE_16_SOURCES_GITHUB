"""The one filesystem boundary for reading and writing R16 JSON projects.

Wraps the proven schema-v2 writer: atomic replace, versioned backups,
independent .recovery snapshots, roof image, and route geometry verification.
"""
import json
from pathlib import Path
from domain.project_document import ProjectDocument
from project_store import write_project, verify_routing_geometry, validate_project


class ProjectRepository:
    def read(self, path) -> ProjectDocument:
        with Path(path).open('r', encoding='utf-8') as stream:
            return ProjectDocument(validate_project(json.load(stream)))

    def write(self, path, document, *, image=None, recovery=False) -> dict:
        state = document.snapshot() if isinstance(document, ProjectDocument) else ProjectDocument(document).snapshot()
        saved = write_project(path, state, image, recovery=recovery)
        verify_routing_geometry(path, state)
        return saved

    @staticmethod
    def recovery_path(path, project_uid, projects_dir):
        root = Path(path).parent if path else Path(projects_dir)
        return root / '.recovery' / (str(project_uid) + '.json')
