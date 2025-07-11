import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from middleware.auth_middleware import verify_token
from models.project import ProjectCreate, ProjectPublic
from models.response_schemas import (
    ApiResponse,
    ColumnMetadata,
    CreateProjectRequest,
    CreateProjectResponse,
    PaginatedResponse,
    PaginationParams,
    Project,
    ProjectStatus,
    UploadStatusResponse,
)
from services.project_service import get_project_service
from services.storage_service import storage_service

router = APIRouter(prefix="/projects", tags=["projects"])
project_service = get_project_service()

# Removed mock projects database - now using real database


@router.get("")
async def get_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(verify_token),
) -> ApiResponse[PaginatedResponse[Project]]:
    """Get user's projects with pagination"""

    try:
        user_uuid = uuid.UUID(user_id)

        # Get projects from database
        skip = (page - 1) * limit
        projects_db = project_service.get_projects_by_user(
            user_uuid, skip=skip, limit=limit
        )
        total = project_service.count_projects_by_user(user_uuid)

        # Convert to API response format
        projects_api = [
            ProjectPublic.from_db_project(project) for project in projects_db
        ]

        # Convert to Project schema for response
        projects_response = [
            Project(
                id=project.id,
                user_id=project.user_id,
                name=project.name,
                description=project.description,
                csv_filename=project.csv_filename,
                csv_path=project.csv_path,
                row_count=project.row_count,
                column_count=project.column_count,
                columns_metadata=project.columns_metadata,
                created_at=project.created_at,
                updated_at=project.updated_at,
                status=project.status,
            )
            for project in projects_api
        ]

        paginated_response = PaginatedResponse(
            items=projects_response,
            total=total,
            page=page,
            limit=limit,
            hasMore=(skip + limit) < total,
        )

        return ApiResponse(success=True, data=paginated_response)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid user ID: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch projects: {str(e)}"
        )


@router.post("")
async def create_project(
    request: CreateProjectRequest, user_id: str = Depends(verify_token)
) -> ApiResponse[CreateProjectResponse]:
    """Create new project"""

    try:
        user_uuid = uuid.UUID(user_id)

        # Create project in database
        project_create = ProjectCreate(
            name=request.name, description=request.description
        )
        project_db = project_service.create_project(project_create, user_uuid)

        # Convert to API response format
        project_api = ProjectPublic.from_db_project(project_db)
        project_response = Project(
            id=project_api.id,
            user_id=project_api.user_id,
            name=project_api.name,
            description=project_api.description,
            csv_filename=project_api.csv_filename,
            csv_path=project_api.csv_path,
            row_count=project_api.row_count,
            column_count=project_api.column_count,
            columns_metadata=project_api.columns_metadata,
            created_at=project_api.created_at,
            updated_at=project_api.updated_at,
            status=project_api.status,
        )

        # Generate presigned URL for file upload
        object_name = f"{user_id}/{project_db.id}/data.csv"
        upload_url = storage_service.generate_presigned_url(object_name)

        if not upload_url:
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")

        # MinIO presigned URLs don't use fields like AWS S3
        upload_fields = {
            "key": object_name,
        }

        response = CreateProjectResponse(
            project=project_response, upload_url=upload_url, upload_fields=upload_fields
        )

        return ApiResponse(success=True, data=response)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@router.get("/{project_id}")
async def get_project(
    project_id: str, user_id: str = Depends(verify_token)
) -> ApiResponse[Project]:
    """Get project details"""

    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        # Get project from database
        project_db = project_service.get_project_by_id(project_uuid)

        if not project_db:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check ownership
        if project_db.user_id != user_uuid:
            raise HTTPException(status_code=403, detail="Access denied")

        # Convert to API response format
        project_api = ProjectPublic.from_db_project(project_db)
        project_response = Project(
            id=project_api.id,
            user_id=project_api.user_id,
            name=project_api.name,
            description=project_api.description,
            csv_filename=project_api.csv_filename,
            csv_path=project_api.csv_path,
            row_count=project_api.row_count,
            column_count=project_api.column_count,
            columns_metadata=project_api.columns_metadata,
            created_at=project_api.created_at,
            updated_at=project_api.updated_at,
            status=project_api.status,
        )

        return ApiResponse(success=True, data=project_response)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid project ID: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch project: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str, user_id: str = Depends(verify_token)
) -> ApiResponse[Dict[str, str]]:
    """Delete project"""

    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        # Check if project exists and user owns it
        if not project_service.check_project_ownership(project_uuid, user_uuid):
            raise HTTPException(status_code=404, detail="Project not found")

        # Delete project from database
        success = project_service.delete_project(project_uuid)

        if not success:
            raise HTTPException(status_code=404, detail="Project not found")

        return ApiResponse(
            success=True, data={"message": "Project deleted successfully"}
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid project ID: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete project: {str(e)}"
        )


@router.get("/{project_id}/upload-url")
async def get_upload_url(
    project_id: str, user_id: str = Depends(verify_token)
) -> ApiResponse[Dict[str, Any]]:
    """Get presigned URL for file upload"""

    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        # Check if project exists and user owns it
        if not project_service.check_project_ownership(project_uuid, user_uuid):
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate presigned URL for file upload
        object_name = f"{user_id}/{project_id}/data.csv"
        upload_url = storage_service.generate_presigned_url(object_name)

        if not upload_url:
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")

        upload_data = {
            "upload_url": upload_url,
            "upload_fields": {
                "key": object_name,
            },
        }

        return ApiResponse(success=True, data=upload_data)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid project ID: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.get("/{project_id}/status")
async def get_project_status(
    project_id: str, user_id: str = Depends(verify_token)
) -> ApiResponse[UploadStatusResponse]:
    """Get project processing status"""

    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        # Get project from database
        project_db = project_service.get_project_by_id(project_uuid)

        if not project_db:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check ownership
        if project_db.user_id != user_uuid:
            raise HTTPException(status_code=403, detail="Access denied")

        # Determine progress and message based on status
        progress = 0
        message = ""

        if project_db.status == "uploading":
            progress = 25
            message = "Waiting for file upload..."
        elif project_db.status == "processing":
            progress = 75
            message = "Analyzing CSV schema..."
        elif project_db.status == "ready":
            progress = 100
            message = "Processing complete"
        elif project_db.status == "error":
            progress = 0
            message = "Processing failed"

        status_response = UploadStatusResponse(
            project_id=project_id,
            status=project_db.status,
            progress=progress,
            message=message,
        )

        return ApiResponse(success=True, data=status_response)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid project ID: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch project status: {str(e)}"
        )
