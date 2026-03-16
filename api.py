from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import core


@asynccontextmanager
async def lifespan(app: FastAPI):
    core.enable_cache()
    yield


app = FastAPI(title="F1 Telemetry API", lifespan=lifespan)


@app.get("/compare")
def compare(year: int, circuit: str, driver1: str, driver2: str):
    try:
        data = core.compare_laps(year, circuit, driver1.upper(), driver2.upper())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # report is a DataFrame — drop it from the response
    data.pop("report")
    return data


@app.get("/season")
def season(year: int, driver: str):
    try:
        return core.get_season(year, driver.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results")
def results(year: int, circuit: str):
    try:
        return core.get_results(year, circuit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
