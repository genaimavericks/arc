"""
DataPuur AI Router - API endpoints for AI-powered profiling and transformation
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
import logging
import json
import asyncio
from pathlib import Path
import traceback
import copy
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator, root_validator, create_model

from api.models import User, get_db, SessionLocal, UploadedFile
from api.auth import has_any_permission, log_activity
from api.profiler.models import ProfileResult
from .models import (
    ProfileSession, ProfileMessage as ProfileMessageModel, TransformationPlan, 
    TransformationMessage, ProfileJob, TransformedDataset
)
from .schemas import (
    ProfileSessionCreate, ProfileSessionResponse, ProfileSessionListResponse,
    ProfileChatRequest, ProfileChatResponse, ProfileMessageSchema, ChatMessage,
    TransformationPlanCreate, TransformationPlanResponse, TransformationPlanUpdate,
    TransformationMessageCreate, TransformationChatRequest, TransformationChatResponse,
    ExecuteScriptRequest, ExecuteScriptResponse, JobStatus,
    DataSourceResponse, ProfileSessionWithPlansResponse,
    TransformedDatasetCreate, TransformedDatasetResponse, DatasetMetadataUpdate
)
from .services import ProfileAgent, TransformationAgent, ScriptExecutor
from .transformed_dataset import router as transformed_dataset_router


# Helper function to standardize profile_summary format
def _standardize_profile_summary(profile_summary):
    """Convert profile_summary to a consistent dictionary format that matches the Pydantic model"""
    try:
        print(f"===DEBUG=== Standardizing profile_summary of type: {type(profile_summary)}")
        
        # Handle None case
        if profile_summary is None:
            print("===DEBUG=== profile_summary is None, returning None")
            return None
            
        # If already a dictionary with 'text' key, ensure text is a string
        if isinstance(profile_summary, dict):
            if 'text' in profile_summary:
                if isinstance(profile_summary['text'], str):
                    print("===DEBUG=== profile_summary is a dict with string text key, returning as is")
                    return profile_summary
                else:
                    print(f"===DEBUG=== profile_summary has non-string text value: {type(profile_summary['text'])}")
                    return {"text": str(profile_summary['text'])}
            else:
                # Dictionary without 'text' key, convert to JSON string
                print("===DEBUG=== profile_summary is a dict without text key, converting to JSON string")
                return {"text": json.dumps(profile_summary)}
        
        # If it's a string, wrap it in a dictionary
        if isinstance(profile_summary, str):
            print("===DEBUG=== profile_summary is a string, wrapping in dict")
            return {"text": profile_summary}
            
        # Special handling for SQLAlchemy objects or other complex objects
        if hasattr(profile_summary, '__dict__'):
            print("===DEBUG=== profile_summary has __dict__, converting to string representation")
            return {"text": str(profile_summary)}
            
        # For any other type, convert to string and wrap in dictionary
        print(f"===DEBUG=== profile_summary is another type: {type(profile_summary)}, converting to string")
        return {"text": str(profile_summary)}
        
    except Exception as e:
        print(f"===DEBUG=== Error in standardize_profile_summary: {str(e)}")
        # Fallback to a safe default
        return {"text": "Profile summary unavailable"}

logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Create router
router = APIRouter(prefix="/api/datapuur-ai", tags=["datapuur-ai"])

# Include the transformed dataset router
router.include_router(transformed_dataset_router)

# Initialize services
profile_agent = ProfileAgent()
transformation_agent = TransformationAgent()
script_executor = ScriptExecutor()


# Profile Session Endpoints
@router.post("/sessions", response_model=ProfileSessionResponse)
async def create_profile_session(
    request: ProfileSessionCreate,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Create a new AI profiling session"""
    try:
        # Create session
        session = ProfileSession(
            file_id=request.file_id,
            file_name=request.file_name,
            file_path=request.file_path,
            username=current_user.username,
            status="active"
        )
        db.add(session)
        db.commit()
        
        # Get profile_id from profile_result and update session
        profile_result = db.query(ProfileResult).filter(
            ProfileResult.file_id == request.file_id
        ).order_by(ProfileResult.created_at.desc()).first()
        
        if profile_result:
            session.profile_id = profile_result.id
            db.commit()
            logger.info(f"Associated session {session.id} with profile {profile_result.id}")
        
        # Get existing profile data if available
        profile_result = db.query(ProfileResult).filter(
            ProfileResult.file_id == request.file_id
        ).order_by(ProfileResult.created_at.desc()).first()
        
        if profile_result:
            # Analyze profile with AI
            analysis = profile_agent.analyze_profile(
                profile_data={
                    "total_rows": profile_result.total_rows,
                    "total_columns": profile_result.total_columns,
                    "data_quality_score": profile_result.data_quality_score,
                    "missing_values_count": sum(
                        col.get("missing_count", 0) 
                        for col in profile_result.column_profiles if isinstance(col, dict)
                    ),
                    "exact_duplicates_count": profile_result.exact_duplicates_count,
                    "columns": profile_result.column_profiles
                },
                file_path=request.file_path
            )
            
            # Update session with analysis
            summary_text = analysis.get("summary", "")
            session.profile_summary = {"text": summary_text}
            session.data_quality_issues = analysis.get("quality_issues", [])
            session.improvement_suggestions = analysis.get("suggestions", [])
            
            # Create system message with profile insights
            initial_message = ProfileMessageModel(
                session_id=session.id,
                role="assistant",
                content=analysis.get("summary", "Profile analysis completed."),
                message_metadata={
                    "quality_issues": analysis.get("quality_issues", []),
                    "suggestions": analysis.get("suggestions", [])
                }
            )
            db.add(initial_message)
        else:
            # Add welcome message if no profile exists
            welcome_message = ProfileMessageModel(
                session_id=session.id,
                role="assistant",
                content="I'll help you analyze and improve your data. Would you like me to start with a comprehensive profile analysis?"
            )
            db.add(welcome_message)
        
        db.commit()
        db.refresh(session)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="AI Profile Session Created",
            details=f"Created AI profiling session for {request.file_name}"
        )
        
        return ProfileSessionResponse(
            id=session.id,
            file_id=session.file_id,
            file_name=session.file_name,
            status=session.status,
            session_type=session.session_type,
            created_at=session.created_at,
            updated_at=session.updated_at,
            profile_summary=session.profile_summary,
            data_quality_issues=session.data_quality_issues,
            improvement_suggestions=session.improvement_suggestions,
            messages=[{
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "metadata": msg.message_metadata
            } for msg in session.messages]
        )
        
    except Exception as e:
        logger.error(f"Error creating profile session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_profile_session(
    session_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Retrieve a profile session by ID"""
    try:
        print(f"===DEBUG=== Retrieving profile session {session_id} for user {current_user.username}")
        logger.info(f"Retrieving profile session {session_id} for user {current_user.username}")
        
        # Find the session
        session = db.query(ProfileSession).filter(
            ProfileSession.id == session_id,
            ProfileSession.username == current_user.username
        ).first()
        
        if not session:
            logger.warning(f"Session {session_id} not found for user {current_user.username}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages for this session
        messages = (
            db.query(ProfileMessageModel)
            .filter(ProfileMessageModel.session_id == session.id)
            .order_by(ProfileMessageModel.timestamp)
            .all()
        )
        
        # Create response object with all fields - fully detached from SQLAlchemy models
        # Create a deep copy of data_quality_issues and improvement_suggestions to break references
        data_quality_issues = []
        if session.data_quality_issues:
            try:
                if isinstance(session.data_quality_issues, list):
                    data_quality_issues = copy.deepcopy(session.data_quality_issues)
                else:
                    print(f"===DEBUG=== data_quality_issues is not a list: {type(session.data_quality_issues)}")
                    data_quality_issues = []
            except Exception as e:
                print(f"===DEBUG=== Error copying data_quality_issues: {str(e)}")
                data_quality_issues = []
        
        improvement_suggestions = []
        if session.improvement_suggestions:
            try:
                if isinstance(session.improvement_suggestions, list):
                    improvement_suggestions = copy.deepcopy(session.improvement_suggestions)
                else:
                    print(f"===DEBUG=== improvement_suggestions is not a list: {type(session.improvement_suggestions)}")
                    improvement_suggestions = []
            except Exception as e:
                print(f"===DEBUG=== Error copying improvement_suggestions: {str(e)}")
                improvement_suggestions = []
        
        # Safe message extraction
        message_list = []
        for message in messages:
            try:
                metadata = None
                if hasattr(message, 'metadata') and message.metadata:
                    try:
                        if isinstance(message.metadata, dict):
                            metadata = dict(message.metadata)
                        else:
                            metadata = {"value": str(message.metadata)}
                    except Exception as e:
                        print(f"===DEBUG=== Error processing message metadata: {str(e)}")
                        metadata = {"error": "Could not process metadata"}
                
                message_list.append({
                    "id": message.id,  # Keep original ID format
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                    "metadata": metadata
                })
            except Exception as msg_e:
                print(f"===DEBUG=== Error processing message: {str(msg_e)}")
                # Skip this message if we can't process it
        
        # Create response object - preserve original types for fields that don't need conversion
        session_data = {
            "id": session.id,  # Keep original UUID format
            "file_id": session.file_id,  # Keep original format
            "file_name": session.file_name,
            "profile_id": session.profile_id,  # Keep original format
            "status": session.status,
            "session_type": session.session_type,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "profile_summary": session.profile_summary,
            "data_quality_issues": data_quality_issues,
            "improvement_suggestions": improvement_suggestions,
            "messages": message_list
        }
        
        return session_data
    except Exception as e:
        print(f"===ERROR=== Error retrieving profile session: {str(e)}")
        logger.error(f"Error retrieving profile session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_profile_session(
    session_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Delete a profile session and its associated transformation plans
    Note: This does not delete the profile results themselves, only the session.
    """
    try:
        print(f"===DEBUG=== Deleting profile session {session_id} for user {current_user.username}")
        logger.info(f"Deleting profile session {session_id} for user {current_user.username}")
        
        # Find the session
        session = db.query(ProfileSession).filter(
            ProfileSession.id == session_id,
            ProfileSession.username == current_user.username
        ).first()
        
        if not session:
            logger.warning(f"Session {session_id} not found for user {current_user.username}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Log the deletion activity
        log_activity(
            db, 
            current_user.username,
            "delete_profile_session",
            {"id": session_id, "file_id": session.file_id, "file_name": session.file_name}
        )
        
        # The delete will cascade to related messages and transformation plans
        # due to the relationship settings in the model
        db.delete(session)
        db.commit()
        
        return {"status": "success", "message": "Profile session deleted successfully"}
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"===ERROR=== Error deleting profile session: {str(e)}")
        logger.error(f"Error deleting profile session: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete profile session: {str(e)}")


@router.get("/sessions")
async def list_profile_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    file_id: Optional[str] = None,
    session_type: Optional[str] = None,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    try:
        print(f"===DEBUG=== Listing profile sessions for user {current_user.username}")
        print(f"===DEBUG=== Query parameters: page={page}, limit={limit}, file_id={file_id}, session_type={session_type}")
        logger.info(f"Listing profile sessions for user {current_user.username}")
        logger.info(f"Query parameters: page={page}, limit={limit}, file_id={file_id}, session_type={session_type}")
        
        # Apply filters
        query = db.query(ProfileSession).filter(
            ProfileSession.username == current_user.username
        )
        
        # Apply file filter if provided
        if file_id:
            query = query.filter(ProfileSession.file_id == file_id)
            
        # Apply session type filter if provided
        if session_type:
            query = query.filter(ProfileSession.session_type == session_type)
        
        # Get total count
        total = query.count()
        logger.info(f"Found {total} profile sessions for user {current_user.username}")
        
        # Apply pagination
        sessions = query.order_by(ProfileSession.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        # Log details about each session to help diagnose issues
        results = []
        print(f"===DEBUG=== Preparing response data for {len(sessions)} sessions")
        for idx, session in enumerate(sessions):
            print(f"===DEBUG=== Processing session {session.id} for response")
            # Get messages for this session
            # Use the SQLAlchemy model (imported at the top level)
            messages = (
                db.query(ProfileMessageModel)
                .filter(ProfileMessageModel.session_id == session.id)
                .order_by(ProfileMessageModel.timestamp)
                .all()
            )
            print(f"===DEBUG=== Found {len(messages)} messages for session {session.id}")
            
            # Detailed logging of profile_summary
            if session.profile_summary:
                if isinstance(session.profile_summary, dict):
                    print(f"===DEBUG=== Session {idx+1} profile_summary is dict with keys: {list(session.profile_summary.keys())}")
                    logger.info(f"Session {idx+1} profile_summary is dict with keys: {list(session.profile_summary.keys())}")
                    if 'text' in session.profile_summary:
                        print(f"===DEBUG=== Session {idx+1} profile_summary.text type: {type(session.profile_summary['text'])}")
                        print(f"===DEBUG=== Session {idx+1} profile_summary.text preview: {session.profile_summary['text'][:50]}..." 
                                   if isinstance(session.profile_summary['text'], str) and len(session.profile_summary['text']) > 50 
                                   else session.profile_summary['text'])
                        logger.info(f"Session {idx+1} profile_summary.text type: {type(session.profile_summary['text'])}")
                        logger.info(f"Session {idx+1} profile_summary.text preview: {session.profile_summary['text'][:50]}..." 
                                   if isinstance(session.profile_summary['text'], str) and len(session.profile_summary['text']) > 50 
                                   else session.profile_summary['text'])
                    else:
                        print(f"===DEBUG=== Session {idx+1} profile_summary does not have 'text' key")
                        logger.info(f"Session {idx+1} profile_summary does not have 'text' key")
                elif isinstance(session.profile_summary, str):
                    print(f"===DEBUG=== Session {idx+1} profile_summary is string, preview: {session.profile_summary[:50]}..." 
                               if len(session.profile_summary) > 50 else session.profile_summary)
                    logger.info(f"Session {idx+1} profile_summary is string, preview: {session.profile_summary[:50]}..." 
                               if len(session.profile_summary) > 50 else session.profile_summary)
                else:
                    print(f"===DEBUG=== Session {idx+1} profile_summary is type {type(session.profile_summary)}, repr: {repr(session.profile_summary)}")
                    logger.info(f"Session {idx+1} profile_summary is type {type(session.profile_summary)}, repr: {repr(session.profile_summary)}")
            logger.info(f"Session {idx+1} standardized profile_summary: {_standardize_profile_summary(session.profile_summary)}")
            if _standardize_profile_summary(session.profile_summary):
                logger.info(f"Session {idx+1} standardized profile_summary type: {type(_standardize_profile_summary(session.profile_summary))}")
                if 'text' in _standardize_profile_summary(session.profile_summary):
                    logger.info(f"Session {idx+1} standardized text type: {type(_standardize_profile_summary(session.profile_summary)['text'])}")
                    logger.info(f"Session {idx+1} standardized text preview: {_standardize_profile_summary(session.profile_summary)['text'][:50]}...")
                # Ensure profile_summary is in the correct format
            standardized_profile_summary = _standardize_profile_summary(session.profile_summary)
            print(f"===DEBUG=== Standardized profile_summary for session {session.id}: {standardized_profile_summary}")
            
            # Create response object with all fields - fully detached from SQLAlchemy models
            # Create a deep copy of data_quality_issues and improvement_suggestions to break references
            data_quality_issues = []
            if session.data_quality_issues:
                try:
                    if isinstance(session.data_quality_issues, list):
                        data_quality_issues = copy.deepcopy(session.data_quality_issues)
                    else:
                        print(f"===DEBUG=== data_quality_issues is not a list: {type(session.data_quality_issues)}")
                        data_quality_issues = []
                except Exception as e:
                    print(f"===DEBUG=== Error copying data_quality_issues: {str(e)}")
                    data_quality_issues = []
            
            improvement_suggestions = []
            if session.improvement_suggestions:
                try:
                    if isinstance(session.improvement_suggestions, list):
                        improvement_suggestions = copy.deepcopy(session.improvement_suggestions)
                    else:
                        print(f"===DEBUG=== improvement_suggestions is not a list: {type(session.improvement_suggestions)}")
                        improvement_suggestions = []
                except Exception as e:
                    print(f"===DEBUG=== Error copying improvement_suggestions: {str(e)}")
                    improvement_suggestions = []
            
            # Safe message extraction
            message_list = []
            for message in messages:
                try:
                    metadata = None
                    if hasattr(message, 'metadata') and message.metadata:
                        try:
                            if isinstance(message.metadata, dict):
                                metadata = dict(message.metadata)
                            else:
                                metadata = {"value": str(message.metadata)}
                        except Exception as e:
                            print(f"===DEBUG=== Error processing message metadata: {str(e)}")
                            metadata = {"error": "Could not process metadata"}
                    
                    message_list.append({
                        "id": message.id,  # Keep original ID format
                        "role": message.role,
                        "content": message.content,
                        "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                        "metadata": metadata
                    })
                except Exception as msg_e:
                    print(f"===DEBUG=== Error processing message: {str(msg_e)}")
                    # Skip this message if we can't process it
            
            # Create response object - preserve original types for fields that don't need conversion
            session_data = {
                "id": session.id,  # Keep original UUID format
                "file_id": session.file_id,  # Keep original format
                "file_name": session.file_name,
                "profile_id": session.profile_id,  # Keep original format
                "status": session.status,
                "session_type": session.session_type,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "profile_summary": standardized_profile_summary,
                "data_quality_issues": data_quality_issues,
                "improvement_suggestions": improvement_suggestions,
                "messages": message_list
            }
            
            print(f"===DEBUG=== Created session_data object for {session.id}")
            results.append(session_data)
        
        # Return raw dictionary instead of Pydantic model to avoid validation issues
        response_data = {
            "sessions": results,
            "total": total,
            "page": page,
            "limit": limit
        }
        print(f"===DEBUG=== Returning response with {len(results)} sessions")
        logger.info(f"Number of sessions in response: {len(response_data['sessions'])}")
        
        # Test JSON serialization before returning to catch any serialization issues
        try:
            import json
            serialized = json.dumps(response_data)
            print(f"===DEBUG=== Response successfully serialized to JSON, length: {len(serialized)}")
        except Exception as json_e:
            print(f"===DEBUG=== ⚠️ JSON serialization error in list_profile_sessions: {str(json_e)}")
            # Try to identify the problematic field
            try:
                # Try to serialize each session individually
                for i, session_data in enumerate(results):
                    try:
                        json.dumps(session_data)
                    except Exception as sess_e:
                        print(f"===DEBUG=== Problem with session {i}, error: {str(sess_e)}")
                        # Check each field in the session
                        for field in session_data:
                            try:
                                json.dumps(session_data[field])
                            except Exception as field_e:
                                print(f"===DEBUG=== Problem field in session {i}: {field}, error: {str(field_e)}")
                                # If it's profile_summary, try to fix it
                                if field == 'profile_summary' and session_data[field] is not None:
                                    print(f"===DEBUG=== Fixing profile_summary in session {i}")
                                    session_data[field] = {"text": str(session_data[field])}
            except Exception as debug_e:
                print(f"===DEBUG=== Error during debug process: {str(debug_e)}")
        
        return response_data
        
    except Exception as e:
        print(f"===ERROR=== Error listing profile sessions: {str(e)}")
        print(f"===ERROR=== {traceback.format_exc()}")
        logger.error(f"Error listing profile sessions: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_profile_session(
    session_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get a specific profile session with all messages"""
    try:
        print(f"===DEBUG=== Retrieving profile session {session_id} for user {current_user.username}")
        logger.info(f"Retrieving profile session {session_id} for user {current_user.username}")
        
        session = db.query(ProfileSession).filter(
            ProfileSession.id == session_id,
            ProfileSession.username == current_user.username
        ).first()
        print(f"===DEBUG=== Session query result: {session is not None}")
        
        if not session:
            logger.warning(f"Session {session_id} not found for user {current_user.username}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages directly from the database to avoid relationship issues
        # Use the SQLAlchemy model (imported at the top level)
        messages = db.query(ProfileMessageModel).filter(ProfileMessageModel.session_id == session_id).order_by(ProfileMessageModel.timestamp).all()
        print(f"===DEBUG=== Retrieved session {session.id} with {len(messages)} messages")
        logger.info(f"Retrieved session {session.id} with {len(messages)} messages")
        
        # Log message details if any exist
        for idx, message in enumerate(messages[:3]):  # Log first 3 messages for debugging
            print(f"===DEBUG=== Message {idx+1}: id={message.id}, role={message.role}, content preview: {message.content[:50] if message.content else 'None'}...")
        
        # Get the standardized profile summary
        standardized_summary = _standardize_profile_summary(session.profile_summary)
        print(f"===DEBUG=== Profile summary before standardization: {type(session.profile_summary)}")
        print(f"===DEBUG=== Profile summary after standardization: {type(standardized_summary)}")
        print(f"===DEBUG=== Standardized summary content: {standardized_summary}")
        
        logger.info(f"Profile summary type after standardization: {type(standardized_summary)}")
        if standardized_summary:
            print(f"===DEBUG=== Standardized summary keys: {list(standardized_summary.keys()) if isinstance(standardized_summary, dict) else 'Not a dict'}")
            logger.info(f"Standardized summary keys: {list(standardized_summary.keys()) if isinstance(standardized_summary, dict) else 'Not a dict'}")
        
        # Create a deep copy of data_quality_issues and improvement_suggestions to break references
        data_quality_issues = []
        if session.data_quality_issues:
            try:
                if isinstance(session.data_quality_issues, list):
                    data_quality_issues = copy.deepcopy(session.data_quality_issues)
                else:
                    print(f"===DEBUG=== data_quality_issues is not a list: {type(session.data_quality_issues)}")
                    data_quality_issues = []
            except Exception as e:
                print(f"===DEBUG=== Error copying data_quality_issues: {str(e)}")
                data_quality_issues = []
        
        improvement_suggestions = []
        if session.improvement_suggestions:
            try:
                if isinstance(session.improvement_suggestions, list):
                    improvement_suggestions = copy.deepcopy(session.improvement_suggestions)
                else:
                    print(f"===DEBUG=== improvement_suggestions is not a list: {type(session.improvement_suggestions)}")
                    improvement_suggestions = []
            except Exception as e:
                print(f"===DEBUG=== Error copying improvement_suggestions: {str(e)}")
                improvement_suggestions = []
        
        # Safe message extraction
        message_list = []
        for message in messages:
            try:
                metadata = None
                if hasattr(message, 'metadata') and message.metadata:
                    try:
                        if isinstance(message.metadata, dict):
                            metadata = dict(message.metadata)
                        else:
                            metadata = {"value": str(message.metadata)}
                    except Exception as e:
                        print(f"===DEBUG=== Error processing message metadata: {str(e)}")
                        metadata = {"error": "Could not process metadata"}
                
                message_list.append({
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                    "metadata": metadata
                })
            except Exception as msg_e:
                print(f"===DEBUG=== Error processing message: {str(msg_e)}")
                # Skip this message if we can't process it
        
        # Return raw dictionary instead of Pydantic model to avoid validation issues
        # Preserve original types where possible to maintain compatibility with frontend
        response_data = {
            "id": session.id,
            "file_id": session.file_id,
            "file_name": session.file_name,
            "status": session.status,
            "session_type": session.session_type,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "profile_id": session.profile_id,
            "profile_summary": standardized_summary,
            "data_quality_issues": data_quality_issues,
            "improvement_suggestions": improvement_suggestions,
            "messages": message_list
        }
        
        # Debug log the response data structure and try to JSON serialize it to catch any issues
        print(f"===DEBUG=== get_profile_session response keys: {list(response_data.keys())}")
        print(f"===DEBUG=== session ID type: {type(session.id).__name__}")
        print(f"===DEBUG=== message_list length: {len(message_list)}")
        
        try:
            import json
            # Try to JSON serialize to catch any serialization issues
            json_data = json.dumps(response_data)
            print(f"===DEBUG=== JSON serialization successful, length: {len(json_data)}")
        except Exception as json_e:
            print(f"===DEBUG=== JSON serialization error: {str(json_e)}")
            # Try to identify the problematic field
            for key in response_data.keys():
                try:
                    json.dumps(response_data[key])
                except Exception as field_e:
                    print(f"===DEBUG=== Problem field: {key}, error: {str(field_e)}")
                    
                    # If the problem is with messages, try to identify the specific message
                    if key == "messages" and isinstance(response_data[key], list):
                        for i, msg in enumerate(response_data[key]):
                            try:
                                json.dumps(msg)
                            except Exception as msg_e:
                                print(f"===DEBUG=== Problem with message {i}, error: {str(msg_e)}")
                                # Check each field in the message
                                for msg_key in msg:
                                    try:
                                        json.dumps(msg[msg_key])
                                    except Exception as field_e:
                                        print(f"===DEBUG=== Problem field in message {i}: {msg_key}, error: {str(field_e)}")

        
        logger.info(f"Successfully constructed response for session {session_id}")
        return response_data
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.exception(f"Error in get_profile_session for session ID {session_id}: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error retrieving session: {str(e)}")


# Chat Endpoints
@router.post("/sessions/{session_id}/chat", response_model=ProfileChatResponse)
async def chat_profile_session(
    session_id: str,
    request: ProfileChatRequest,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Chat with AI about data profiling"""
    logger.info(f"Chat request received for session {session_id} from user {current_user.username}")
    logger.info(f"Request message: {request.message}")
    
    session = db.query(ProfileSession).filter(
        ProfileSession.id == session_id,
        ProfileSession.username == current_user.username
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.info(f"Found session: {session.id}, profile_id: {session.profile_id}, status: {session.status}")
    
    # Check existing messages
    # Use the SQLAlchemy model (imported at the top level)
    existing_messages = db.query(ProfileMessageModel).filter(ProfileMessageModel.session_id == session_id).all()
    logger.info(f"Found {len(existing_messages)} existing messages for session {session_id}")
    
    try:
        # Add user message
        user_message = ProfileMessageModel(
            session_id=session_id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()
        logger.info(f"Added user message with id: {user_message.id} to session: {session_id}")
        logger.info(f"User message content: {user_message.content[:100]}..." if len(user_message.content) > 100 else f"User message content: {user_message.content}")
        
        # Get conversation history
        messages = db.query(ProfileMessageModel).filter(
            ProfileMessageModel.session_id == session_id
        ).order_by(ProfileMessageModel.timestamp).all()
        
        # Prepare context
        conversation = [
            {"role": msg.role, "content": msg.content}
            for msg in messages[-10:]  # Last 10 messages
        ]
        
        # Check if user is asking for script generation
        if any(keyword in request.message.lower() for keyword in [
            "generate script", "create script", "write code", "python code"
        ]):
            # Generate profiling script
            script = profile_agent.generate_profile_script(
                file_path=session.file_path,
                custom_requirements=request.message,
                focus_areas=None
            )
            
            # Save script to session
            session.profile_script = script
            
            # Create assistant response
            assistant_message = ProfileMessageModel(
                session_id=session_id,
                role="assistant",
                content="I've generated a custom profiling script based on your requirements. You can execute it to get detailed insights.",
                message_metadata={"script": script}
            )
        else:
            # Regular conversation about profiling
            try:
                logger.info(f"Calling LLM with {len(conversation)} messages")
                for idx, msg in enumerate(conversation):
                    logger.info(f"Message {idx}: {msg['role']} - {msg['content'][:50]}..." if len(msg['content']) > 50 else f"Message {idx}: {msg['role']} - {msg['content']}")
                
                response = profile_agent.model.chat(
                    messages=conversation,
                    system_message="You are a data profiling expert helping users understand and improve their data quality."
                )
                
                logger.info(f"LLM response type: {type(response)}")
                logger.info(f"LLM response content: {response.content[:100]}..." if response.content and len(response.content) > 100 else f"LLM response content: {response.content}")
                
                if not response.content or response.content.strip() == "":
                    # Fallback response if model returns empty content
                    logger.warning("LLM returned empty response, using fallback")
                    content = "I apologize, but I couldn't generate a proper response. Please try asking your question again or rephrase it."
                else:
                    content = response.content
                    
                assistant_message = ProfileMessageModel(
                    session_id=session_id,
                    role="assistant",
                    content=content
                )
            except Exception as e:
                logger.error(f"Error calling LLM: {str(e)}")
                assistant_message = ProfileMessageModel(
                    session_id=session_id,
                    role="assistant",
                    content="I apologize, but I encountered an error processing your request. Please try again."
                )
        
        db.add(assistant_message)
        session.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Added assistant message with id: {assistant_message.id} to session: {session_id}")
        logger.info(f"Assistant message content: {assistant_message.content[:100]}..." if len(assistant_message.content) > 100 else f"Assistant message content: {assistant_message.content}")
        
        # Safely extract message metadata to prevent circular references
        metadata = None
        if hasattr(assistant_message, 'message_metadata') and assistant_message.message_metadata:
            try:
                if isinstance(assistant_message.message_metadata, dict):
                    metadata = dict(assistant_message.message_metadata)
                else:
                    metadata = {"value": str(assistant_message.message_metadata)}
            except Exception as e:
                print(f"===DEBUG=== Error processing message metadata: {str(e)}")
                metadata = {"error": "Could not process metadata"}
        
        # Extract script safely from metadata
        generated_script = None
        if metadata and isinstance(metadata, dict) and "script" in metadata:
            try:
                generated_script = str(metadata["script"])
            except Exception as script_e:
                print(f"===DEBUG=== Error extracting script: {str(script_e)}")
                generated_script = None
        
        # Safely get profile summary
        standardized_summary = _standardize_profile_summary(session.profile_summary)
        
        # Safely get improvement suggestions
        suggestions = []
        if session.improvement_suggestions:
            try:
                if isinstance(session.improvement_suggestions, list):
                    suggestions = copy.deepcopy(session.improvement_suggestions)
                else:
                    print(f"===DEBUG=== improvement_suggestions is not a list: {type(session.improvement_suggestions)}")
                    suggestions = []
            except Exception as e:
                print(f"===DEBUG=== Error copying improvement_suggestions: {str(e)}")
                suggestions = []
        
        # Create a detached message object that preserves original types
        message_obj = {
            "id": assistant_message.id,
            "role": assistant_message.role,
            "content": assistant_message.content,
            "timestamp": assistant_message.timestamp.isoformat() if assistant_message.timestamp else None,
            "metadata": metadata
        }
        
        # Debug log the exact message object structure and try JSON serialization
        print(f"===DEBUG=== Message object structure: {message_obj}")
        
        try:
            import json
            json_data = json.dumps(message_obj)
            print(f"===DEBUG=== Message JSON serialization successful, length: {len(json_data)}")
        except Exception as json_e:
            print(f"===DEBUG=== Message JSON serialization error: {str(json_e)}")
            # Identify problematic fields
            for key in message_obj.keys():
                try:
                    json.dumps(message_obj[key])
                except Exception as field_e:
                    print(f"===DEBUG=== Problem field in message: {key}, error: {str(field_e)}")
                    
        # Debug print the metadata in detail
        if metadata:
            print(f"===DEBUG=== Metadata type: {type(metadata).__name__}")
            if isinstance(metadata, dict):
                for k, v in metadata.items():
                    print(f"===DEBUG=== Metadata key: {k}, value type: {type(v).__name__}")
                    if hasattr(v, '__dict__'):
                        print(f"===DEBUG=== Object with __dict__: {k}")
            else:
                print(f"===DEBUG=== Non-dict metadata: {metadata}")
        
        # Check entire response object
        response_obj = {
            "message": message_obj,
            "session_status": session.status,
            "profile_summary": standardized_summary,
            "suggestions": suggestions,
            "generated_script": generated_script
        }
        try:
            json_data = json.dumps(response_obj)
            print(f"===DEBUG=== Full response JSON serialization successful")
        except Exception as json_e:
            print(f"===DEBUG=== Full response JSON serialization error: {str(json_e)}")
        
        # Create and return the response
        return ProfileChatResponse(
            message=message_obj,
            session_status=session.status,
            profile_summary=standardized_summary,
            suggestions=suggestions,
            generated_script=generated_script
        )
        
    except Exception as e:
        logger.error(f"Error in profile chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Transformation Endpoints

@router.put("/transformations/{plan_id}", response_model=TransformationPlanResponse)
async def update_transformation_plan(
    plan_id: str,
    request: TransformationPlanUpdate,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Update transformation plan details (name, description) without finalizing the plan."""
    try:
        plan = db.query(TransformationPlan).filter(TransformationPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Transformation plan not found")
        # Ownership/permission: allow if user has datapuur:write (already checked),
        # optionally could check ownership if profile_session_id is present
        if request.name is not None:
            plan.name = request.name
        if request.description is not None:
            plan.description = request.description
        plan.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(plan)
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Update Transformation Plan",
            details=f"Updated transformation plan '{plan.name}' ({plan.id})"
        )
        return TransformationPlanResponse(
            id=plan.id,
            profile_session_id=plan.profile_session_id,
            name=plan.name,
            description=plan.description,
            status=plan.status,
            transformation_steps=plan.transformation_steps or [],
            expected_improvements=plan.expected_improvements or {},
            transformation_script=plan.transformation_script,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )
    except Exception as e:
        logger.error(f"Error updating transformation plan {plan_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update transformation plan: {str(e)}")

@router.delete("/transformations/{plan_id}")
async def delete_transformation_plan(
    plan_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Delete a specific transformation plan"""
    try:
        # Find the plan in the database
        plan = db.query(TransformationPlan).filter(
            TransformationPlan.id == plan_id
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Transformation plan not found")
        
        # Log the deletion
        log_activity(
            db, 
            current_user.username,
            "delete_transformation_plan",
            {"id": plan_id, "name": plan.name}
        )
        
        # Delete the plan - this will cascade to related messages due to relationship settings
        db.delete(plan)
        db.commit()
        
        return {"status": "success", "message": "Transformation plan deleted successfully"}
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting transformation plan: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete transformation plan: {str(e)}")

@router.get("/transformations/{plan_id}", response_model=TransformationPlanResponse)
async def get_transformation_plan(
    plan_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get a specific transformation plan"""
    print(f"\n====== TRYING TO GET TRANSFORMATION PLAN {plan_id} ======")
    print(f"User: {current_user.username}")
    
    # First, check if the plan exists at all
    plan = None
    direct_plan = db.query(TransformationPlan).filter(TransformationPlan.id == plan_id).first()
    
    if not direct_plan:
        print(f"[DEBUG] Plan not found in database: {plan_id}")
        raise HTTPException(status_code=404, detail="Transformation plan not found")
    
    print(f"[DEBUG] Plan found: ID={direct_plan.id}, Name={direct_plan.name}, HasSession={direct_plan.profile_session_id is not None}")
    
    # Now handle the permissions based on whether it has a profile_session_id or not
    if direct_plan.profile_session_id is not None:
        # For plans with a profile session, check user ownership
        print(f"[DEBUG] Plan has profile_session_id: {direct_plan.profile_session_id}")
        
        # Find the profile session and check user ownership
        session = db.query(ProfileSession).filter(
            ProfileSession.id == direct_plan.profile_session_id
        ).first()
        
        if not session:
            print(f"[DEBUG] Referenced profile session not found: {direct_plan.profile_session_id}")
            # Even if session is missing, we'll still allow access
            plan = direct_plan
        elif session.username != current_user.username:
            print(f"[DEBUG] Permission denied: Plan owned by {session.username}, requested by {current_user.username}")
            raise HTTPException(status_code=403, detail="You don't have access to this transformation plan")
        else:
            print(f"[DEBUG] Permission check passed: plan owned by {session.username}")
            plan = direct_plan
    else:
        # For standalone plans (no profile_session_id), allow access with datapuur:read permission
        # This is already enforced by the endpoint's permission dependency
        print(f"[DEBUG] This is a standalone plan without profile_session_id")
        plan = direct_plan
    
    print(f"[DEBUG] Final access granted to plan: {plan.id}")
    import sys
    sys.stdout.flush()  # Force immediate output
    
    # Check ownership - for plans with profile_session_id already confirmed via the query
    # For standalone plans, verify ownership through plan creator or related messages
    if plan.profile_session_id is None:
        print(f"[DEBUG] This is a standalone plan (no profile session), checking permission model")
        # Standalone plans are accessible to the creator - usually tracked in metadata or messages
        # For now, we're allowing access to all users with datapuur:read permissions
        # to any standalone plan as a fallback case
        pass
    
    # Log activity
    log_activity(
        db=db,
        username=current_user.username,
        action="View Transformation Plan",
        details=f"Viewed transformation plan '{plan.name}'"
    )
    
    return TransformationPlanResponse(
        id=plan.id,
        profile_session_id=plan.profile_session_id,
        name=plan.name,
        description=plan.description,
        status=plan.status,
        transformation_steps=plan.transformation_steps or [],
        expected_improvements=plan.expected_improvements or {},
        transformation_script=plan.transformation_script,
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )

@router.get("/transformations", response_model=List[TransformationPlanResponse])
async def list_transformation_plans(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """List all transformation plans for the current user"""
    try:
        # Get all transformation plans for the current user
        # Since TransformationPlan doesn't have a direct username field,
        # we'll query for all plans associated with the user's sessions
        query = db.query(TransformationPlan).outerjoin(
            ProfileSession,
            TransformationPlan.profile_session_id == ProfileSession.id
        ).filter(
            # Only get plans associated with this user's sessions
            or_(
                ProfileSession.username == current_user.username,
                # Include standalone plans (those without a session)
                # If security requirements are strict, this condition could be removed
                TransformationPlan.profile_session_id == None
            )
        )
        
        # Apply pagination
        total = query.count()
        plans = query.order_by(TransformationPlan.created_at.desc()).\
            offset((page - 1) * limit).limit(limit).all()
        
        # Log the activity
        log_activity(
            db=db,
            username=current_user.username,
            action="list_transformation_plans",
            details={"page": page, "limit": limit, "count": len(plans)}
        )
        
        # Return response
        return [TransformationPlanResponse(
            id=plan.id,
            profile_session_id=plan.profile_session_id,
            name=plan.name,
            description=plan.description,
            status=plan.status,
            transformation_steps=plan.transformation_steps or [],
            expected_improvements=plan.expected_improvements or {},
            transformation_script=plan.transformation_script,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        ) for plan in plans]
    except Exception as e:
        logger.error(f"Error listing transformation plans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing transformation plans: {str(e)}")

@router.get("/sessions/by-file/{file_id}/plans")
async def get_profile_session_plans_by_file_id(
    file_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get the latest profile session for a file ID and its transformation plans"""
    try:
        # Find the latest profile session for this file
        profile_session = db.query(ProfileSession).filter(
            ProfileSession.file_id == file_id,
            ProfileSession.username == current_user.username
        ).order_by(ProfileSession.created_at.desc()).first()
        
        if not profile_session:
            return {"id": None, "file_id": file_id, "transformation_plans": []}
        
        # Get transformation plans for this session
        # Note: TransformationPlan doesn't have a username field, only connected via profile_session
        transformation_plans = db.query(TransformationPlan).filter(
            TransformationPlan.profile_session_id == profile_session.id
        ).all()
        
        # Format transformation plans for response
        plans_response = []
        for plan in transformation_plans:
            plans_response.append(TransformationPlanResponse(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                profile_session_id=plan.profile_session_id,
                status=plan.status,
                transformation_steps=plan.transformation_steps,
                expected_improvements=plan.expected_improvements,
                transformation_script=plan.transformation_script,
                created_at=plan.created_at,
                updated_at=plan.updated_at
            ))
        
        return ProfileSessionWithPlansResponse(
            id=profile_session.id,
            file_id=profile_session.file_id,
            transformation_plans=plans_response
        )
    except Exception as e:
        logger.error(f"Error getting profile session plans by file ID: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting profile session plans by file ID: {str(e)}")


@router.get("/transformations/by-source/{source_id}")
async def get_transformation_plans_by_source_id(
    source_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get transformation plans directly by source_id"""
    try:
        # Find transformation plans that match the source_id
        transformation_plans = db.query(TransformationPlan).filter(
            TransformationPlan.source_id == source_id
        ).all()
        
        # Format transformation plans for response
        plans_response = []
        for plan in transformation_plans:
            # Verify user has access to the plan via profile sessions
            if plan.profile_session_id:
                profile_session = db.query(ProfileSession).filter(
                    ProfileSession.id == plan.profile_session_id,
                    ProfileSession.username == current_user.username
                ).first()
                
                # Skip plans the user doesn't have access to
                if not profile_session:
                    continue
            
            plans_response.append(TransformationPlanResponse(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                profile_session_id=plan.profile_session_id,
                status=plan.status,
                transformation_steps=plan.transformation_steps,
                expected_improvements=plan.expected_improvements,
                transformation_script=plan.transformation_script,
                created_at=plan.created_at,
                updated_at=plan.updated_at
            ))
        
        return {"source_id": source_id, "transformation_plans": plans_response}
    except Exception as e:
        logger.error(f"Error getting transformation plans by source ID: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting transformation plans by source ID: {str(e)}")


def extract_schema_from_file(file_path: str) -> Dict[str, Any]:
    """Extract schema information from a data file when no profile session is available.
    
    Args:
        file_path: Path to the data file (supports CSV, Parquet, Excel)
        
    Returns:
        Dict with schema information in the format required by transformation_agent
    """
    schema_info = {}
    
    try:
        import pandas as pd
        import os
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return schema_info
        
        # Determine file type based on extension
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Read the first few rows to infer schema (limiting rows to optimize performance)
        if file_extension == '.csv':
            df = pd.read_csv(file_path, nrows=1000)
        elif file_extension in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path, nrows=1000)
        elif file_extension == '.parquet':
            df = pd.read_parquet(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_extension}")
            return schema_info
        
        # Extract schema information for each column
        for column in df.columns:
            # Get column data type
            pd_dtype = df[column].dtype
            if pd.api.types.is_numeric_dtype(pd_dtype):
                if pd.api.types.is_integer_dtype(pd_dtype):
                    dtype = 'integer'
                else:
                    dtype = 'float'
            elif pd.api.types.is_datetime64_dtype(pd_dtype):
                dtype = 'datetime'
            elif pd.api.types.is_bool_dtype(pd_dtype):
                dtype = 'boolean'
            else:
                dtype = 'string'
            
            # Check nullability
            nullable = df[column].isnull().any()
            
            # Add column schema info
            schema_info[column] = {
                'type': dtype,
                'nullable': nullable,
                'unique_count': df[column].nunique()
            }
        
        logger.info(f"Successfully extracted schema from file: {file_path}")
        return schema_info
    
    except Exception as e:
        logger.error(f"Error extracting schema from file: {str(e)}")
        import traceback
        traceback.print_exc()
        return schema_info


@router.post("/transformations/draft", response_model=TransformationPlanResponse)
async def create_draft_transformation_plan(
    request: TransformationPlanCreate,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Create a draft transformation plan using source data and AI generation"""
    print("====== DRAFT TRANSFORMATION PLAN CREATE ENDPOINT CALLED ======")
    print(f"Request received from user: {current_user.username}")
    print(f"Request data: {request.model_dump()}")
    
    try:
        print(f"[Transformation] Creating draft plan using AI agent")
        
        # Variables to store source details
        file_path = None
        profile_summary = ""
        quality_issues = []
        suggestions = []
        session = None  # Initialize session variable
        
        # Check if source ID is provided
        if request.source_id:
            # Try to get uploaded file details
            uploaded_file = db.query(UploadedFile).filter(
                UploadedFile.id == request.source_id,
                UploadedFile.uploaded_by == current_user.username
            ).first()
            
            if uploaded_file:
                print(f"[Transformation] Found source file: {uploaded_file.filename}")
                file_path = str(DATA_DIR / f'{uploaded_file.id}.parquet')
                
                # Check if this source has a profile
                # Look up the most recent profile session for this source
                profile_session = db.query(ProfileSession).filter(
                    ProfileSession.file_id == uploaded_file.id,
                    ProfileSession.username == current_user.username
                ).order_by(ProfileSession.created_at.desc()).first()
                
                if profile_session:
                    print(f"[Transformation] Found profile session: {profile_session.id}")
                    profile_summary = profile_session.profile_summary or ""
                    quality_issues = profile_session.data_quality_issues or []
                    suggestions = profile_session.improvement_suggestions or []
                    print(f"[Transformation] Using profile data - Issues: {len(quality_issues)}, Suggestions: {len(suggestions)}")
            else:
                logger.warning(f"File with ID {request.source_id} not found or not accessible by {current_user.username}")
        
        # Get user requirements
        user_requirements = request.description or "Create a basic data transformation plan"
        if request.input_instructions:
            user_requirements = f"{user_requirements}\n\n{request.input_instructions}"
        
        # Extract schema info from file if available and not already provided by profile session
        schema_info = {}
        if file_path and not schema_info:
            print(f"[Transformation] Extracting schema info from file: {file_path}")
            schema_info = extract_schema_from_file(file_path)
            print(f"[Transformation] Schema info extracted with {len(schema_info)} columns")

        print(f"[Transformation] Schema info: {schema_info}")
        # Generate the plan using the transformation agent
        plan_data = transformation_agent.create_transformation_plan(
            profile_summary=profile_summary,
            quality_issues=quality_issues,
            suggestions=suggestions,
            user_requirements=user_requirements,
            schema_info=schema_info
        )
        
        print(f"[Transformation] AI generated plan with {len(plan_data.get('steps', []))} steps")
        
        # Create plan record with AI-generated data
        # Before using the steps, ensure all transformation steps have valid parameters dictionary
        steps = plan_data.get("steps", [])
        for step in steps:
            # Ensure each step has a valid parameters dictionary
            if "parameters" not in step or step["parameters"] is None:
                step["parameters"] = {}  # Set default empty dict if missing or None
                
        plan_kwargs = {
            "name": request.name,
            "description": request.description or plan_data.get("description", "Data transformation plan"),
            "transformation_steps": steps,
            "expected_improvements": plan_data.get("expected_improvements", {})
        }
        
        # Store source ID if provided
        if request.source_id:
            plan_kwargs["source_id"] = request.source_id
        
        # Only add profile_session_id if provided
        if request.profile_session_id:
            plan_kwargs["profile_session_id"] = request.profile_session_id
            
            # Try to find the profile session if an ID was provided
            session = db.query(ProfileSession).filter(
                ProfileSession.id == request.profile_session_id,
                ProfileSession.username == current_user.username
            ).first()
            
            logger.info(f"Profile session lookup - ID: {request.profile_session_id}, Found: {session is not None}")
        
        # Create the plan
        plan = TransformationPlan(**plan_kwargs)
        plan.username = current_user.username
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        # Generate a transformation script for the plan
        try:
            if file_path:
                # We have a file path from the data source, use it for script generation
                print(f"[Transformation] Generating script using file path from data source: {file_path}")
                try:
                    # Extract filename from input path and construct output path in the data folder
                    import os
                    input_filename = os.path.basename(file_path)
                    # Get absolute project root directory
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    output_file_path = os.path.join(project_root, 'api', 'datapuur_ai', 'data', input_filename)
                    
                    # Ensure the output directory exists
                    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                    
                    # Retrieve profile data if available
                    profile_result = None
                    # Extract schema information if profile data is available
                    schema_info = {}
                    profile_summary = {}
                    
                    # Try to access profile data if uploaded_file exists
                    try:
                        if uploaded_file and hasattr(uploaded_file, 'id'):
                            # Try to get profile data from the database
                            profile_result = db.query(ProfileResult).filter(
                                ProfileResult.file_id == uploaded_file.id
                            ).first()
                            
                            if profile_result:
                                # Extract column schema information from column_profiles
                                if hasattr(profile_result, 'column_profiles') and profile_result.column_profiles:
                                    try:
                                        # Handle column_profiles if it's a dictionary
                                        if isinstance(profile_result.column_profiles, dict):
                                            for col_name, col_info in profile_result.column_profiles.items():
                                                schema_info[col_name] = {
                                                    'type': col_info.get('type', 'unknown'),
                                                    'nullable': col_info.get('missing_count', 0) > 0,
                                                    'unique_count': col_info.get('unique_count', 0),
                                                    'stats': col_info.get('statistics', {})
                                                }
                                        # Handle column_profiles if it's a list
                                        elif isinstance(profile_result.column_profiles, list):
                                            for col_item in profile_result.column_profiles:
                                                if isinstance(col_item, dict) and 'name' in col_item:
                                                    col_name = col_item.get('name')
                                                    schema_info[col_name] = {
                                                        'type': col_item.get('type', 'unknown'),
                                                        'nullable': col_item.get('missing_count', 0) > 0,
                                                        'unique_count': col_item.get('unique_count', 0),
                                                        'stats': col_item.get('statistics', {})
                                                    }
                                    except Exception as e:
                                        print(f"[Transformation] Error processing column profiles: {str(e)}")
                                        logger.error(f"Error processing column profiles: {str(e)}")
                                        # Continue with empty schema_info if we can't process the profiles
                                    
                                # Extract profile summary information from direct fields
                                profile_summary = {
                                    'total_rows': profile_result.total_rows if hasattr(profile_result, 'total_rows') else 0,
                                    'total_columns': profile_result.total_columns if hasattr(profile_result, 'total_columns') else 0,
                                    'exact_duplicates_count': profile_result.exact_duplicates_count if hasattr(profile_result, 'exact_duplicates_count') else 0,
                                    'fuzzy_duplicates_count': profile_result.fuzzy_duplicates_count if hasattr(profile_result, 'fuzzy_duplicates_count') else 0
                                }
                                
                                # Add column type distribution if available
                                if hasattr(profile_result, 'column_profiles') and profile_result.column_profiles:
                                    try:
                                        column_types = {}
                                        # Handle column_profiles if it's a dictionary
                                        if isinstance(profile_result.column_profiles, dict):
                                            for col_name, col_info in profile_result.column_profiles.items():
                                                col_type = col_info.get('type', 'unknown')
                                                if col_type in column_types:
                                                    column_types[col_type] += 1
                                                else:
                                                    column_types[col_type] = 1
                                        # Handle column_profiles if it's a list
                                        elif isinstance(profile_result.column_profiles, list):
                                            for col_item in profile_result.column_profiles:
                                                if isinstance(col_item, dict):
                                                    col_type = col_item.get('type', 'unknown')
                                                    if col_type in column_types:
                                                        column_types[col_type] += 1
                                                    else:
                                                        column_types[col_type] = 1
                                        profile_summary['column_types'] = column_types
                                    except Exception as e:
                                        print(f"[Transformation] Error processing column type distribution: {str(e)}")
                                        logger.error(f"Error processing column type distribution: {str(e)}")
                                        # Continue without column_types if we can't process the profiles
                                
                                print(f"[Transformation] Successfully extracted profile data for file ID: {uploaded_file.id}")
                            else:
                                print(f"[Transformation] Profile result not found for file ID: {uploaded_file.id}")
                    except Exception as profile_error:
                        # Log the error but continue without failing the whole transformation process
                        logger.error(f"Error processing profile data: {str(profile_error)}")
                        print(f"[Transformation] Could not process profile data: {str(profile_error)}")
                        import traceback
                        traceback.print_exc()  # Print stack trace for debugging
                    
                    # Generate transformation script with schema and profile information
                    script = transformation_agent.generate_transformation_script(
                        input_file_path=file_path,
                        transformation_steps=plan.transformation_steps,
                        output_file_path=output_file_path,
                        schema_info=schema_info,
                        profile_summary=profile_summary
                    )
                    plan.transformation_script = script
                    print(f"[Transformation] Script generated successfully with output to {output_file_path}, length: {len(script)}")
                    # Save the output path in the plan for reference
                    plan.output_file_path = output_file_path
                except Exception as script_error:
                    logger.error(f"Error generating script: {str(script_error)}")
                    plan.transformation_script = "# Error generating transformation script\n# Please try regenerating the script or contact support"
            else:
                # No source file path available, try session or use generic script
                if session and hasattr(session, 'file_path') and session.file_path:
                    print(f"[Transformation] Using file path from session: {session.file_path}")
                    try:
                        # Extract filename from session path and construct output path in the data folder
                        import os
                        import sys
                        input_filename = os.path.basename(session.file_path)
                        # Get absolute project root directory
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        output_file_path = os.path.join(project_root, 'api', 'datapuur_ai', 'data', input_filename)
                        
                        # Ensure the output directory exists
                        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                        
                        # Extract schema info from file if we don't have it from a profile
                        schema_info = {}
                        if session.file_path:
                            print(f"[Transformation] Extracting schema info from session file: {session.file_path}")
                            schema_info = extract_schema_from_file(session.file_path)
                            print(f"[Transformation] Schema info extracted with {len(schema_info)} columns")

                        script = transformation_agent.generate_transformation_script(
                            input_file_path=session.file_path,
                            transformation_steps=plan.transformation_steps,
                            output_file_path=output_file_path,
                            schema_info=schema_info
                        )
                        plan.transformation_script = script
                        print(f"[Transformation] Script generated successfully with output to {output_file_path} from session, length: {len(script)}")
                        # Save the output path in the plan for reference
                        plan.output_file_path = output_file_path
                    except Exception as script_error:
                        logger.error(f"Error generating script from session: {str(script_error)}")
                        plan.transformation_script = "# Error generating transformation script\n# Please try regenerating the script"
                else:
                    # No file path available, generate a generic script
                    print(f"[Transformation] No file path available, generating generic script")
                    try:
                        generic_input = "input.parquet (assumed format)"
                        script = transformation_agent.generate_transformation_script(
                            input_file_path=generic_input,
                            transformation_steps=plan.transformation_steps
                        )
                        plan.transformation_script = script
                        print(f"[Transformation] Generic script generated successfully")
                    except Exception as e:
                        logger.error(f"Error generating generic script: {str(e)}")
                        plan.transformation_script = "# Transformation plan\n# Add a data source to generate a complete script tailored to your data"
        except Exception as e:
            logger.error(f"Unexpected error in script generation: {str(e)}")
            plan.transformation_script = "# Draft transformation plan\n# Error occurred during script generation"
        
        db.add(plan)
        db.commit()
        
        return TransformationPlanResponse(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            profile_session_id=plan.profile_session_id,
            transformation_steps=plan.transformation_steps,
            expected_improvements=plan.expected_improvements,
            transformation_script=plan.transformation_script,
            status=plan.status,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating draft transformation plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating draft transformation plan: {str(e)}")

@router.post("/transformations", response_model=TransformationPlanResponse)
async def create_transformation_plan(
    request: TransformationPlanCreate,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    print("====== TRANSFORMATION PLAN CREATE ENDPOINT CALLED ======")
    print(f"Request received from user: {current_user.username}")
    print(f"Request data: {request.dict()}")
    import sys
    sys.stdout.flush()  # Force immediate output
    """Create a complete transformation plan with script using the agent"""
    session = None
    
    # Only try to find the profile session if an ID was provided
    if request.profile_session_id:
        session = db.query(ProfileSession).filter(
            ProfileSession.id == request.profile_session_id,
            ProfileSession.username == current_user.username
        ).first()
        
        logger.info(f"Profile session lookup - ID: {request.profile_session_id}, Found: {session is not None}")
    
    # We'll continue even if no session is found - profile session is optional
    
    try:
        print(f"[Transformation] Starting plan creation for user: {current_user.username}")
        print(f"[Transformation] Plan name: {request.name}")
        print(f"[Transformation] Profile session ID: {request.profile_session_id or 'None'}")
        
        # Combine user description and chat instructions if provided
        user_requirements = request.description or ""
        if request.input_instructions:
            user_requirements = f"{user_requirements}\n\n{request.input_instructions}"
            print(f"[Transformation] Instructions provided, length: {len(request.input_instructions)}")
            
        # Generate transformation plan using AI
        print(f"[Transformation] Creating complete plan with AI processing")
        profile_summary = ""
        quality_issues = []
        suggestions = []
        
        # Use session data if available
        if session:
            print(f"[Transformation] Using profile session data: {session.id}")
            profile_summary = session.profile_summary or ""
            quality_issues = session.data_quality_issues or []
            suggestions = session.improvement_suggestions or []
            print(f"[Transformation] Profile data loaded - Issues: {len(quality_issues)}, Suggestions: {len(suggestions)}")
        
        print(f"[Transformation] Calling AI agent to create transformation plan...")
        plan_data = transformation_agent.create_transformation_plan(
            profile_summary=profile_summary,
            quality_issues=quality_issues,
            suggestions=suggestions,
            user_requirements=user_requirements
        )
        print(f"[Transformation] AI plan generated with {len(plan_data.get('steps', []))} steps")
        
        # Create plan record
        # Ensure transformation steps have valid parameters
        transformation_steps = plan_data.get("steps", [])
        for step in transformation_steps:
            # Ensure each step has a valid parameters dictionary
            parameters = step.get("parameters")
            
            # Check if parameters is None or not a dictionary
            if parameters is None or not isinstance(parameters, dict):
                # If it's a list, convert it to a dictionary with numeric keys
                if isinstance(parameters, list):
                    param_dict = {}
                    for i, item in enumerate(parameters):
                        param_dict[f"item_{i}"] = item
                    step["parameters"] = param_dict
                else:
                    # For None or any other type, use empty dictionary
                    step["parameters"] = {}
                    
                # Log the conversion for debugging
                logger.debug(f"Converted parameters from {type(parameters).__name__} to dict in step: {step.get('operation')}")
                
        # Create new plan record with optional profile_session_id
        plan_kwargs = {
            "name": request.name or plan_data.get("name", "Transformation Plan"),
            "description": request.description or plan_data.get("description", ""),
            "transformation_steps": transformation_steps,
            "expected_improvements": plan_data.get("expected_improvements", {})
        }
        
        # Only add profile_session_id if provided
        if request.profile_session_id:
            plan_kwargs["profile_session_id"] = request.profile_session_id
        
        # Create the plan and add it to the database
        plan = TransformationPlan(**plan_kwargs)
        db.add(plan)
        print(f"[Transformation] Created new plan")
        print(f"[Transformation] Plan added to database with ID: {plan.id}")
        
        # Always generate a transformation script for the plan
        if plan.transformation_steps:
            # Generate initial script if we have a session with file path
            if session and session.file_path:
                print(f"[Transformation] Generating script using file path: {session.file_path}")
                try:
                    # Extract filename and prepare output path
                    import os
                    base_filename = os.path.basename(session.file_path)
                    filename_no_ext = os.path.splitext(base_filename)[0]
                    output_file_path = os.path.join('api/datapuur_ai/data', base_filename)
                    
                    # Ensure the output directory exists
                    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                    
                    
                    script = transformation_agent.generate_transformation_script(
                        input_file_path=session.file_path,
                        transformation_steps=plan.transformation_steps,
                        output_file_path=output_file_path
                    )
                    plan.transformation_script = script
                    plan.source_id = filename_no_ext
                    plan.output_file_path = output_file_path
                    print(f"[Transformation] Script generation successful with output to {output_file_path} from session, length: {len(script)}")
                    print(session.file_path)
                    
                except Exception as script_error:
                    logger.error(f"Error generating script: {str(script_error)}")
                    plan.transformation_script = "# Error generating transformation script\n# Please try regenerating the script or contact support"
            else:
                # No file path available, use best-effort generic script
                print(f"[Transformation] No file path available, generating generic script")
                try:
                    # Generate a generic script with assumptions about the data format
                    generic_input = "input.parquet"
                    generic_output = "api/datapuur_ai/data/output.parquet"
                    
                    # Ensure the output directory exists
                    import os
                    os.makedirs(os.path.dirname(generic_output), exist_ok=True)
                    
                    # For generic scripts, we may not have a real input file to extract schema from
                    # but we should still try if the generic_input exists
                    schema_info = {}
                    if os.path.exists(generic_input):
                        print(f"[Transformation] Extracting schema info from generic input file: {generic_input}")
                        schema_info = extract_schema_from_file(generic_input)
                        print(f"[Transformation] Schema info extracted with {len(schema_info)} columns")

                    script = transformation_agent.generate_transformation_script(
                        input_file_path=generic_input,
                        transformation_steps=plan.transformation_steps,
                        output_file_path=generic_output,
                        schema_info=schema_info
                    )
                    plan.transformation_script = script
                    plan.output_file_path = generic_output
                    print(f"[Transformation] Generic script generated with output to {generic_output}")
                    
                except Exception:
                    plan.transformation_script = "# Transformation plan\n# Add a data source to generate a complete script tailored to your data"
        else:
            # Just add a placeholder script for drafts
            plan.transformation_script = "# Draft transformation plan\n# Edit this script or use the AI assistant to generate transformations"
        
        # First commit the plan to get a valid ID
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        # Store the chat instructions as user message if provided
        if request.input_instructions:
            user_message = TransformationMessage(
                plan_id=plan.id,
                role="user",
                content=request.input_instructions,
                message_metadata={"source": "chat"}
            )
            db.add(user_message)
            
        # Now add initial message with the valid plan.id
        initial_message = TransformationMessage(
            plan_id=plan.id,  # Now plan.id is valid
            role="assistant",
            content=f"I've created a transformation plan with {len(plan.transformation_steps)} steps. The plan will {plan.description}",
            message_metadata={
                "steps": plan.transformation_steps,
                "script": plan.transformation_script,
                "is_final_plan": True
            }
        )
        db.add(initial_message)
        db.commit()
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Create transformation plan",
            details=f"Created transformation plan: {plan.name}"
        )
        
        print(f"[Transformation] Plan creation completed successfully")
        print(f"[Transformation] Returning plan with ID: {plan.id}, Steps: {len(plan.transformation_steps)}")
        
        # Return the transformation plan
        return TransformationPlanResponse(
            id=plan.id,
            profile_session_id=plan.profile_session_id,
            name=plan.name,
            description=plan.description,
            status=plan.status,
            transformation_steps=plan.transformation_steps,
            expected_improvements=plan.expected_improvements,
            transformation_script=plan.transformation_script,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating transformation plan: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error creating transformation plan: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error creating transformation plan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Transformation Chat Endpoints
@router.post("/transformation-messages", response_model=TransformationChatResponse)
async def create_transformation_message(
    request: TransformationMessageCreate,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Create a chat message for transformation plan refinement"""
    try:
        plan = None
        session = None
        print("request.plan_id", request.plan_id)
        # Check if we have a valid plan_id or profile_session_id
        if request.plan_id:
            # First try to get plan without joining ProfileSession
            plan = db.query(TransformationPlan).filter(
                TransformationPlan.id == request.plan_id
            ).first()
            
            # If plan exists, verify ownership by checking username in profile_session if it exists
            if plan:
                if plan.profile_session_id:
                    # If plan has a profile session, verify ownership
                    profile_session = db.query(ProfileSession).filter(
                        ProfileSession.id == plan.profile_session_id,
                        ProfileSession.username == current_user.username
                    ).first()
                    
                    if not profile_session:
                        # If profile session exists but doesn't belong to current user
                        logger.warning(f"Profile session {request.profile_session_id} not found, but continuing")
                else:
                    # For plans without profile_session_id, we'll assume they belong to the current user
                    # (This is safe as they were created in this session)
                    pass
            else:
                # Plan doesn't exist
                raise HTTPException(status_code=404, detail="Transformation plan not found")
                
            session = plan.profile_session
        elif request.profile_session_id:
            # For initial messages before plan creation
            session = db.query(ProfileSession).filter(
                ProfileSession.id == request.profile_session_id,
                ProfileSession.username == current_user.username
            ).first()
            
            # Make profile session validation optional - don't error if session not found
            # This allows transformation messages to work without requiring a profile session
            if not session:
                logger.warning(f"Profile session {request.profile_session_id} not found, but continuing")
                # No need to raise an exception, just proceed without the session
        else:
            raise HTTPException(status_code=400, detail="Either plan_id or profile_session_id is required")
        
        plan_id = request.plan_id
        
        # Create user message with valid plan_id
        user_message = TransformationMessage(
            plan_id=plan_id,
            role=request.role,
            content=request.content,
            message_metadata={"source": "chat"}
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # Generate AI response
        response_content = ""
        metadata = {}
        transformation_steps = None
        script = None
        
        if plan:
            # If we have a plan, use its context for AI response
            # Get profile information if we have a session, otherwise use defaults
            profile_summary = ""
            data_quality_issues = []
            
            if session:
                profile_summary = session.profile_summary or ""
                data_quality_issues = session.data_quality_issues or []
            
            # Create a simplified plan structure for the transformation agent
            # This ensures we're passing a dict structure that the agent expects
            current_plan = {
                "steps": plan.transformation_steps or [],
                "name": plan.name or "Transformation Plan",
                "description": plan.description or ""
            }
            
            # Store the previous steps for comparison after update
            previous_steps = copy.deepcopy(plan.transformation_steps) or []
            
            try:
                # Extract schema information if session has a file path
                schema_info = {}
                if session and hasattr(session, 'file_path') and session.file_path:
                    print(f"[Transformation] Extracting schema for plan refinement from: {session.file_path}")
                    schema_info = extract_schema_from_file(session.file_path)
                    print(f"[Transformation] Schema extracted with {len(schema_info)} columns for plan refinement")
                
                # The refine_transformation_plan method takes current_plan (as a dict) and refinement_request
                response_data = transformation_agent.refine_transformation_plan(
                    current_plan=current_plan,
                    refinement_request=request.content,
                    schema_info=schema_info
                )
            except Exception as e:
                logger.error(f"Error in transformation agent: {str(e)}")
                # If transformation fails, return a simplified response
                response_data = current_plan
            
            # Get a meaningful response for the user
            response_content = "I've updated the transformation plan according to your feedback."
            
            # Extract the steps from the response data
            # The response format may be a dict with a 'steps' key, or the original structure
            if isinstance(response_data, dict) and 'steps' in response_data:
                transformation_steps = response_data['steps']
            else:
                # If we didn't get the expected format, try using it directly or keep original steps
                transformation_steps = response_data if isinstance(response_data, list) else plan.transformation_steps
                
            # Validate and convert transformation steps to ensure they match the required schema
            validated_steps = []
            if transformation_steps and isinstance(transformation_steps, list):
                for i, step in enumerate(transformation_steps):
                    # Convert potentially misformatted steps to match our schema
                    valid_step = {
                        "order": step.get("order", step.get("id", i+1)),
                        "operation": step.get("operation", step.get("action", "transform")),
                        "description": step.get("description", step.get("name", f"Transformation step {i+1}")),
                        "parameters": step.get("parameters", {})
                    }
                    validated_steps.append(valid_step)
                    
                # Use validated steps if we have any, otherwise fall back to original plan steps
                transformation_steps = validated_steps if validated_steps else plan.transformation_steps
            
            # Generate updated script if we have new transformation steps and a file path available
            script = None
            if transformation_steps and transformation_steps != previous_steps:
                # Try to get file path from session for script generation
                file_path = None
                if session and hasattr(session, 'file_path') and session.file_path:
                    file_path = session.file_path
                    print(f"[Transformation] Found file path for script refinement: {file_path}")
                    
                    # Refine existing transformation script based on steps changes and user message
                    try:
                        # Get existing script or create empty placeholder if none exists
                        current_script = plan.transformation_script if plan.transformation_script else f"# Transformation for {file_path}\n# Initial script placeholder\n"
                        
                        # Combine step changes info with user request message for context
                        refinement_context = f"Updated transformation steps: {json.dumps(transformation_steps, indent=2)}\n\nUser message: {request.content}"
                        
                        # Get file ID from plan if available
                        file_id = None
                        if hasattr(plan, 'file_id') and plan.file_id:
                            file_id = plan.file_id
                        
                        # Retrieve profile data if available
                        profile_result = None
                        # Extract schema information if profile data is available
                        schema_info = {}
                        profile_summary = {}
                        
                        try:
                            if file_id:
                                # Try to get profile data from the database
                                profile_result = db.query(ProfileResult).filter(
                                    ProfileResult.file_id == file_id
                                ).first()
                                
                                if profile_result:
                                    # Extract column schema information from column_profiles
                                    if hasattr(profile_result, 'column_profiles') and profile_result.column_profiles:
                                        try:
                                            # Handle column_profiles if it's a dictionary
                                            if isinstance(profile_result.column_profiles, dict):
                                                for col_name, col_info in profile_result.column_profiles.items():
                                                    schema_info[col_name] = {
                                                        'type': col_info.get('type', 'unknown'),
                                                        'nullable': col_info.get('missing_count', 0) > 0,
                                                        'unique_count': col_info.get('unique_count', 0),
                                                        'stats': col_info.get('statistics', {})
                                                    }
                                            # Handle column_profiles if it's a list
                                            elif isinstance(profile_result.column_profiles, list):
                                                for col_item in profile_result.column_profiles:
                                                    if isinstance(col_item, dict) and 'name' in col_item:
                                                        col_name = col_item.get('name')
                                                        schema_info[col_name] = {
                                                            'type': col_item.get('type', 'unknown'),
                                                            'nullable': col_item.get('missing_count', 0) > 0,
                                                            'unique_count': col_item.get('unique_count', 0),
                                                            'stats': col_item.get('statistics', {})
                                                        }
                                        except Exception as e:
                                            print(f"[Transformation] Error processing column profiles in message creation: {str(e)}")
                                            logger.error(f"Error processing column profiles in message creation: {str(e)}")
                                            # Continue with empty schema_info if we can't process the profiles
                                        
                                    # Extract profile summary information from direct fields
                                    profile_summary = {
                                        'total_rows': profile_result.total_rows if hasattr(profile_result, 'total_rows') else 0,
                                        'total_columns': profile_result.total_columns if hasattr(profile_result, 'total_columns') else 0,
                                        'exact_duplicates_count': profile_result.exact_duplicates_count if hasattr(profile_result, 'exact_duplicates_count') else 0,
                                        'fuzzy_duplicates_count': profile_result.fuzzy_duplicates_count if hasattr(profile_result, 'fuzzy_duplicates_count') else 0
                                    }
                                    
                                    # Add column type distribution if available
                                    if hasattr(profile_result, 'column_profiles') and profile_result.column_profiles:
                                        try:
                                            column_types = {}
                                            # Handle column_profiles if it's a dictionary
                                            if isinstance(profile_result.column_profiles, dict):
                                                for col_name, col_info in profile_result.column_profiles.items():
                                                    col_type = col_info.get('type', 'unknown')
                                                    if col_type in column_types:
                                                        column_types[col_type] += 1
                                                    else:
                                                        column_types[col_type] = 1
                                            # Handle column_profiles if it's a list
                                            elif isinstance(profile_result.column_profiles, list):
                                                for col_item in profile_result.column_profiles:
                                                    if isinstance(col_item, dict):
                                                        col_type = col_item.get('type', 'unknown')
                                                        if col_type in column_types:
                                                            column_types[col_type] += 1
                                                        else:
                                                            column_types[col_type] = 1
                                            profile_summary['column_types'] = column_types
                                        except Exception as e:
                                            print(f"[Transformation] Error processing column type distribution in message creation: {str(e)}")
                                            logger.error(f"Error processing column type distribution in message creation: {str(e)}")
                                            # Continue without column_types if we can't process the profiles
                                    
                                    print(f"[Transformation] Successfully extracted profile data for file ID: {file_id}")
                                else:
                                    print(f"[Transformation] Profile result not found for file ID: {file_id}")
                        except Exception as profile_error:
                            # Log the error but continue without failing the whole transformation process
                            logger.error(f"Error processing profile data in message handler: {str(profile_error)}")
                            print(f"[Transformation] Could not process profile data in message handler: {str(profile_error)}")
                        
                        # Refine the script using the agent with schema and profile data
                        script = transformation_agent.refine_transformation_script(
                            current_script=current_script,
                            refinement_request=refinement_context,
                            schema_info=schema_info,
                            profile_summary=profile_summary
                        )
                        print(f"[Transformation] Successfully refined transformation script")
                    except Exception as script_error:
                        logger.error(f"Error refining transformation script: {str(script_error)}")
                        # Fallback to existing script if available
                        script = plan.transformation_script if hasattr(plan, 'transformation_script') else None
                else:
                    # No file path available, keep existing script or add placeholder
                    script = plan.transformation_script if hasattr(plan, 'transformation_script') else "# Updated transformation plan\n# Add a data source to generate complete transformations"
                    print(f"[Transformation] No file path available, using existing or placeholder script")
            else:
                # No changes to steps, keep existing script
                script = plan.transformation_script if hasattr(plan, 'transformation_script') else None
            
            # Update plan with new steps and script
            if transformation_steps:
                plan.transformation_steps = transformation_steps
            
            if script:
                plan.transformation_script = script
                
            db.add(plan)
            
            # Safely handle metadata creation for draft plans that might have missing/null fields
            metadata = {"steps": []}
            
            # Add transformation steps if available
            if transformation_steps:
                metadata["steps"] = transformation_steps
            elif plan.transformation_steps:
                metadata["steps"] = plan.transformation_steps
                
            # Identify changes between previous and new steps
            # Always create a changes object even if empty to ensure consistent structure
            added = []
            modified = []
            removed = []
            
            if previous_steps and transformation_steps:
                # Map steps by order/ID for easier comparison
                prev_steps_map = {step.get("order", i): step for i, step in enumerate(previous_steps)}
                new_steps_map = {step.get("order", i): step for i, step in enumerate(transformation_steps)}
                
                # Identify added, modified, and removed steps
                all_step_ids = set(list(prev_steps_map.keys()) + list(new_steps_map.keys()))
                
                for step_id in all_step_ids:
                    if step_id not in prev_steps_map:
                        added.append(new_steps_map[step_id])
                    elif step_id not in new_steps_map:
                        removed.append(prev_steps_map[step_id])
                    elif prev_steps_map[step_id] != new_steps_map[step_id]:
                        modified.append({
                            "previous": prev_steps_map[step_id],
                            "current": new_steps_map[step_id]
                        })
            
            # If this is the first message, consider all steps as added
            elif not previous_steps and transformation_steps:
                added = transformation_steps
                
            # Always include changes object in metadata
            metadata["changes"] = {
                "added": added,
                "modified": modified,
                "removed": removed
            }
                
            # Add script if available
            if script:
                metadata["script"] = script
            elif hasattr(plan, 'transformation_script') and plan.transformation_script:
                metadata["script"] = plan.transformation_script
        else:
            # Just acknowledge receipt without plan context
            response_content = "I've noted your requirements for the transformation plan. When you're ready, you can create the plan to generate a full transformation strategy."
        
        # Create assistant response message with explicit changes in metadata
        # Ensure the changes are at the top level of the metadata for easier access in the frontend
        message_metadata = {}
        
        # Include steps information
        if "steps" in metadata:
            message_metadata["steps"] = metadata["steps"]
            
        # Include script if available
        if "script" in metadata:
            message_metadata["script"] = metadata["script"]
            
        # Make sure changes are at the top level of metadata
        if "changes" in metadata:
            print(f"DEBUG: Changes metadata structure present")
            message_metadata["changes"] = metadata["changes"]
        
        # Create the assistant message
        assistant_message = TransformationMessage(
            plan_id=request.plan_id,
            role="assistant",
            content=response_content,
            message_metadata=message_metadata
        )
        db.add(assistant_message)
        
        # Log activity
        log_activity(
            db=db,
            username=current_user.username,
            action="Transformation Chat Message",
            details={"plan_id": request.plan_id, "session_id": request.profile_session_id}
        )
        
        db.commit()
        db.refresh(assistant_message)
        
        # Convert SQLAlchemy model to Pydantic schema
        message_response = ProfileMessageSchema(
            id=assistant_message.id,
            role=assistant_message.role,
            content=assistant_message.content,
            timestamp=assistant_message.timestamp,
            metadata=assistant_message.message_metadata
        )
        
        # The changes are already in the assistant message metadata via the message_response
        # which was created from assistant_message.message_metadata
        # No need to add it again, just return the response directly
        # Include the script in the response if it was generated or updated
        return TransformationChatResponse(
            message=message_response,
            plan_status=plan.status if plan else "draft",
            transformation_steps=transformation_steps or (plan.transformation_steps if plan else None),
            generated_script=script or (plan.transformation_script if plan else None)
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating transformation message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get transformation plan messages
@router.get("/transformation-plans/{plan_id}/messages", response_model=List[ProfileMessageSchema])
async def get_transformation_plan_messages(
    plan_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get all chat messages for a transformation plan"""
    try:
        # Verify plan belongs to the current user
        plan = db.query(TransformationPlan).join(
            ProfileSession,
            TransformationPlan.profile_session_id == ProfileSession.id
        ).filter(
            TransformationPlan.id == plan_id,
            ProfileSession.username == current_user.username
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Transformation plan not found")
        
        # Get all messages for the plan
        messages = db.query(TransformationMessage).filter(
            TransformationMessage.plan_id == plan_id
        ).order_by(TransformationMessage.timestamp).all()
        
        # Convert SQLAlchemy models to Pydantic schemas
        return [
            ProfileMessageSchema(
                id=message.id,
                role=message.role,
                content=message.content,
                timestamp=message.timestamp,
                metadata=message.message_metadata
            ) for message in messages
        ]
    
    except Exception as e:
        logger.error(f"Error getting transformation messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Script Execution Endpoints
@router.post("/execute", response_model=ExecuteScriptResponse)
async def execute_script(
    request: ExecuteScriptRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Execute a generated script"""
    try:
        # Validate and clean script
        validation = script_executor.validate_script(request.script)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Script validation failed: {', '.join(validation['issues'])}"
            )
        
        # Use the cleaned script version
        script_to_execute = validation["cleaned_script"]
        
        # Get file path from session or plan
        file_path = None
        if request.session_id:
            session = db.query(ProfileSession).filter(
                ProfileSession.id == request.session_id
            ).first()
            if session:
                file_path = session.file_path
        elif request.plan_id:
            plan = db.query(TransformationPlan).filter(
                TransformationPlan.id == request.plan_id
            ).first()
            if plan :
                file_path = str(DATA_DIR / f'{plan.source_id}.parquet')
        
        if not file_path:
            raise HTTPException(status_code=400, detail="Could not determine input file")
        
        # Create job record
        job = ProfileJob(
            job_type=request.job_type,
            session_id=request.session_id,
            plan_id=request.plan_id,
            status="pending",
            script=request.script,
            input_file_path=file_path,
            created_by=current_user.username
        )
        db.add(job)
        db.commit()
        
        # Schedule background task
        background_tasks.add_task(
            execute_script_background,
            job_id=job.id,
            script=script_to_execute,  # Use cleaned script instead of original
            file_path=file_path,
            job_type=request.job_type
        )
        
        return ExecuteScriptResponse(
            job_id=job.id,
            status="pending",
            message="Script execution started"
        )
        
    except Exception as e:
        db.rollback()
        error_traceback = traceback.format_exc()
        
        # Log detailed error information
        logger.error(f"[BACKGROUND JOB] Error executing script: {str(e)}")
        logger.error(f"[BACKGROUND JOB] Error traceback: {error_traceback}")
        
        # Log additional context
        script_length = len(request.script) if request.script else 0
        logger.error(f"[BACKGROUND JOB] Script length: {script_length} characters")
        logger.error(f"[BACKGROUND JOB] Job type: {request.job_type}")
        logger.error(f"[BACKGROUND JOB] Session ID: {request.session_id}")
        logger.error(f"[BACKGROUND JOB] Plan ID: {request.plan_id}")
        logger.error(f"[BACKGROUND JOB] File path: {file_path if 'file_path' in locals() else 'Not determined yet'}")
        
        # Include more details in the HTTP exception
        error_detail = {
            "message": f"Script execution failed: {str(e)}",
            "error_type": type(e).__name__,
            "context": {
                "job_type": request.job_type,
                "session_id": request.session_id,
                "plan_id": request.plan_id
            }
        }
        
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get job execution status"""
    job = db.query(ProfileJob).filter(
        ProfileJob.id == job_id,
        ProfileJob.created_by == current_user.username
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        message=job.message,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at
    )


# Background task function
async def execute_script_background(job_id: str, script: str, file_path: str, job_type: str):
    """Execute script in background"""
    db = SessionLocal()
    try:
        # Update job status
        job = db.query(ProfileJob).filter(ProfileJob.id == job_id).first()
        if not job:
            return
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Execute script with job_id for context and logging
        if job_type == "transformation":
            logger.info(f"[BACKGROUND JOB {job_id}] Executing transformation script")
            result = await script_executor.execute_transformation(
                script=script,
                input_file=file_path,
                job_id=job_id
            )
        else:
            logger.info(f"[BACKGROUND JOB {job_id}] Executing regular script")
            result = await script_executor.execute_script(
                script=script,
                input_file_path=file_path,
                job_id=job_id  # Pass job_id for context and logging
            )
        
        # Update job with results
        job.status = "completed" if result.get("success") else "failed"
        job.completed_at = datetime.utcnow()
        
        # Store any captured messages for logs
        if result.get("messages"):
            if not job.result:
                job.result = {}
            job.result["execution_logs"] = result.get("messages")
        
        # Store statistics if available
        if result.get("statistics"):
            if not job.result:
                job.result = {}
            job.result["statistics"] = result.get("statistics")
        
        # Store error if any
        job.error = result.get("error")
        
        # Store output file path
        job.output_file_path = result.get("output_file_path")
        
        # Log completion
        logger.info(f"Job {job_id} completed with status: {job.status}")
        if job.output_file_path:
            logger.info(f"Output saved to: {job.output_file_path}")
        if job.error:
            logger.error(f"Job error: {job.error}")
        
        # Update related records
        if job_type == "transformation" and job.plan_id and result.get("success"):
            plan = db.query(TransformationPlan).filter(
                TransformationPlan.id == job.plan_id
            ).first()
            if plan:
                plan.status = "completed"
                plan.output_file_path = result.get("full_output_path")
                plan.output_file_id = result.get("output_file_id")
                plan.execution_output = result
                
                # Create transformed dataset record
                try:
                    # Extract source file name for dataset name
                    dataset_name = plan.name
                    
                    # Extract source file name from path
                    import os
                    source_filename = os.path.basename(job.input_file_path) if job.input_file_path else "unknown"
                    
                    # Create the transformed dataset record
                    transformed_dataset = TransformedDataset(
                        name=dataset_name,
                        description=f"Transformed from {dataset_name}",
                        source_file_path=job.input_file_path,
                        transformed_file_path=result.get("output_file_path"),
                        transformation_plan_id=plan.id,
                        job_id=job.id,
                        created_by=job.created_by,
                        metadata={
                            "transformation_date": datetime.utcnow().isoformat(),
                            "source_file": source_filename,
                        },
                        column_metadata={}  # Will be populated during statistics calculation
                    )
                    import os
                    import pandas as pd
                    # Calculate statistics from the output file
                    output_path = result.get("full_output_path")
                    if output_path and os.path.exists(output_path):
                        try:
                            # Calculate file size in bytes
                            file_size = os.path.getsize(output_path)
                            transformed_dataset.file_size_bytes = file_size
                            
                            # Determine file type and read
                            if str(output_path).endswith('.parquet'):
                                df_output = pd.read_parquet(output_path)
                            elif str(output_path).endswith('.csv'):
                                df_output = pd.read_csv(output_path)
                            elif str(output_path).endswith(('.xls', '.xlsx')):
                                df_output = pd.read_excel(output_path)
                            else:
                                logger.warning(f"Unsupported output file format for statistics calculation: {output_path}")
                                df_output = None
                                
                            if df_output is not None:
                                # Calculate basic statistics
                                row_count = len(df_output)
                                column_count = len(df_output.columns)
                                
                                # Create stats dictionary
                                stats = {
                                    "row_count": row_count,
                                    "column_count": column_count,
                                    "file_size_bytes": file_size,
                                    "columns": list(df_output.columns),
                                    "dtypes": {
                                        col: str(df_output[col].dtype) for col in df_output.columns
                                    },
                                    "missing_values": {
                                        col: int(df_output[col].isna().sum()) for col in df_output.columns
                                    },
                                    "total_missing": int(df_output.isna().sum().sum())
                                }
                                
                                # Update dataset with statistics
                                transformed_dataset.row_count = row_count
                                transformed_dataset.column_count = column_count
                                transformed_dataset.data_summary = stats
                                
                                # Populate column_metadata with column information
                                column_metadata = {}
                                for col in df_output.columns:
                                    dtype = str(df_output[col].dtype)
                                    # Get sample data (first few non-null values)
                                    sample_data = df_output[col].dropna().head(3).tolist()
                                    sample_str = str(sample_data)[:50] + "..." if len(str(sample_data)) > 50 else str(sample_data)
                                    
                                    # For numeric columns, add additional statistics
                                    stats_info = {}
                                    if pd.api.types.is_numeric_dtype(df_output[col]):
                                        stats_info = {
                                            "min": float(df_output[col].min()) if not pd.isna(df_output[col].min()) else None,
                                            "max": float(df_output[col].max()) if not pd.isna(df_output[col].max()) else None,
                                            "mean": float(df_output[col].mean()) if not pd.isna(df_output[col].mean()) else None,
                                            "median": float(df_output[col].median()) if not pd.isna(df_output[col].median()) else None
                                        }
                                    
                                    # For string columns, add length statistics
                                    elif pd.api.types.is_string_dtype(df_output[col]):
                                        non_null_values = df_output[col].dropna()
                                        if len(non_null_values) > 0:
                                            stats_info = {
                                                "avg_length": float(non_null_values.str.len().mean()),
                                                "max_length": int(non_null_values.str.len().max()),
                                                "unique_values": min(int(non_null_values.nunique()), 1000)  # Cap at 1000
                                            }
                                    
                                    column_metadata[col] = {
                                        "name": col,
                                        "type": dtype,
                                        "description": "",  # Empty description to be filled by user later
                                        "missing_count": int(df_output[col].isna().sum()),
                                        "missing_percentage": float(df_output[col].isna().sum() / len(df_output) * 100),
                                        "sample_data": sample_str,
                                        "stats": stats_info
                                    }
                                
                                transformed_dataset.column_metadata = column_metadata
                                
                                logger.info(f"Calculated statistics for transformed dataset: {row_count} rows, {column_count} columns, {file_size} bytes")
                        except Exception as stats_error:
                            logger.error(f"Error calculating statistics: {str(stats_error)}")
                    # If statistics calculation failed, try to use any provided statistics from the result
                    elif result.get("statistics"):
                        stats = result.get("statistics")
                        transformed_dataset.row_count = stats.get("row_count")
                        transformed_dataset.column_count = stats.get("column_count")
                        transformed_dataset.data_summary = stats
                    
                    db.add(transformed_dataset)
                    logger.info(f"Created transformed dataset record: {transformed_dataset.id}")
                except Exception as e:
                    logger.error(f"Failed to create transformed dataset record: {e}")
                    # Continue execution, don't fail the job because of this
        
        db.commit()
        
    except Exception as e:
        # Use exception info for detailed error logging
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Error in background script execution: {error_msg}")
        logger.error(f"Traceback: {error_traceback}")
        
        # Update job status if job exists
        if 'job' in locals() and job:
            job.status = "failed"
            job.error = error_msg
            job.completed_at = datetime.utcnow()
            
            # Store error details in result
            if not job.result:
                job.result = {}
            job.result["error_details"] = {
                "error": error_msg,
                "traceback": error_traceback
            }
            
            db.commit()
    finally:
        db.close()


# Data Sources Endpoints
@router.get("/datasources", response_model=List[DataSourceResponse])
async def list_datasources(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """List available data sources for AI transformation"""
    
    # Connect to the profiler service to get available data sources
    from api.profiler.router import get_profiler_service
    profiler_service = get_profiler_service()
    
    # Get data sources from the profiler service
    try:
        offset = (page - 1) * limit
        data_files = profiler_service.list_data_files(limit=limit, offset=offset)
        
        # Convert to response model
        result = []
        for file in data_files:
            # Check if file has a profile
            profile_result = db.query(ProfileResult).filter(
                ProfileResult.file_id == file.get("id")
            ).first()
            
            result.append(DataSourceResponse(
                id=file.get("id", ""),
                name=file.get("name", ""),
                file_path=file.get("path", ""),
                file_size=file.get("size", 0),
                row_count=file.get("row_count"),
                column_count=file.get("column_count"),
                created_at=file.get("created_at") or datetime.utcnow(),
                updated_at=file.get("updated_at"),
                data_type=file.get("type", "parquet"),
                has_profile=profile_result is not None
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing data sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list data sources: {str(e)}")


# AI Profile Endpoints
@router.get("/profiles")
async def get_ai_profiles(
    file_id: str = Query(..., description="File ID to get profiles for"),
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get AI profiles for a specific file"""
    # Check if actual profile exists in ProfileResult table
    profile_result = db.query(ProfileResult).filter(
        ProfileResult.file_id == file_id
    ).first()
    
    # Derive status from column_profiles similar to get_ai_profile_status
    status = "completed"  # Default status
    if profile_result:
        if profile_result.column_profiles:
            for profile in profile_result.column_profiles:
                if isinstance(profile, dict) and 'error' in profile:
                    status = "error"
                    break
        
    if profile_result and status == "completed":
        # Check if a session exists for this profile
        session = db.query(ProfileSession).filter(
            ProfileSession.file_id == file_id,
            ProfileSession.username == current_user.username
        ).first()
        
        return {
            "profiles": [{
                "id": file_id,
                "file_id": file_id,
                "file_name": profile_result.file_name,
                "status": "completed",
                "created_at": profile_result.created_at,
                "total_rows": profile_result.total_rows,
                "total_columns": profile_result.total_columns,
                "data_quality_score": profile_result.data_quality_score,
                "has_session": session is not None
            }]
        }
    
    return {"profiles": []}


@router.post("/profiles")
async def create_ai_profile(
    request: ProfileSessionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(has_any_permission(["datapuur:write"])),
    db: Session = Depends(get_db)
):
    """Create an AI profile for a data source"""
    try:
        # Check if this is a recreation request
        recreate = getattr(request, 'recreate', False)
        
        # Check if profile already exists
        existing_session = db.query(ProfileSession).filter(
            ProfileSession.file_id == request.file_id,
            ProfileSession.username == current_user.username
        ).first()
        
        if existing_session and not recreate:
            return {
                "id": request.file_id,
                "file_id": request.file_id,
                "file_name": request.file_name,
                "status": "completed",
                "created_at": existing_session.created_at
            }
        
        # If recreating, delete the existing session
        if existing_session and recreate:
            db.delete(existing_session)
            db.commit()
            logger.info(f"Deleted existing profile for recreation: {request.file_id}")
        
        # Create profile in background
        profile_id = request.file_id
        
        # Start background task to create profile
        background_tasks.add_task(
            create_profile_background,
            profile_id=profile_id,
            file_id=request.file_id,
            file_name=request.file_name,
            file_path=request.file_path,
            username=current_user.username,
            db=db
        )
        
        return {
            "id": profile_id,
            "file_id": request.file_id,
            "file_name": request.file_name,
            "status": "processing",
            "message": "Profile creation started"
        }
        
    except Exception as e:
        logger.error(f"Error creating AI profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}")
async def get_ai_profile_status(
    profile_id: str,
    current_user: User = Depends(has_any_permission(["datapuur:read"])),
    db: Session = Depends(get_db)
):
    """Get AI profile status"""
    # Import ProfileResult model
    from api.profiler.models import ProfileResult
    
    # Check if actual profile exists
    profile_result = db.query(ProfileResult).filter(
        ProfileResult.file_id == profile_id
    ).first()
    
    if profile_result:
        # Check if a session exists for this profile
        session = db.query(ProfileSession).filter(
            ProfileSession.file_id == profile_id,
            ProfileSession.username == current_user.username
        ).first()
        
        # Determine status based on whether column_profiles contains an error entry
        status = "completed"
        if profile_result.column_profiles:
            # Check if any item in the column_profiles list has an 'error' key
            for profile in profile_result.column_profiles:
                if isinstance(profile, dict) and 'error' in profile:
                    status = "error"
                    break
            
        return {
            "id": profile_id,
            "file_id": profile_id,
            "file_name": profile_result.file_name,
            "status": status,  # Derived status, not from model
            "created_at": profile_result.created_at,
            "total_rows": profile_result.total_rows,
            "total_columns": profile_result.total_columns,
            "data_quality_score": profile_result.data_quality_score,
            "exact_duplicates_count": profile_result.exact_duplicates_count,
            "fuzzy_duplicates_count": profile_result.fuzzy_duplicates_count,
            "has_session": session is not None
        }
    
    # Check if it's still processing (would need a separate tracking mechanism)
    return {
        "id": profile_id,
        "status": "processing",
        "message": "Profile is being created..."
    }


async def create_profile_background(
    profile_id: str,
    file_id: str,
    file_name: str,
    file_path: str,
    username: str,
    db: Session  # This parameter is not used, we'll create a new session
):
    """Background task to create AI profile"""
    # Create a new database session for the background task
    db = SessionLocal()
    try:
        logger.info(f"Starting AI profile creation for file: {file_name}")
        
        # Import necessary modules
        import pandas as pd
        import os
        from api.profiler.services.engine import DataProfiler
        from api.profiler.models import ProfileResult
        import numpy as np
        import json

        # Helper function to convert NumPy types to Python native types for JSON serialization
        def convert_numpy_types(obj):
            """Convert NumPy types to Python native types for JSON serialization"""
            if isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return convert_numpy_types(obj.tolist())
            elif isinstance(obj, np.bool_):
                return bool(obj)
            else:
                return obj
        
        # Fix file path resolution - handle both absolute and relative paths
        if os.path.isabs(file_path):
            resolved_path = file_path
        else:
            resolved_path = str(DATA_DIR/file_path)
            
        # Log the resolved path for debugging
        print(f"Resolving file path: original={file_path}, resolved={resolved_path}")

        # Check if file exists
        if not os.path.exists(resolved_path):
            # Try alternative path resolution based on file_id
            alternative_path = str(DATA_DIR/f"{file_id}.parquet")
            print(f"Trying alternative path: {alternative_path}")
            
            if os.path.exists(alternative_path):
                resolved_path = alternative_path
                logger.info(f"Using alternative path: {resolved_path}")
            else:
                logger.error(f"File not found at primary path: {resolved_path} or alternative path: {alternative_path}")
                raise Exception(f"File not found: {file_path}")
        
        # Update file_path to the resolved path
        file_path = resolved_path
        
        # Read the parquet file
        print(f"Reading parquet file: {file_path}")
        try:
            df = pd.read_parquet(file_path)
            print(f"Successfully read parquet file with {len(df)} rows and {len(df.columns)} columns")
        except Exception as e:
            logger.error(f"Error reading parquet file: {str(e)}")
            raise Exception(f"Failed to read data file: {str(e)}")
        
        # Get file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        memory_limit_mb = max(1000, int(file_size_mb * 2))
        
        logger.info(f"Starting profile generation with memory limit {memory_limit_mb} MB")
        profiler = DataProfiler(df, max_memory_mb=memory_limit_mb)
        
        # Generate profile
        profile_summary, column_profiles = profiler.generate_profile()
        
        # Process duplicates with sampling
        try:
            exact_duplicates = profiler.detect_exact_duplicates(sample_size=min(50000, len(df)))
            profile_summary["exact_duplicates_count"] = exact_duplicates["count"]
            
            if len(df) > 1000000:  # Skip fuzzy duplicates for very large files
                fuzzy_duplicates = {"count": 0, "values": []}
            else:
                fuzzy_duplicates = profiler.detect_fuzzy_duplicates(threshold=0.9, max_rows=min(1000, len(df)))
            
            profile_summary["fuzzy_duplicates_count"] = fuzzy_duplicates["count"]
            duplicate_groups = {
                "exact": exact_duplicates["values"],
                "fuzzy": fuzzy_duplicates["values"]
            }
        except Exception as e:
            logger.error(f"Error in duplicate detection: {str(e)}")
            profile_summary["exact_duplicates_count"] = 0
            profile_summary["fuzzy_duplicates_count"] = 0
            duplicate_groups = {"exact": [], "fuzzy": []}
        
        # Create or update ProfileResult
        profile_result = db.query(ProfileResult).filter(
            ProfileResult.file_id == file_id
        ).first()
        
        if not profile_result:
            profile_result = ProfileResult(
                id=profile_id,
                file_id=file_id,
                file_name=file_name,
                parquet_file_path=str(file_path),
                total_rows=0,  # Will be updated below
                total_columns=0,  # Will be updated below
                data_quality_score=0.0  # Will be updated below
            )
            db.add(profile_result)
        
        # Update profile data - convert NumPy types to Python native types
        profile_result.total_rows = int(profile_summary["total_rows"])
        profile_result.total_columns = int(profile_summary["total_columns"])
        profile_result.data_quality_score = float(profile_summary["data_quality_score"])
        profile_result.column_profiles = convert_numpy_types(column_profiles)
        profile_result.exact_duplicates_count = int(profile_summary["exact_duplicates_count"])
        profile_result.fuzzy_duplicates_count = int(profile_summary["fuzzy_duplicates_count"])
        profile_result.duplicate_groups = convert_numpy_types(duplicate_groups)
        # Status field removed as it's not in the ProfileResult model
        
        db.commit()
        logger.info(f"Profile created successfully for file: {file_name}")
        
        # Now create the AI profile session with the actual profile data
        # Convert PosixPath to string to avoid SQLite error
        session = ProfileSession(
            file_id=file_id,
            file_name=file_name,
            file_path=os.path.basename(file_path),  # Store just the filename part
            username=username,
            profile_id=profile_id,  # Link to the profile we just created
            status="active"
        )
        db.add(session)
        
        # Analyze profile with AI - ensure all data is serializable
        # Handle column_profiles as a list of dictionaries
        profile_data = {
            "total_rows": profile_result.total_rows,
            "total_columns": profile_result.total_columns,
            "data_quality_score": profile_result.data_quality_score,
            "missing_values_count": sum(
                int(col.get("missing_count", 0)) 
                for col in profile_result.column_profiles if isinstance(col, dict)
            ),
            "exact_duplicates_count": profile_result.exact_duplicates_count,
            "columns": profile_result.column_profiles
        }
        
        # Convert any remaining NumPy types
        profile_data = convert_numpy_types(profile_data)
        
        # Analyze with AI
        analysis = profile_agent.analyze_profile(
            profile_data=profile_data,
            file_path=str(file_path)
        )
        
        # Update session with analysis
        session.profile_summary = analysis.get("summary")
        session.data_quality_issues = analysis.get("quality_issues", [])
        session.improvement_suggestions = analysis.get("suggestions", [])
        
        # First commit the session to get a valid session.id
        db.add(session)
        db.commit()
        
        # Now that session has an ID, add the initial AI message
        # Use the SQLAlchemy model (imported at the top level)
        initial_message = ProfileMessageModel(
            session_id=session.id,  # Now session.id is valid
            role="assistant",
            content=analysis.get("summary", "Profile analysis completed."),
            message_metadata={
                "quality_issues": analysis.get("quality_issues", []),
                "suggestions": analysis.get("suggestions", [])
            }
        )
        db.add(initial_message)
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in background profile creation: {str(e)}")
        db.rollback()
        
        # Update profile result if it exists to log the error
        profile_result = db.query(ProfileResult).filter(
            ProfileResult.file_id == file_id
        ).first()
        if profile_result:
            # Add error information to column_profiles as JSON since there's no dedicated error field
            # Handle column_profiles as a list and add an error dictionary to it
            if not profile_result.column_profiles:
                profile_result.column_profiles = []
            
            # Add error as a special error entry in the list
            profile_result.column_profiles.append({"error": str(e)})
            db.commit()
    finally:
        db.close()



