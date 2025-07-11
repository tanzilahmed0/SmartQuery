import uuid
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.project import (
    ProjectCreate,
    ProjectInDB,
    ProjectStatusEnum,
    ProjectTable,
    ProjectUpdate,
)
from services.database_service import get_db_service


class ProjectService:
    """Service for project database operations"""

    def __init__(self):
        self.db_service = get_db_service()

    def create_project(
        self, project_data: ProjectCreate, user_id: uuid.UUID
    ) -> ProjectInDB:
        """Create a new project in the database"""
        with self.db_service.get_session() as session:
            try:
                # Create new project
                db_project = ProjectTable(
                    user_id=user_id,
                    name=project_data.name,
                    description=project_data.description,
                    csv_filename="",  # Will be set after upload
                    csv_path=f"{user_id}/{uuid.uuid4()}/",  # Generate unique path
                    status=ProjectStatusEnum.UPLOADING,
                    columns_metadata=[],  # Initialize as empty list
                )

                session.add(db_project)
                session.commit()
                session.refresh(db_project)

                return ProjectInDB.model_validate(db_project)

            except IntegrityError as e:
                session.rollback()
                raise ValueError(f"Database error: {str(e)}")

    def get_project_by_id(self, project_id: uuid.UUID) -> Optional[ProjectInDB]:
        """Get project by ID"""
        with self.db_service.get_session() as session:
            project = (
                session.query(ProjectTable)
                .filter(ProjectTable.id == project_id)
                .first()
            )
            return ProjectInDB.model_validate(project) if project else None

    def get_projects_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[ProjectInDB]:
        """Get list of projects for a user with pagination"""
        with self.db_service.get_session() as session:
            projects = (
                session.query(ProjectTable)
                .filter(ProjectTable.user_id == user_id)
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [ProjectInDB.model_validate(project) for project in projects]

    def count_projects_by_user(self, user_id: uuid.UUID) -> int:
        """Count total number of projects for a user"""
        with self.db_service.get_session() as session:
            return (
                session.query(ProjectTable)
                .filter(ProjectTable.user_id == user_id)
                .count()
            )

    def update_project(
        self, project_id: uuid.UUID, project_update: ProjectUpdate
    ) -> ProjectInDB:
        """Update project information"""
        with self.db_service.get_session() as session:
            project = (
                session.query(ProjectTable)
                .filter(ProjectTable.id == project_id)
                .first()
            )

            if not project:
                raise ValueError(f"Project with ID {project_id} not found")

            # Update only provided fields
            update_data = project_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(project, field, value)

            try:
                session.commit()
                session.refresh(project)
                return ProjectInDB.model_validate(project)

            except IntegrityError as e:
                session.rollback()
                raise ValueError(f"Update failed: {str(e)}")

    def delete_project(self, project_id: uuid.UUID) -> bool:
        """Delete a project (hard delete)"""
        with self.db_service.get_session() as session:
            project = (
                session.query(ProjectTable)
                .filter(ProjectTable.id == project_id)
                .first()
            )

            if not project:
                return False

            session.delete(project)
            session.commit()
            return True

    def update_project_status(
        self, project_id: uuid.UUID, status: ProjectStatusEnum
    ) -> ProjectInDB:
        """Update project status"""
        return self.update_project(project_id, ProjectUpdate(status=status))

    def update_project_metadata(
        self,
        project_id: uuid.UUID,
        csv_filename: str,
        row_count: int,
        column_count: int,
        columns_metadata: list,
    ) -> ProjectInDB:
        """Update project metadata after file processing"""
        return self.update_project(
            project_id,
            ProjectUpdate(
                csv_filename=csv_filename,
                row_count=row_count,
                column_count=column_count,
                columns_metadata=columns_metadata,
                status=ProjectStatusEnum.READY,
            ),
        )

    def check_project_ownership(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Check if user owns the project"""
        with self.db_service.get_session() as session:
            project = (
                session.query(ProjectTable)
                .filter(ProjectTable.id == project_id, ProjectTable.user_id == user_id)
                .first()
            )
            return project is not None

    def health_check(self) -> dict:
        """Check if project service and database connection is healthy"""
        try:
            with self.db_service.get_session() as session:
                # Try to count projects
                project_count = session.query(ProjectTable).count()
                return {
                    "status": "healthy",
                    "message": f"Project service operational. Total projects: {project_count}",
                    "project_count": project_count,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Project service error: {str(e)}",
                "project_count": 0,
            }


_project_service_instance = None


def get_project_service():
    """Returns a singleton instance of the ProjectService."""
    global _project_service_instance
    if _project_service_instance is None:
        _project_service_instance = ProjectService()
    return _project_service_instance
