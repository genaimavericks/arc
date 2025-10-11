"""
Enhanced Dashboard Creator API Router
Provides endpoints for AI-powered dashboard generation and management
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import logging

from ..models import DashboardRecord, DashboardBuildQueue, get_db
from ..auth import get_current_active_user, has_permission
from .services.dataset_validator import DatasetValidator
from .services.dashboard_template_generator import ModernDashboardTemplateGenerator
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

# Request/Response Models
class DatasetSelectionRequest(BaseModel):
    source_ids: List[str] = Field(default_factory=list, description="Source dataset IDs")
    transformed_ids: List[str] = Field(default_factory=list, description="Transformed dataset IDs")

class TemplateGenerationRequest(BaseModel):
    user_prompt: str = Field(..., description="User's natural language description")
    dataset_selection: DatasetSelectionRequest
    user_context: Optional[Dict] = Field(default_factory=dict, description="Additional user context")

class DashboardCreateRequest(BaseModel):
    dashboard_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    template_id: str = Field(..., description="Selected template ID")
    dataset_selection: DatasetSelectionRequest
    dashboard_config: Dict = Field(..., description="Dashboard configuration")
    ai_chat_history: Optional[List[Dict]] = Field(default_factory=list)

class DashboardResponse(BaseModel):
    id: str
    dashboard_name: str
    description: Optional[str]
    build_status: str
    static_path: Optional[str]
    created_at: str
    updated_at: str
    user_id: str

class BuildStatusResponse(BaseModel):
    dashboard_id: str
    build_status: str
    static_path: Optional[str]
    build_started_at: Optional[str]
    build_completed_at: Optional[str]
    error_message: Optional[str]

# Initialize services
dataset_validator = DatasetValidator()
template_generator = ModernDashboardTemplateGenerator()

@router.get("/test-endpoint")
async def test_endpoint():
    """Test endpoint to verify routing works"""
    print("🧪 TEST ENDPOINT REACHED!")
    return {"status": "success", "message": "Dashboard router is working"}

@router.post("/generate-templates")
async def generate_templates(
    request: TemplateGenerationRequest,
    current_user = Depends(has_permission("dashboard:write")),
    db: Session = Depends(get_db)
):
    """Generate AI-powered dashboard templates based on user input and selected datasets"""
    
    try:
        print(f"🚀 DASHBOARD GENERATION STARTED - User: {current_user.username}")
        print(f"🚀 Request data: {request}")
        print(f"🚀 Dataset selection: {request.dataset_selection}")
        logger.info(f"🚀 DASHBOARD GENERATION STARTED - User: {current_user.username}")
        logger.info(f"Generating templates for user {current_user.username}")
        
        # Convert request to dict for processing
        dataset_selection = {
            "source_ids": request.dataset_selection.source_ids,
            "transformed_ids": request.dataset_selection.transformed_ids
        }
        
        # Generate templates using AI service
        result = await template_generator.generate_dashboard_templates(
            user_prompt=request.user_prompt,
            dataset_selection=dataset_selection,
            user_context=request.user_context
        )
        
        # Log template generation
        from ..auth import log_activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Dashboard templates generated",
            details=f"Generated {len(result.get('templates', []))} templates"
        )
        
        print(f"🚀 DASHBOARD GENERATION SUCCESS - Generated {len(result.get('templates', []))} templates")
        return result
        
    except Exception as e:
        print(f"❌ DASHBOARD GENERATION ERROR: {str(e)}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        logger.error(f"Error generating templates: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate templates: {str(e)}"
        )

@router.post("/create-static", response_model=DashboardResponse)
async def create_static_dashboard(
    request: DashboardCreateRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(has_permission("dashboard:write")),
    db: Session = Depends(get_db)
):
    """Create a new dashboard and queue it for static generation"""
    
    try:
        # Generate unique dashboard ID
        dashboard_id = str(uuid.uuid4())
        
        # Validate datasets before creating dashboard
        dataset_selection = {
            "source_ids": request.dataset_selection.source_ids,
            "transformed_ids": request.dataset_selection.transformed_ids
        }
        
        validation_result = await dataset_validator.validate_selected_datasets(dataset_selection)
        
        if not validation_result["can_create_dashboard"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create dashboard: Selected datasets are invalid or empty"
            )
        
        # Create dashboard record
        dashboard_record = DashboardRecord(
            id=dashboard_id,
            user_id=current_user.username,
            dashboard_name=request.dashboard_name,
            description=request.description,
            source_dataset_ids=request.dataset_selection.source_ids,
            transformed_dataset_ids=request.dataset_selection.transformed_ids,
            dashboard_config=request.dashboard_config,
            template_id=request.template_id,
            ai_chat_history=request.ai_chat_history,
            build_status="building",
            build_started_at=datetime.utcnow()
        )
        
        db.add(dashboard_record)
        db.commit()
        db.refresh(dashboard_record)
        
        # Queue for background processing
        build_job = DashboardBuildQueue(
            id=str(uuid.uuid4()),
            dashboard_id=dashboard_id,
            build_priority=5,
            status="queued"
        )
        
        db.add(build_job)
        db.commit()
        
        # Add background task for static generation
        background_tasks.add_task(
            process_dashboard_build,
            dashboard_id,
            request.dashboard_config,
            validation_result
        )
        
        # Log dashboard creation
        from ..auth import log_activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Dashboard created",
            details=f"Created dashboard: {request.dashboard_name}"
        )
        
        return DashboardResponse(
            id=dashboard_record.id,
            dashboard_name=dashboard_record.dashboard_name,
            description=dashboard_record.description,
            build_status=dashboard_record.build_status,
            static_path=dashboard_record.static_path,
            created_at=dashboard_record.created_at.isoformat(),
            updated_at=dashboard_record.updated_at.isoformat(),
            user_id=dashboard_record.user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard creation failed: {str(e)}"
        )

@router.get("/{dashboard_id}/build-status", response_model=BuildStatusResponse)
async def get_build_status(
    dashboard_id: str,
    current_user = Depends(has_permission("dashboard:read")),
    db: Session = Depends(get_db)
):
    """Get the build status of a dashboard"""
    
    try:
        dashboard = db.query(DashboardRecord).filter(
            DashboardRecord.id == dashboard_id
        ).first()
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        # Check if user has access
        if dashboard.user_id != current_user.username and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get latest build job
        build_job = db.query(DashboardBuildQueue).filter(
            DashboardBuildQueue.dashboard_id == dashboard_id
        ).order_by(DashboardBuildQueue.created_at.desc()).first()
        
        return BuildStatusResponse(
            dashboard_id=dashboard.id,
            build_status=dashboard.build_status,
            static_path=dashboard.static_path,
            build_started_at=dashboard.build_started_at.isoformat() if dashboard.build_started_at else None,
            build_completed_at=dashboard.build_completed_at.isoformat() if dashboard.build_completed_at else None,
            error_message=build_job.error_message if build_job else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting build status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get build status: {str(e)}"
        )

@router.get("/user-dashboards", response_model=List[DashboardResponse])
async def get_user_dashboards(
    current_user = Depends(has_permission("dashboard:read")),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get all dashboards for the current user"""
    
    try:
        dashboards = db.query(DashboardRecord).filter(
            DashboardRecord.user_id == current_user.username
        ).order_by(
            DashboardRecord.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [
            DashboardResponse(
                id=dashboard.id,
                dashboard_name=dashboard.dashboard_name,
                description=dashboard.description,
                build_status=dashboard.build_status,
                static_path=dashboard.static_path,
                created_at=dashboard.created_at.isoformat(),
                updated_at=dashboard.updated_at.isoformat(),
                user_id=dashboard.user_id
            )
            for dashboard in dashboards
        ]
        
    except Exception as e:
        logger.error(f"Error getting user dashboards: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboards: {str(e)}"
        )

@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str,
    current_user = Depends(has_permission("dashboard:read")),
    db: Session = Depends(get_db)
):
    """Get a specific dashboard by ID"""
    
    try:
        dashboard = db.query(DashboardRecord).filter(
            DashboardRecord.id == dashboard_id
        ).first()
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        # Check if user has access
        if dashboard.user_id != current_user.username and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return DashboardResponse(
            id=dashboard.id,
            dashboard_name=dashboard.dashboard_name,
            description=dashboard.description,
            build_status=dashboard.build_status,
            static_path=dashboard.static_path,
            created_at=dashboard.created_at.isoformat(),
            updated_at=dashboard.updated_at.isoformat(),
            user_id=dashboard.user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )

