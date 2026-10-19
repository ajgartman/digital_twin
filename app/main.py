import uvicorn
from fastapi import FastAPI, HTTPException
from app.api.routes.validation import router as validation_router
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World!"}

@app.get("/health")
def health():
    return {"status":"ok"}


app.include_router(validation_router)


# Running the server from the code editor.
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)