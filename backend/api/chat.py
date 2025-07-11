import random
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from middleware.auth_middleware import verify_token
from models.response_schemas import (
    ApiResponse,
    ChatMessage,
    CSVPreview,
    PaginatedResponse,
    QueryResult,
    QuerySuggestion,
    SendMessageRequest,
    SendMessageResponse,
)
from services.project_service import get_project_service

router = APIRouter(prefix="/chat", tags=["chat"])
project_service = get_project_service()

# Mock chat messages database
MOCK_CHAT_MESSAGES = {}

# Mock CSV preview data
MOCK_CSV_PREVIEWS = {
    "project_001": {
        "columns": [
            "date",
            "product_name",
            "sales_amount",
            "quantity",
            "category",
            "region",
            "customer_id",
            "discount",
        ],
        "sample_data": [
            [
                "2024-01-01",
                "Product A",
                1500.00,
                10,
                "Electronics",
                "North",
                "CUST001",
                0.1,
            ],
            [
                "2024-01-02",
                "Product B",
                2300.50,
                15,
                "Clothing",
                "South",
                "CUST002",
                0.05,
            ],
            [
                "2024-01-03",
                "Product C",
                1890.25,
                12,
                "Electronics",
                "East",
                "CUST003",
                0.15,
            ],
            [
                "2024-01-04",
                "Product A",
                1200.00,
                8,
                "Electronics",
                "West",
                "CUST004",
                0.0,
            ],
            ["2024-01-05", "Product D", 3400.75, 25, "Home", "North", "CUST005", 0.2],
        ],
        "total_rows": 1000,
        "data_types": {
            "date": "date",
            "product_name": "string",
            "sales_amount": "number",
            "quantity": "number",
            "category": "string",
            "region": "string",
            "customer_id": "string",
            "discount": "number",
        },
    },
    "project_002": {
        "columns": [
            "customer_id",
            "age",
            "city",
            "signup_date",
            "total_orders",
            "lifetime_value",
        ],
        "sample_data": [
            [1, 25, "New York", "2023-06-15", 5, 1250.50],
            [2, 30, "Los Angeles", "2023-07-20", 8, 2100.25],
            [3, 45, "Chicago", "2023-05-10", 12, 3450.75],
            [4, 35, "Houston", "2023-08-05", 3, 890.00],
            [5, 28, "Phoenix", "2023-09-12", 7, 1875.80],
        ],
        "total_rows": 500,
        "data_types": {
            "customer_id": "number",
            "age": "number",
            "city": "string",
            "signup_date": "date",
            "total_orders": "number",
            "lifetime_value": "number",
        },
    },
}

# Mock query suggestions
MOCK_SUGGESTIONS = [
    {
        "id": "sug_001",
        "text": "Show me total sales by month",
        "category": "analysis",
        "complexity": "beginner",
    },
    {
        "id": "sug_002",
        "text": "Create a bar chart of top 5 products by sales",
        "category": "visualization",
        "complexity": "intermediate",
    },
    {
        "id": "sug_003",
        "text": "What's the average sales amount by region?",
        "category": "analysis",
        "complexity": "beginner",
    },
    {
        "id": "sug_004",
        "text": "Show sales trend over time as a line chart",
        "category": "visualization",
        "complexity": "intermediate",
    },
    {
        "id": "sug_005",
        "text": "Compare sales performance across different categories",
        "category": "analysis",
        "complexity": "advanced",
    },
]


def generate_mock_query_result(query: str, project_id: str) -> QueryResult:
    """Generate mock query result based on the question"""

    # Mock SQL generation based on query content
    if "total sales" in query.lower() or "sum" in query.lower():
        sql_query = "SELECT product_name, SUM(sales_amount) as total_sales FROM data GROUP BY product_name ORDER BY total_sales DESC LIMIT 10"
        result_data = [
            {"product_name": "Product A", "total_sales": 15000.50},
            {"product_name": "Product B", "total_sales": 12300.25},
            {"product_name": "Product C", "total_sales": 9890.75},
            {"product_name": "Product D", "total_sales": 8450.00},
            {"product_name": "Product E", "total_sales": 7200.80},
        ]
        result_type = "table"

    elif "chart" in query.lower() or "visualization" in query.lower():
        sql_query = "SELECT category, SUM(sales_amount) as total_sales FROM data GROUP BY category"
        result_data = [
            {"category": "Electronics", "total_sales": 45000.50},
            {"category": "Clothing", "total_sales": 32300.25},
            {"category": "Home", "total_sales": 28900.75},
            {"category": "Sports", "total_sales": 15450.00},
        ]
        result_type = "chart"

    elif "average" in query.lower():
        sql_query = (
            "SELECT region, AVG(sales_amount) as avg_sales FROM data GROUP BY region"
        )
        result_data = [
            {"region": "North", "avg_sales": 1850.75},
            {"region": "South", "avg_sales": 1720.50},
            {"region": "East", "avg_sales": 1950.25},
            {"region": "West", "avg_sales": 1680.80},
        ]
        result_type = "table"

    else:
        # Default response
        sql_query = "SELECT * FROM data LIMIT 5"
        result_data = [
            {
                "date": "2024-01-01",
                "product_name": "Product A",
                "sales_amount": 1500.00,
            },
            {
                "date": "2024-01-02",
                "product_name": "Product B",
                "sales_amount": 2300.50,
            },
            {
                "date": "2024-01-03",
                "product_name": "Product C",
                "sales_amount": 1890.25,
            },
        ]
        result_type = "table"

    return QueryResult(
        id=str(uuid.uuid4()),
        query=query,
        sql_query=sql_query,
        result_type=result_type,
        data=result_data,
        execution_time=round(random.uniform(0.1, 2.0), 2),
        row_count=len(result_data),
        chart_config=(
            {
                "type": "bar",
                "x_axis": "category" if result_type == "chart" else "product_name",
                "y_axis": "total_sales",
                "title": "Sales Analysis",
            }
            if result_type == "chart"
            else None
        ),
    )