# Background task for dashboard processing
async def process_dashboard_build(
    dashboard_id: str,
    dashboard_config: Dict,
    validation_result: Dict
):
    """Background task to process dashboard build"""
    
    from ..models import SessionLocal
    from .services.static_dashboard_builder import StaticDashboardBuilder
    
    db = SessionLocal()
    
    try:
        # Update build status to processing
        dashboard = db.query(DashboardRecord).filter(
            DashboardRecord.id == dashboard_id
        ).first()
        
        if not dashboard:
            logger.error(f"Dashboard {dashboard_id} not found for building")
            return
        
        dashboard.build_status = "processing"
        db.commit()
        
        logger.info(f"Starting build process for dashboard {dashboard_id}")
        
        # Build static dashboard using the builder service
        builder = StaticDashboardBuilder()
        build_result = await builder.build_static_dashboard(
            dashboard_id=dashboard_id,
            dashboard_config=dashboard_config,
            validation_result=validation_result
        )
        
        if build_result["success"]:
            # Update dashboard with successful build
            dashboard.build_status = "ready"
            dashboard.build_completed_at = datetime.utcnow()
            dashboard.static_path = build_result["static_path"]
            dashboard.asset_manifest = build_result["asset_manifest"]
            
            logger.info(f"Dashboard {dashboard_id} build completed successfully")
        else:
            # Update dashboard with failed build
            dashboard.build_status = "failed"
            dashboard.build_completed_at = datetime.utcnow()
            
            # Update build queue with error
            build_job = db.query(DashboardBuildQueue).filter(
                DashboardBuildQueue.dashboard_id == dashboard_id
            ).order_by(DashboardBuildQueue.created_at.desc()).first()
            
            if build_job:
                build_job.status = "failed"
                build_job.error_message = build_result.get("error", "Unknown build error")
                build_job.completed_at = datetime.utcnow()
            
            logger.error(f"Dashboard {dashboard_id} build failed: {build_result.get('error')}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error processing dashboard build {dashboard_id}: {str(e)}")
        
        # Update to failed status
        try:
            dashboard = db.query(DashboardRecord).filter(
                DashboardRecord.id == dashboard_id
            ).first()
            
            if dashboard:
                dashboard.build_status = "failed"
                dashboard.build_completed_at = datetime.utcnow()
                db.commit()
                
            # Update build queue
            build_job = db.query(DashboardBuildQueue).filter(
                DashboardBuildQueue.dashboard_id == dashboard_id
            ).order_by(DashboardBuildQueue.created_at.desc()).first()
            
            if build_job:
                build_job.status = "failed"
                build_job.error_message = str(e)
                build_job.completed_at = datetime.utcnow()
                db.commit()
                
        except Exception as inner_e:
            logger.error(f"Error updating failed build status: {str(inner_e)}")
    
    finally:
        db.close()
