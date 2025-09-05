from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.auth import router as auth_router
from src.stations import router as stations_router
from src.routes import router as routes_router
from src.schedules import router as schedules_router
from src.bookings import router as bookings_router
from src.admin import router as admin_router

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Bangkok Train Transport System API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    auth_router.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)

app.include_router(
    stations_router.router,
    prefix=f"{settings.API_V1_STR}/stations",
    tags=["Stations"]
)

app.include_router(
    routes_router,
    prefix=f"{settings.API_V1_STR}/routes",
    tags=["Route Planning"]
)

app.include_router(
    schedules_router,
    prefix=f"{settings.API_V1_STR}/schedules",
    tags=["Schedules & Real-time"]
)

app.include_router(
    bookings_router,
    prefix=f"{settings.API_V1_STR}/bookings",
    tags=["Booking & Ticketing"]
)

app.include_router(
    admin_router.router,
    tags=["Admin System"]
)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Bangkok Train Transport System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)