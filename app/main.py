import uvicorn
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World!"}

@app.get("/health")
def health():
    return {"status":"ok"}


# Running the server from the code editor.
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
