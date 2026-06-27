from fastapi import FastAPI

from stock_agent.app.api.routes import router


app = FastAPI(title="Stock Agent")
app.include_router(router)