@router.post("/{project_id}/message")
async def send_message(
    project_id: str, request: SendMessageRequest, user_id: str = Depends(verify_token)
) -> ApiResponse[SendMessageResponse]:
    """Send message and get query results"""

    # Verify project exists and user has access
    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        if not project_service.check_project_ownership(project_uuid, user_uuid):
            raise HTTPException(status_code=404, detail="Project not found")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    # Create user message
    user_message = ChatMessage(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=user_id,
        content=request.message,
        role="user",
        created_at=datetime.utcnow().isoformat() + "Z",
    )

    # Generate mock query result
    query_result = generate_mock_query_result(request.message, project_id)

    # Store message in mock database
    if project_id not in MOCK_CHAT_MESSAGES:
        MOCK_CHAT_MESSAGES[project_id] = []
    MOCK_CHAT_MESSAGES[project_id].append(user_message.model_dump())

    # Create AI response message
    ai_message = ChatMessage(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id="assistant",
        content=f"Here are the results for your query: '{request.message}'",
        role="assistant",
        created_at=datetime.utcnow().isoformat() + "Z",
        metadata={"query_result_id": query_result.id},
    )
    MOCK_CHAT_MESSAGES[project_id].append(ai_message.model_dump())

    response = SendMessageResponse(message=user_message, result=query_result)

    return ApiResponse(success=True, data=response)


@router.get("/{project_id}/messages")
async def get_messages(
    project_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(verify_token),
) -> ApiResponse[PaginatedResponse[ChatMessage]]:
    """Get chat message history"""

    # Verify project exists and user has access
    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        if not project_service.check_project_ownership(project_uuid, user_uuid):
            raise HTTPException(status_code=404, detail="Project not found")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    # Get messages for project
    messages_data = MOCK_CHAT_MESSAGES.get(project_id, [])
    messages = [ChatMessage(**msg) for msg in messages_data]

    # Apply pagination
    total = len(messages)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    messages_page = messages[start_idx:end_idx]

    paginated_response = PaginatedResponse(
        items=messages_page,
        total=total,
        page=page,
        limit=limit,
        hasMore=end_idx < total,
    )

    return ApiResponse(success=True, data=paginated_response)


@router.get("/{project_id}/preview")
async def get_csv_preview(
    project_id: str, user_id: str = Depends(verify_token)
) -> ApiResponse[CSVPreview]:
    """Get CSV data preview"""

    # Verify project exists and user has access
    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        if not project_service.check_project_ownership(project_uuid, user_uuid):
            raise HTTPException(status_code=404, detail="Project not found")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    # Get preview data for project
    if project_id not in MOCK_CSV_PREVIEWS:
        raise HTTPException(status_code=404, detail="CSV preview not available")

    preview_data = MOCK_CSV_PREVIEWS[project_id]
    preview = CSVPreview(**preview_data)

    return ApiResponse(success=True, data=preview)


@router.get("/{project_id}/suggestions")
async def get_query_suggestions(
    project_id: str, user_id: str = Depends(verify_token)
) -> ApiResponse[List[QuerySuggestion]]:
    """Get query suggestions"""

    # Verify project exists and user has access
    try:
        user_uuid = uuid.UUID(user_id)
        project_uuid = uuid.UUID(project_id)

        if not project_service.check_project_ownership(project_uuid, user_uuid):
            raise HTTPException(status_code=404, detail="Project not found")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    # Return mock suggestions
    suggestions = [QuerySuggestion(**sug) for sug in MOCK_SUGGESTIONS]

    return ApiResponse(success=True, data=suggestions)
