import ctypes
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List

# --- Part 1: C++ Bridge Setup (Updated for Query) ---

# First, define a ctypes Structure that EXACTLY mirrors the C++ struct.
# This is our Python representation of a DataPoint.
class CDataPoint(ctypes.Structure):
    _fields_ = [
        ("timestamp", ctypes.c_uint64),
        ("value", ctypes.c_double)
    ]

try:
    lib = ctypes.CDLL("libinsight.so")
except OSError as e:
    print(f"FATAL: Error loading C++ shared library 'libinsight.so': {e}")
    exit(1)

# --- Define the ingest function signature ---
ingest_point_func = lib.ingest_point
ingest_point_func.argtypes = [ctypes.c_uint64, ctypes.c_double]
ingest_point_func.restype = None

# --- Define the NEW query function signature ---
# int64_t query_range(uint64_t start_ts, uint64_t end_ts, DataPoint* out_buffer, int64_t buffer_capacity)
query_range_func = lib.query_range
query_range_func.argtypes = [
    ctypes.c_uint64,
    ctypes.c_uint64,
    ctypes.POINTER(CDataPoint), # A pointer to our CDataPoint structure
    ctypes.c_int64
]
query_range_func.restype = ctypes.c_int64


# --- Part 2: FastAPI Application Definition ---
app = FastAPI(
    title="Insight-TSDB Service",
    description="A high-performance Time-Series Database with a C++ engine.",
    version="2.1.0", # Version bump for new feature
)

# --- Define our data models (schemas) ---
class IngestRequest(BaseModel):
    metric: str = Field(..., json_schema_extra={"example": "cpu.load.avg"})
    timestamp: int = Field(..., json_schema_extra={"example": 1664632800000})
    value: float = Field(..., json_schema_extra={"example": 42.5})

class IngestResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "success"})
    points_ingested: int = Field(..., json_schema_extra={"example": 1})

# This is the model for a single data point in our query response.
class QueryDataPoint(BaseModel):
    timestamp: int
    value: float

# The query response will be a list of these data points.
class QueryResponse(BaseModel):
    metric: str
    points: List[QueryDataPoint]

# --- Define API Endpoints ---
@app.post("/api/ingest", tags=["Ingestion"], response_model=IngestResponse)
async def ingest_data_point(point: IngestRequest):
    try:
        ingest_point_func(point.timestamp, point.value)
        return {"status": "success", "points_ingested": 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"C++ engine error: {e}")

# --- NEW ENDPOINT ---
@app.get("/api/query", tags=["Query"], response_model=QueryResponse)
async def query_data_range(
    start_ts: int = Query(..., description="Start of the time range (Unix timestamp, milliseconds)"),
    end_ts: int = Query(..., description="End of the time range (Unix timestamp, milliseconds)")
):
    """
    Queries the database for data points within a specified time range.
    """
    # Define a hard limit for the buffer to prevent memory issues.
    BUFFER_CAPACITY = 10000 

    # Create the buffer in Python. This is the block of memory we will pass to C++.
    # It's an array of CDataPoint objects, with a size of BUFFER_CAPACITY.
    BufferArrayType = CDataPoint * BUFFER_CAPACITY
    result_buffer = BufferArrayType()

    # Call the C++ function to fill the buffer.
    points_found = query_range_func(start_ts, end_ts, result_buffer, BUFFER_CAPACITY)

    # Convert the C++ structs from the buffer into a Python list of dictionaries.
    results = []
    for i in range(points_found):
        point = result_buffer[i]
        results.append({"timestamp": point.timestamp, "value": point.value})
    
    # We will hardcode the metric name for now.
    return {"metric": "cpu.load.avg", "points": results}